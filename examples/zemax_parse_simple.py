"""Demo: parse a Zemax ZMX file and show the resulting OptiVerse component.

Uses the canonical :mod:`optiverse.services.zemax_parser` and
:class:`optiverse.services.zemax_converter.ZemaxToInterfaceConverter` rather
than an inline reimplementation, so this demo can't drift away from the
real import behaviour.

Usage::

    python examples/zemax_parse_simple.py /path/to/file.zmx
"""

from __future__ import annotations

import sys

from optiverse.services.glass_catalog import GlassCatalog
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.zemax_parser import ZemaxParser


def _print_summary(filepath: str) -> int:
    parser = ZemaxParser()
    zemax_data = parser.parse(filepath)
    if zemax_data is None:
        print(f"Could not parse Zemax file: {filepath}", file=sys.stderr)
        return 1

    print("=" * 70)
    print("ZEMAX FILE PARSER — Simple Demonstration")
    print("=" * 70)
    print()
    print(parser.format_summary(zemax_data))
    print()
    print("-" * 70)
    print("CONVERSION TO OPTIVERSE COMPONENT")
    print("-" * 70)

    component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zemax_data)
    print(f"Name: {component.name}")
    print(f"Object height: {component.object_height_mm:.2f} mm (full diameter)")
    print(f"Interfaces: {len(component.interfaces or [])}")
    print()
    for idx, iface in enumerate(component.interfaces or [], start=1):
        radius = (
            f"R={iface.radius_of_curvature_mm:+.2f} mm" if iface.is_curved else "flat"
        )
        print(
            f"  [{idx}] {iface.name}\n"
            f"      pos=({iface.x1_mm:.2f}, {iface.y1_mm:.2f}) → "
            f"({iface.x2_mm:.2f}, {iface.y2_mm:.2f})  {radius}"
        )
    if component.notes:
        print()
        print("Notes:")
        for line in component.notes.splitlines():
            print(f"  {line}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python zemax_parse_simple.py <path_to_zmx_file>", file=sys.stderr)
        return 2
    return _print_summary(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
