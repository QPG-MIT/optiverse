"""
Zemax ZMX file parser for importing lens prescriptions.

Supports:
- Sequential mode (MODE SEQ)
- Standard surfaces
- Glass materials (including ``MIRROR`` for reflective surfaces)
- Coatings and semi-diameters
- Lens units (``UNIT MM | CM | M | IN``) — all lengths returned in mm
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

_logger = logging.getLogger(__name__)

# Zemax PARM cards on a COORDBRK surface:
#   PARM 1: x-decenter (length, in lens units)
#   PARM 2: y-decenter (length, in lens units)
#   PARM 3: tilt about x (degrees)
#   PARM 4: tilt about y (degrees)
#   PARM 5: tilt about z (degrees)
#   PARM 6: order flag (0 = decenter-then-tilt, 1 = tilt-then-decenter)
# Only PARM 1 and PARM 2 are length quantities and require UNIT scaling.
_COORDBRK_LENGTH_PARMS = (1, 2)

# Conversion factor from each supported Zemax lens-unit to millimetres.
# Lengths (DISZ, DIAM, ENPD) are *multiplied* by this, curvatures (CURV) are
# *divided* by it (since CURV is 1/length).
_UNIT_TO_MM: dict[str, float] = {
    "MM": 1.0,
    "CM": 10.0,
    "M": 1000.0,
    "IN": 25.4,
    "INCH": 25.4,
}


@dataclass
class ZemaxSurface:
    """Parsed Zemax surface data.

    `semi_diameter_mm` reflects Zemax's DIAM card, which stores the surface
    *semi*-diameter (half-aperture) in lens units. The full clear aperture
    diameter of the surface is therefore ``2 * semi_diameter_mm``.
    """

    number: int
    type: str = "STANDARD"
    curvature: float = 0.0  # 1/mm
    thickness: float = 0.0  # mm to next surface
    glass: str = ""
    semi_diameter_mm: float = 0.0  # mm (DIAM card; semi-diameter, not full diameter)
    coating: str = ""
    comment: str = ""
    is_stop: bool = False
    # PARM cards by index (1-based). Length-valued parms (1, 2 on COORDBRK)
    # are already converted to millimetres at parse time; angle-valued parms
    # (3, 4, 5 on COORDBRK) remain in degrees.
    parm: dict[int, float] = field(default_factory=dict)

    @property
    def radius_mm(self) -> float:
        """Radius of curvature (mm). Returns inf for flat surfaces."""
        if abs(self.curvature) < 1e-10:
            return float("inf")
        return 1.0 / self.curvature

    @property
    def is_flat(self) -> bool:
        """Check if surface is flat (infinite radius)."""
        return abs(self.curvature) < 1e-10

    @property
    def is_mirror(self) -> bool:
        """True if this surface is reflective (Zemax ``GLAS MIRROR``)."""
        return self.glass.strip().upper() == "MIRROR"

    @property
    def is_coordinate_break(self) -> bool:
        """True if this surface is a Zemax coordinate break (TYPE COORDBRK)."""
        return self.type.strip().upper() == "COORDBRK"

    @property
    def is_aspheric(self) -> bool:
        """True if this surface is an even or odd aspheric (TYPE EVENASPH / ODDASPHE).

        The parser does not capture aspheric coefficients; the converter
        treats the surface as a sphere at its base radius and flags it.
        """
        t = self.type.strip().upper()
        return t in {"EVENASPH", "ODDASPHE", "ASPHERIC"}


@dataclass
class ZemaxFile:
    """Parsed Zemax file data."""

    name: str = ""
    mode: str = "SEQ"  # SEQ or NSC
    wavelengths_um: list[float] = field(default_factory=list)
    primary_wavelength_idx: int = 1  # 1-indexed
    surfaces: list[ZemaxSurface] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
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

    def parse(self, filepath: str) -> ZemaxFile | None:
        """
        Parse a Zemax ZMX file.

        Args:
            filepath: Path to .zmx file

        Returns:
            ZemaxFile object, or None if parsing fails
        """
        try:
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            return self._parse_lines(lines)

        except OSError as e:
            _logger.error(f"Error reading Zemax file '{filepath}': {e}")
            return None
        except ValueError as e:
            _logger.error(f"Error parsing Zemax file '{filepath}': {e}")
            return None

    def _parse_lines(self, lines: list[str]) -> ZemaxFile:
        """Parse lines from Zemax file."""
        zemax = ZemaxFile()

        # First pass: pick up the UNIT card so we can normalise lengths to mm
        # as we parse surface blocks below. Zemax convention puts UNIT before
        # any SURF, but scanning first is robust to other orderings.
        length_scale_mm = self._extract_length_scale_mm(lines)

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Parse header fields
            if line.startswith("NAME "):
                zemax.name = line[5:].strip()

            elif line.startswith("MODE "):
                zemax.mode = line[5:].strip()

            elif line.startswith("NOTE "):
                # Extract note content (skip leading "0 ")
                note_content = line[5:].strip()
                if note_content.startswith("0 "):
                    note_content = note_content[2:]
                zemax.notes.append(note_content)

            elif line.startswith("ENPD "):
                # Entrance pupil diameter (full diameter, in file units → mm)
                try:
                    zemax.entrance_pupil_diameter = (
                        self._parse_float(line[5:]) * length_scale_mm
                    )
                except ValueError:
                    pass

            elif line.startswith("WAVM "):
                # Wavelength: WAVM <index> <wavelength_um> <weight>
                parts = line[5:].split()
                if len(parts) >= 2:
                    try:
                        wavelength = float(parts[1])
                        zemax.wavelengths_um.append(wavelength)
                    except ValueError:
                        pass

            elif line.startswith("PWAV "):
                # Primary wavelength index
                try:
                    zemax.primary_wavelength_idx = int(line[5:].strip())
                except ValueError:
                    pass

            elif line.startswith("SURF "):
                # Surface definition
                surf_num = int(line[5:].strip())
                i, surface = self._parse_surface_block(
                    lines, i + 1, surf_num, length_scale_mm
                )
                zemax.surfaces.append(surface)
                continue  # _parse_surface_block already advances i

            i += 1

        return zemax

    def _extract_length_scale_mm(self, lines: list[str]) -> float:
        """Scan for the UNIT card and return the mm-per-file-unit factor.

        Defaults to mm (1.0) when UNIT is absent or specifies an unknown unit.
        """
        for raw in lines:
            stripped = raw.strip()
            if not stripped.startswith("UNIT "):
                continue
            parts = stripped[5:].split()
            if not parts:
                continue
            unit = parts[0].upper()
            scale = _UNIT_TO_MM.get(unit)
            if scale is None:
                _logger.warning("Unknown Zemax UNIT '%s'; assuming mm", unit)
                return 1.0
            return scale
        return 1.0

    def _parse_surface_block(
        self,
        lines: list[str],
        start_idx: int,
        surf_num: int,
        length_scale_mm: float = 1.0,
    ) -> tuple[int, ZemaxSurface]:
        """
        Parse a SURF block.

        ``length_scale_mm`` is the mm-per-file-unit factor from the UNIT card.
        Lengths (DISZ, DIAM) are multiplied by it; curvatures (CURV) are
        divided by it (since 1/file-unit → 1/mm requires dividing by mm/unit).

        Returns:
            (next_line_index, ZemaxSurface)
        """
        surface = ZemaxSurface(number=surf_num)

        i = start_idx
        while i < len(lines):
            line_raw = lines[i]  # Keep original for indentation check
            line = line_raw.strip()

            # End of surface block when we hit next SURF or major keyword
            if line.startswith(("SURF ", "BLNK", "TOL", "MNUM", "MOFF")):
                break

            # Skip empty lines or lines that aren't indented (surface properties are indented)
            if not line or not line_raw.startswith("  "):
                i += 1
                continue

            # Parse surface properties (indented lines)
            if line.startswith("TYPE "):
                surface.type = line[5:].split()[0]

            elif line.startswith("CURV "):
                # CURV <value> ...   (file units of 1/length → 1/mm)
                parts = line[5:].split()
                if parts:
                    surface.curvature = self._parse_float(parts[0]) / length_scale_mm

            elif line.startswith("DISZ "):
                # DISZ <value>   (file units of length → mm)
                parts = line[5:].split()
                if parts:
                    val_str = parts[0]
                    if val_str.upper() == "INFINITY":
                        surface.thickness = float("inf")
                    else:
                        surface.thickness = self._parse_float(val_str) * length_scale_mm

            elif line.startswith("GLAS "):
                # GLAS <material> ...
                parts = line[5:].split()
                if parts:
                    surface.glass = parts[0]

            elif line.startswith("DIAM "):
                # DIAM <semi_diameter> ...   (Zemax DIAM is a semi-diameter, in file units)
                parts = line[5:].split()
                if parts:
                    surface.semi_diameter_mm = self._parse_float(parts[0]) * length_scale_mm

            elif line.startswith("COAT "):
                # COAT <coating_name>
                parts = line[5:].split()
                if parts:
                    surface.coating = parts[0]

            elif line.startswith("COMM "):
                # COMM <comment>
                surface.comment = line[5:].strip()

            elif line.startswith("STOP"):
                surface.is_stop = True

            elif line.startswith("PARM "):
                # PARM <index> <value> ...
                # Stored raw here; UNIT scaling for length-valued PARMs is
                # applied below once TYPE is known (TYPE may follow PARM).
                parts = line[5:].split()
                if len(parts) >= 2:
                    try:
                        idx = int(parts[0])
                        val = self._parse_float(parts[1])
                    except ValueError:
                        pass
                    else:
                        surface.parm[idx] = val

            i += 1

        # Apply UNIT scaling to length-valued PARMs (only meaningful for
        # COORDBRK surfaces, where PARMs 1 and 2 are decenters).
        if length_scale_mm != 1.0 and surface.is_coordinate_break:
            for parm_idx in _COORDBRK_LENGTH_PARMS:
                if parm_idx in surface.parm:
                    surface.parm[parm_idx] *= length_scale_mm

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
                    f"semi_d={surf.semi_diameter_mm:.2f}mm"
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
