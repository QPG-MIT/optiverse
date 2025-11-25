"""
Zemax ZMX file parser for importing lens prescriptions.

Supports:
- Sequential mode (MODE SEQ)
- Standard surfaces
- Glass materials
- Coatings and diameters
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

_logger = logging.getLogger(__name__)


@dataclass
class ZemaxSurface:
    """Parsed Zemax surface data."""
    number: int
    type: str = "STANDARD"
    curvature: float = 0.0  # 1/mm
    thickness: float = 0.0  # mm to next surface
    glass: str = ""
    diameter: float = 0.0  # mm
    coating: str = ""
    comment: str = ""
    is_stop: bool = False

    @property
    def radius_mm(self) -> float:
        """Radius of curvature (mm). Returns inf for flat surfaces."""
        if abs(self.curvature) < 1e-10:
            return float('inf')
        return 1.0 / self.curvature

    @property
    def is_flat(self) -> bool:
        """Check if surface is flat (infinite radius)."""
        return abs(self.curvature) < 1e-10


@dataclass
class ZemaxFile:
    """Parsed Zemax file data."""
    name: str = ""
    mode: str = "SEQ"  # SEQ or NSC
    wavelengths_um: List[float] = field(default_factory=list)
    primary_wavelength_idx: int = 1  # 1-indexed
    surfaces: List[ZemaxSurface] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    entrance_pupil_diameter: float = 0.0  # mm

    @property
    def primary_wavelength_um(self) -> float:
        """Get primary wavelength in micrometers."""
        if self.wavelengths_um and 0 < self.primary_wavelength_idx <= len(self.wavelengths_um):
            return self.wavelengths_um[self.primary_wavelength_idx - 1]
        # Default to 550nm if not specified
        return 0.55

    @property
    def num_surfaces(self) -> int:
        """Number of surfaces (excluding object surface)."""
        return len([s for s in self.surfaces if s.number > 0])


class ZemaxParser:
    """
    Parser for Zemax ZMX (sequential mode) files.

    Example usage:
        parser = ZemaxParser()
        zemax_data = parser.parse("AC254-100-B.zmx")
        print(f"Loaded: {zemax_data.name}")
        print(f"Surfaces: {zemax_data.num_surfaces}")
    """

    def parse(self, filepath: str) -> Optional[ZemaxFile]:
        """
        Parse a Zemax ZMX file.

        Args:
            filepath: Path to .zmx file

        Returns:
            ZemaxFile object, or None if parsing fails
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            return self._parse_lines(lines)

        except OSError as e:
            _logger.error(f"Error reading Zemax file '{filepath}': {e}")
            return None
        except ValueError as e:
            _logger.error(f"Error parsing Zemax file '{filepath}': {e}")
            return None

    def _parse_lines(self, lines: List[str]) -> ZemaxFile:
        """Parse lines from Zemax file."""
        zemax = ZemaxFile()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Parse header fields
            if line.startswith('NAME '):
                zemax.name = line[5:].strip()

            elif line.startswith('MODE '):
                zemax.mode = line[5:].strip()

            elif line.startswith('NOTE '):
                # Extract note content (skip leading "0 ")
                note_content = line[5:].strip()
                if note_content.startswith('0 '):
                    note_content = note_content[2:]
                zemax.notes.append(note_content)

            elif line.startswith('ENPD '):
                # Entrance pupil diameter
                try:
                    zemax.entrance_pupil_diameter = self._parse_float(line[5:])
                except ValueError:
                    pass

            elif line.startswith('WAVM '):
                # Wavelength: WAVM <index> <wavelength_um> <weight>
                parts = line[5:].split()
                if len(parts) >= 2:
                    try:
                        wavelength = float(parts[1])
                        zemax.wavelengths_um.append(wavelength)
                    except ValueError:
                        pass

            elif line.startswith('PWAV '):
                # Primary wavelength index
                try:
                    zemax.primary_wavelength_idx = int(line[5:].strip())
                except ValueError:
                    pass

            elif line.startswith('SURF '):
                # Surface definition
                surf_num = int(line[5:].strip())
                i, surface = self._parse_surface_block(lines, i + 1, surf_num)
                zemax.surfaces.append(surface)
                continue  # _parse_surface_block already advances i

            i += 1

        return zemax

    def _parse_surface_block(
        self,
        lines: List[str],
        start_idx: int,
        surf_num: int
    ) -> tuple[int, ZemaxSurface]:
        """
        Parse a SURF block.

        Returns:
            (next_line_index, ZemaxSurface)
        """
        surface = ZemaxSurface(number=surf_num)

        i = start_idx
        while i < len(lines):
            line_raw = lines[i]  # Keep original for indentation check
            line = line_raw.strip()

            # End of surface block when we hit next SURF or major keyword
            if line.startswith(('SURF ', 'BLNK', 'TOL', 'MNUM', 'MOFF')):
                break

            # Skip empty lines or lines that aren't indented (surface properties are indented)
            if not line or not line_raw.startswith('  '):
                i += 1
                continue

            # Parse surface properties (indented lines)
            if line.startswith('TYPE '):
                surface.type = line[5:].split()[0]

            elif line.startswith('CURV '):
                # CURV <value> ...
                parts = line[5:].split()
                if parts:
                    surface.curvature = self._parse_float(parts[0])

            elif line.startswith('DISZ '):
                # DISZ <value>
                parts = line[5:].split()
                if parts:
                    val_str = parts[0]
                    if val_str.upper() == 'INFINITY':
                        surface.thickness = float('inf')
                    else:
                        surface.thickness = self._parse_float(val_str)

            elif line.startswith('GLAS '):
                # GLAS <material> ...
                parts = line[5:].split()
                if parts:
                    surface.glass = parts[0]

            elif line.startswith('DIAM '):
                # DIAM <value> ...
                parts = line[5:].split()
                if parts:
                    surface.diameter = self._parse_float(parts[0])

            elif line.startswith('COAT '):
                # COAT <coating_name>
                parts = line[5:].split()
                if parts:
                    surface.coating = parts[0]

            elif line.startswith('COMM '):
                # COMM <comment>
                surface.comment = line[5:].strip()

            elif line.startswith('STOP'):
                surface.is_stop = True

            i += 1

        return i, surface

    def _parse_float(self, s: str) -> float:
        """Parse float, handling scientific notation."""
        s = s.strip()
        # Handle formats like "1.499700059988000000E-002"
        return float(s)

    def format_summary(self, zemax: ZemaxFile) -> str:
        """Generate a human-readable summary of the Zemax file."""
        lines = []
        lines.append(f"Zemax File: {zemax.name}")
        lines.append(f"Mode: {zemax.mode}")
        lines.append(f"Primary Wavelength: {zemax.primary_wavelength_um:.4f} µm")
        lines.append(f"Entrance Pupil: {zemax.entrance_pupil_diameter:.2f} mm")
        lines.append("")
        lines.append("Surfaces:")

        for surf in zemax.surfaces:
            if surf.number == 0:
                lines.append(f"  S{surf.number}: Object (infinity)")
            else:
                r_str = f"{surf.radius_mm:.2f}" if not surf.is_flat else "∞"
                glass_str = surf.glass if surf.glass else "Air"
                lines.append(
                    f"  S{surf.number}: R={r_str}mm, "
                    f"t={surf.thickness:.2f}mm, "
                    f"mat={glass_str}, "
                    f"d={surf.diameter:.2f}mm"
                )

        return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    if len(sys.argv) > 1:
        parser = ZemaxParser()
        data = parser.parse(sys.argv[1])
        if data:
            _logger.info(parser.format_summary(data))



