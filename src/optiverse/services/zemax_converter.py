"""
Convert Zemax surface definitions to OptiVerse InterfaceDefinition objects.

Maps Zemax sequential surfaces to the interface-based component model.
"""

import logging
import math
from typing import Optional

from ..core.interface_definition import InterfaceDefinition
from ..core.models import ComponentRecord
from .glass_catalog import GlassCatalog
from .log_service import get_log_service
from .zemax_parser import ZemaxFile, ZemaxSurface

_logger = logging.getLogger(__name__)


class ZemaxToInterfaceConverter:
    """
    Convert Zemax surfaces to InterfaceDefinition objects.

    Mapping strategy:
    - Each Zemax surface → refractive_interface
    - Sequential DISZ → x-position in mm
    - GLAS materials → n1, n2 refractive indices
    - DIAM → interface line length

    Example usage:
        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)
        component = converter.convert(zemax_file)
        # component.interfaces now contains all optical interfaces
    """

    def __init__(self, glass_catalog: Optional[GlassCatalog] = None):
        """
        Initialize converter.

        Args:
            glass_catalog: Glass catalog for refractive index lookup.
                          If None, creates default catalog.
        """
        self.catalog = glass_catalog or GlassCatalog()

    def convert(self, zemax_file: ZemaxFile) -> ComponentRecord:
        """
        Convert Zemax file to ComponentRecord with interfaces.

        Args:
            zemax_file: Parsed Zemax data

        Returns:
            ComponentRecord with interfaces populated
        """
        interfaces: list[InterfaceDefinition] = []
        cumulative_x = 0.0  # Position along optical axis
        current_material = ""  # Start in air

        # Process each surface (skip surface 0, which is object at infinity)
        for i, surf in enumerate(zemax_file.surfaces):
            if surf.number == 0:
                # Object surface - skip
                continue

            # Check if this is the image surface (last surface)
            is_image_surface = i == len(zemax_file.surfaces) - 1

            # Get next surface to determine material after this interface
            next_material = surf.glass if surf.glass else ""

            if not is_image_surface:
                # Get refractive indices
                n1 = self._get_index(current_material, zemax_file.primary_wavelength_um)
                n2 = self._get_index(next_material, zemax_file.primary_wavelength_um)

                # Create interface
                interface = self._create_interface(
                    surf, cumulative_x, n1, n2, zemax_file.primary_wavelength_um
                )
                interfaces.append(interface)

            # Advance position for next surface
            if not math.isinf(surf.thickness):
                cumulative_x += surf.thickness

            # Update current material for next iteration
            current_material = next_material

        # Determine component properties
        diameter_mm = self._get_max_diameter(zemax_file)

        # Generate component name
        name = zemax_file.name or "Imported Lens"

        # Create notes
        notes_lines = [
            "Imported from Zemax",
            f"Primary wavelength: {zemax_file.primary_wavelength_um * 1000:.1f} nm",
        ]
        if zemax_file.notes:
            # Include first note (often contains part number/description)
            notes_lines.append(zemax_file.notes[0][:200])  # Limit length
        notes = "\n".join(notes_lines)

        return ComponentRecord(
            name=name, interfaces=interfaces, object_height_mm=diameter_mm, notes=notes
        )

    def _create_interface(
        self, surf: ZemaxSurface, x_pos: float, n1: float, n2: float, wavelength_um: float
    ) -> InterfaceDefinition:
        """
        Create InterfaceDefinition from Zemax surface.

        Handles both flat and curved surfaces. For curved surfaces:
        - Zemax 3D (rotationally symmetric) → OptiVerse 2D (cross-section)
        - Radius of curvature preserved
        - Surface endpoints show aperture extent

        Args:
            surf: Zemax surface data
            x_pos: Position along optical axis (mm)
            n1: Refractive index before interface
            n2: Refractive index after interface
            wavelength_um: Wavelength for index calculation

        Returns:
            InterfaceDefinition object with curved surface properties
        """
        # Use diameter if available, otherwise use entrance pupil or default
        diameter = surf.diameter if surf.diameter > 0 else 25.4
        half_diameter = diameter / 2.0

        # Determine if surface is curved
        is_curved = not surf.is_flat
        radius_mm = surf.radius_mm if not surf.is_flat else 0.0

        # Calculate surface sag for curved surfaces (3D→2D projection)
        # The sag is how much the curved surface deviates from flat at the edge
        sag = 0.0
        if is_curved and abs(radius_mm) > 1e-6:
            # Sag formula: s = R - sqrt(R² - h²)
            # where h is the semi-diameter (half_diameter)
            R_abs = abs(radius_mm)
            h_sq = half_diameter**2
            if h_sq < R_abs**2:
                sag = R_abs - math.sqrt(R_abs**2 - h_sq)
                if radius_mm < 0:
                    sag = -sag  # Concave from left

        # Position of interface center (vertex)
        # For 2D cross-section, we show the interface as a line from -half_diameter to +half_diameter
        # The x-position represents the vertex (center point) of the curved surface

        # Generate descriptive name
        material_before = self._material_name(n1)
        material_after = self._material_name(n2)

        curvature_str = ""
        if is_curved:
            if radius_mm > 0:
                curvature_str = f" [R=+{radius_mm:.1f}mm]"
            else:
                curvature_str = f" [R={radius_mm:.1f}mm]"

        name = f"S{surf.number}: {material_before} → {material_after}{curvature_str}"
        if surf.comment:
            name = f"{surf.comment} (S{surf.number})"

        return InterfaceDefinition(
            x1_mm=x_pos,
            y1_mm=-half_diameter,
            x2_mm=x_pos,
            y2_mm=half_diameter,
            element_type="refractive_interface",
            name=name,
            n1=n1,
            n2=n2,
            is_curved=is_curved,
            radius_of_curvature_mm=radius_mm,
        )

    def _get_index(self, material: str, wavelength_um: float) -> float:
        """
        Get refractive index for material.

        Args:
            material: Material name (empty string = air)
            wavelength_um: Wavelength in micrometers

        Returns:
            Refractive index (defaults to 1.0 for air, 1.5 for unknown)
        """
        if not material or material.upper() in ["", "AIR", "VACUUM"]:
            return 1.0

        index = self.catalog.get_refractive_index(material, wavelength_um)

        if index is None:
            # Fallback: assume typical glass
            log = get_log_service()
            log.warning(f"Unknown material '{material}', assuming n=1.5", "Zemax")
            return 1.5

        return index

    def _material_name(self, n: float) -> str:
        """
        Generate readable material name from refractive index.

        Args:
            n: Refractive index

        Returns:
            Material name string
        """
        if abs(n - 1.0) < 0.01:
            return "Air"
        elif abs(n - 1.333) < 0.01:
            return "Water"
        elif abs(n - 1.458) < 0.01:
            return "Fused Silica"
        elif abs(n - 1.517) < 0.01:
            return "BK7"
        else:
            return f"n={n:.3f}"

    def _get_max_diameter(self, zemax_file: ZemaxFile) -> float:
        """
        Get maximum diameter from all surfaces.

        Args:
            zemax_file: Zemax data

        Returns:
            Maximum diameter in mm (default 25.4mm if none found)
        """
        diameters = [s.diameter for s in zemax_file.surfaces if s.diameter > 0]
        if diameters:
            return max(diameters)

        # Fallback: use entrance pupil diameter
        if zemax_file.entrance_pupil_diameter > 0:
            return zemax_file.entrance_pupil_diameter

        # Default: 1 inch
        return 25.4


# Quick test
if __name__ == "__main__":
    import sys

    from .zemax_parser import ZemaxParser

    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    if len(sys.argv) > 1:
        # Parse Zemax file
        parser = ZemaxParser()
        zemax_data = parser.parse(sys.argv[1])

        if zemax_data:
            _logger.info("Zemax file parsed successfully")
            _logger.info(parser.format_summary(zemax_data))
            _logger.info("\n" + "=" * 60)

            # Convert to interfaces
            converter = ZemaxToInterfaceConverter()
            component = converter.convert(zemax_data)

            _logger.info("\nConverted to OptiVerse component:")
            _logger.info(f"Name: {component.name}")
            num_ifaces = len(component.interfaces) if component.interfaces else 0
            if num_ifaces > 1:
                _logger.info(f"Type: Multi-element ({num_ifaces} interfaces)")
            elif num_ifaces == 1:
                _logger.info(f"Type: {component.interfaces[0].element_type}")
            else:
                _logger.info("Type: Unknown")
            _logger.info(f"Object height: {component.object_height_mm:.2f} mm")
            _logger.info(f"Interfaces: {num_ifaces}")
            _logger.info("")

            if component.interfaces:
                for i, iface in enumerate(component.interfaces):
                    _logger.info(f"Interface {i + 1}: {iface.name}")
                    _logger.info(f"  Position: x={iface.x1_mm:.2f} mm")
                    _logger.info(f"  Height: {iface.length_mm():.2f} mm")
                    _logger.info(f"  Indices: n1={iface.n1:.4f} → n2={iface.n2:.4f}")
                    _logger.info("")
