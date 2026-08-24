"""
Convert Zemax surface definitions to OptiVerse InterfaceDefinition objects.

Maps Zemax sequential surfaces to the interface-based component model.
"""

import logging
import math

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
    - Each refracting Zemax surface → ``refractive_interface``
    - Surface with ``GLAS MIRROR`` → ``mirror`` element, and the optical-axis
      direction flips after it (a folded system unfolds into a single line
      in the editor with positions reflected across the mirror).
    - Sequential DISZ → x-position in mm (direction-aware)
    - GLAS materials → n1, n2 refractive indices
    - DIAM (semi-diameter) → interface half-extent in y
    - The first surface (``SURF 0``) is the object; the last surface is the
      image plane — neither emits an interface.
    - Dummy / aperture-stop surfaces that don't refract (flat AND same
      material on both sides) are skipped to avoid cluttering the import.

    Example usage:
        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)
        component = converter.convert(zemax_file)
        # component.interfaces now contains all optical interfaces
    """

    # If |n1 - n2| is below this, a flat surface is treated as a dummy
    # (no optical effect) and skipped during conversion.
    _DUMMY_INDEX_TOL = 1e-4

    def __init__(self, glass_catalog: GlassCatalog | None = None):
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

        The converter tracks an oriented 2D frame ``(pos_x, pos_y, angle_rad)``
        as it walks the sequential surface list. Each surface is placed at the
        current ``pos``; its interface line is drawn perpendicular to the
        current propagation direction. Thicknesses advance ``pos`` along the
        current direction. ``COORDBRK`` surfaces translate / rotate the frame
        (in-plane axes only — out-of-plane tilts are ignored), and mirrors
        reverse the propagation direction.

        Args:
            zemax_file: Parsed Zemax data

        Returns:
            ComponentRecord with interfaces populated
        """
        interfaces: list[InterfaceDefinition] = []
        # 2D frame: position (mm) of the current axis vertex, plus the
        # propagation direction (radians, 0 = +x).
        pos_x = 0.0
        pos_y = 0.0
        angle_rad = 0.0
        current_material = ""  # Material on the n1 side of the next surface (air to start)
        approximated_aspheres: list[int] = []

        wavelength_um = zemax_file.primary_wavelength_um
        last_index = len(zemax_file.surfaces) - 1

        for i, surf in enumerate(zemax_file.surfaces):
            if surf.number == 0:
                # Object surface — never emits an interface.
                continue

            is_image_surface = i == last_index

            if is_image_surface:
                # Image / sensor plane: don't emit an interface, and don't
                # update materials. We do not advance past it either.
                continue

            if surf.is_coordinate_break:
                pos_x, pos_y, angle_rad = self._apply_coordinate_break(
                    surf, pos_x, pos_y, angle_rad
                )
                # COORDBRK itself has no aperture; just advance along the
                # (possibly rotated) axis by its DISZ thickness.
                pos_x, pos_y = self._advance(pos_x, pos_y, angle_rad, surf.thickness)
                continue

            if surf.is_aspheric:
                # Aspheric coefficients aren't represented in the 2D editor;
                # the renderer will treat the surface as a sphere at its
                # base radius. Log + annotate so the approximation is visible.
                approximated_aspheres.append(surf.number)

            if surf.is_mirror:
                interfaces.append(
                    self._create_mirror_interface(surf, pos_x, pos_y, angle_rad)
                )
                pos_x, pos_y = self._advance(pos_x, pos_y, angle_rad, surf.thickness)
                # Light reverses along the optical axis after a planar reflection.
                angle_rad += math.pi
                continue

            next_material = surf.glass if surf.glass else ""
            n1 = self._get_index(current_material, wavelength_um)
            n2 = self._get_index(next_material, wavelength_um)

            # Skip dummy / aperture-stop surfaces that don't change the
            # medium and have no curvature — they have no optical effect
            # and only clutter the imported component.
            if surf.is_flat and abs(n1 - n2) < self._DUMMY_INDEX_TOL:
                pass
            else:
                interfaces.append(
                    self._create_refractive_interface(
                        surf, pos_x, pos_y, angle_rad, n1, n2
                    )
                )

            pos_x, pos_y = self._advance(pos_x, pos_y, angle_rad, surf.thickness)
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
        if approximated_aspheres:
            ids = ", ".join(f"S{n}" for n in approximated_aspheres)
            warning = (
                f"Note: aspheric surface(s) {ids} approximated as spheres at "
                "their base radius — aspheric coefficients are not represented."
            )
            notes_lines.append(warning)
            try:
                get_log_service().warning(warning, "Zemax")
            except Exception:  # pragma: no cover — log service absent in headless tests
                _logger.warning(warning)
        if zemax_file.notes:
            # Include first note (often contains part number/description)
            notes_lines.append(zemax_file.notes[0][:200])  # Limit length
        notes = "\n".join(notes_lines)

        return ComponentRecord(
            name=name, interfaces=interfaces, object_height_mm=diameter_mm, notes=notes
        )

    @staticmethod
    def _advance(
        pos_x: float, pos_y: float, angle_rad: float, thickness: float
    ) -> tuple[float, float]:
        """Move ``pos`` forward along ``angle_rad`` by ``thickness`` mm.

        Infinite thicknesses (Zemax ``DISZ INFINITY``, used on the object
        surface) leave the position unchanged.
        """
        if math.isinf(thickness):
            return pos_x, pos_y
        return (
            pos_x + thickness * math.cos(angle_rad),
            pos_y + thickness * math.sin(angle_rad),
        )

    @staticmethod
    def _apply_coordinate_break(
        surf: ZemaxSurface, pos_x: float, pos_y: float, angle_rad: float
    ) -> tuple[float, float, float]:
        """Apply a Zemax COORDBRK surface's in-plane decenter and tilt.

        Maps Zemax PARM 1 (x-decenter) to a shift perpendicular to the
        current propagation direction, and PARM 4 (tilt about y) to a
        rotation in the cross-section plane. Out-of-plane PARMs (2 / 3 / 5)
        are silently dropped — they can't be represented in a 2D editor.
        Uses the default Zemax order: decenter, then tilt.
        """
        decenter_x = surf.parm.get(1, 0.0)
        tilt_y_deg = surf.parm.get(4, 0.0)

        # Decenter is "x" in the Zemax pre-tilt frame, which maps to the
        # direction perpendicular to current propagation (i.e. across the
        # optical axis, in the cross-section plane).
        if decenter_x:
            perp_x = -math.sin(angle_rad)
            perp_y = math.cos(angle_rad)
            pos_x += decenter_x * perp_x
            pos_y += decenter_x * perp_y

        angle_rad += math.radians(tilt_y_deg)
        return pos_x, pos_y, angle_rad

    def _create_refractive_interface(
        self,
        surf: ZemaxSurface,
        pos_x: float,
        pos_y: float,
        angle_rad: float,
        n1: float,
        n2: float,
    ) -> InterfaceDefinition:
        """
        Build a refractive InterfaceDefinition from a Zemax surface.

        The interface is a line segment perpendicular to the current
        propagation direction. Curvature, if any, is conveyed via
        ``is_curved`` / ``radius_of_curvature_mm`` — the renderer derives
        sag from those, working from the chord normal so rotated surfaces
        bulge in the right direction automatically.

        Args:
            surf: Zemax surface data.
            pos_x, pos_y: Position of the surface vertex (mm).
            angle_rad: Current propagation direction (radians; 0 = +x).
            n1: Refractive index on the incident side.
            n2: Refractive index on the transmitted side.
        """
        x1, y1, x2, y2 = self._line_endpoints(surf, pos_x, pos_y, angle_rad)
        is_curved = not surf.is_flat
        radius_mm = surf.radius_mm if is_curved else 0.0

        return InterfaceDefinition(
            x1_mm=x1,
            y1_mm=y1,
            x2_mm=x2,
            y2_mm=y2,
            element_type="refractive_interface",
            name=self._refractive_name(surf, n1, n2, is_curved, radius_mm),
            n1=n1,
            n2=n2,
            is_curved=is_curved,
            radius_of_curvature_mm=radius_mm,
        )

    def _create_mirror_interface(
        self,
        surf: ZemaxSurface,
        pos_x: float,
        pos_y: float,
        angle_rad: float,
    ) -> InterfaceDefinition:
        """Build a mirror InterfaceDefinition from a Zemax mirror surface."""
        x1, y1, x2, y2 = self._line_endpoints(surf, pos_x, pos_y, angle_rad)
        is_curved = not surf.is_flat
        radius_mm = surf.radius_mm if is_curved else 0.0

        descriptive = f"S{surf.number}: Mirror"
        if is_curved:
            sign = "+" if radius_mm > 0 else ""
            descriptive = f"S{surf.number}: Mirror [R={sign}{radius_mm:.1f}mm]"
        if surf.is_aspheric:
            descriptive = f"{descriptive} (Asphere approx.)"
        if surf.is_stop:
            descriptive = f"{descriptive} (Aperture Stop)"
        name = f"{surf.comment} | {descriptive}" if surf.comment else descriptive

        return InterfaceDefinition(
            x1_mm=x1,
            y1_mm=y1,
            x2_mm=x2,
            y2_mm=y2,
            element_type="mirror",
            name=name,
            reflectivity=100.0,
            is_curved=is_curved,
            radius_of_curvature_mm=radius_mm,
        )

    def _line_endpoints(
        self,
        surf: ZemaxSurface,
        pos_x: float,
        pos_y: float,
        angle_rad: float,
    ) -> tuple[float, float, float, float]:
        """Endpoints of the interface line at ``pos``, perpendicular to ``angle_rad``.

        Returns ``(x1, y1, x2, y2)``. For axis-aligned propagation (``angle_rad
        == 0``) this matches the previous axis-aligned convention:
        ``x1 == x2 == pos_x``, ``y1 == -half_d``, ``y2 == +half_d``.
        """
        half_diameter = self._half_diameter_mm(surf)
        perp_x = -math.sin(angle_rad)
        perp_y = math.cos(angle_rad)
        return (
            pos_x - half_diameter * perp_x,
            pos_y - half_diameter * perp_y,
            pos_x + half_diameter * perp_x,
            pos_y + half_diameter * perp_y,
        )

    # Default semi-diameter when DIAM is omitted: 1/2" → a 1" full aperture.
    _DEFAULT_SEMI_DIAMETER_MM = 12.7

    def _half_diameter_mm(self, surf: ZemaxSurface) -> float:
        """Semi-diameter (mm) for the interface line, with a sane default."""
        if surf.semi_diameter_mm > 0:
            return surf.semi_diameter_mm
        return self._DEFAULT_SEMI_DIAMETER_MM

    def _refractive_name(
        self,
        surf: ZemaxSurface,
        n1: float,
        n2: float,
        is_curved: bool,
        radius_mm: float,
    ) -> str:
        """Compose a descriptive name, prefixing any Zemax COMM verbatim."""
        material_before = self._material_name(n1)
        material_after = self._material_name(n2)

        curvature_str = ""
        if is_curved:
            sign = "+" if radius_mm > 0 else ""
            curvature_str = f" [R={sign}{radius_mm:.1f}mm]"

        descriptive = (
            f"S{surf.number}: {material_before} → {material_after}{curvature_str}"
        )
        if surf.is_aspheric:
            descriptive = f"{descriptive} (Asphere approx.)"
        if surf.is_stop:
            descriptive = f"{descriptive} (Aperture Stop)"
        if surf.comment:
            # Preserve Zemax COMM (often a part number) without dropping the
            # auto-generated material/curvature info.
            return f"{surf.comment} | {descriptive}"
        return descriptive

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
        Get the maximum full-aperture diameter across all surfaces.

        Zemax DIAM records are semi-diameters, so the full diameter is
        ``2 * semi_diameter_mm``.

        Args:
            zemax_file: Zemax data

        Returns:
            Maximum full diameter in mm (default 25.4mm if none found)
        """
        semi_diameters = [s.semi_diameter_mm for s in zemax_file.surfaces if s.semi_diameter_mm > 0]
        if semi_diameters:
            return 2.0 * max(semi_diameters)

        # Fallback: use entrance pupil diameter (already a full diameter)
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
            elif num_ifaces == 1 and component.interfaces:
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
