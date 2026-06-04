"""
Export an Optiverse scene to a PyOpticL v2 layout folder.

The generated folder contains a Python script and a ``models/`` directory
laid out exactly the way PyOpticL's ``import_model`` expects:

    <export>/
        <export>.py
        models/
            <comp_a>/<comp_a>.step
            <comp_a>/<comp_a>.json
            <comp_b>/...

The script can be executed in FreeCAD with the PyOpticL workbench to
produce a 3-D CAD model with a precision-drilled baseplate.
"""

from __future__ import annotations

import datetime
import json
import logging
import math
import os
import re
import shutil
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class BaseplateOptions:
    """User-configurable options for the exported baseplate."""

    width_mm: float = 200.0
    height_mm: float = 150.0
    thickness_mm: float = 25.4  # 1 inch
    optical_height_mm: float = 12.7  # 0.5 inch
    gap_mm: float = 3.175  # 1/8 inch
    metric: bool = False
    label: str = "Optiverse Export"


_STEM_SANITIZER = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_stem(s: str) -> str:
    """Return a string safe to use as both a model name and folder name."""
    cleaned = _STEM_SANITIZER.sub("_", s) if s else ""
    return cleaned or "part"


# ---------------------------------------------------------------------------
# Interface mapping helpers
# ---------------------------------------------------------------------------


def _interface_to_pyopticl(iface_dict: dict[str, Any]) -> str | None:
    """Generate a PyOpticL Interface constructor call from an InterfaceDefinition dict.

    Returns a Python source fragment, or None if the interface type is not exportable.
    """
    etype = iface_dict.get("element_type", "")

    # Compute interface length as approximate diameter/size
    x1 = iface_dict.get("x1_mm", 0.0)
    y1 = iface_dict.get("y1_mm", 0.0)
    x2 = iface_dict.get("x2_mm", 0.0)
    y2 = iface_dict.get("y2_mm", 0.0)
    length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    diameter_expr = f'dim({length:.1f}, "mm")'

    if etype == "mirror":
        return f"Reflection(position=(0, 0, 0), rotation=(0, 0, 0), diameter={diameter_expr})"

    if etype == "lens":
        efl = iface_dict.get("efl_mm", 100.0)
        return (
            f"Lens(position=(0, 0, 0), rotation=(0, 0, 0), "
            f'diameter={diameter_expr}, focal_length=dim({efl:.1f}, "mm"))'
        )

    if etype == "beam_splitter":
        ratio = iface_dict.get("split_R", 50.0) / 100.0
        pol = iface_dict.get("pbs_transmission_axis_deg")
        is_pol = iface_dict.get("is_polarizing", False)
        diag = length * math.sqrt(2)
        parts = [
            "position=(0, 0, 0)",
            "rotation=(0, 0, -45)",
            f'width=dim({diag:.1f}, "mm")',
            f'height=dim({diag:.1f}, "mm")',
        ]
        if is_pol and pol is not None:
            parts.append(f"ref_polarization={pol:.1f}")
        else:
            parts.append(f"ref_ratio={ratio:.3f}")
        return f"Reflection({', '.join(parts)})"

    if etype == "dichroic":
        cutoff = iface_dict.get("cutoff_wavelength_nm", 550.0)
        pass_type = iface_dict.get("pass_type", "longpass")
        if pass_type == "longpass":
            wavelengths = f"[(None, {cutoff:.0f})]"
        else:
            wavelengths = f"[({cutoff:.0f}, None)]"
        return (
            f"Reflection(position=(0, 0, 0), rotation=(0, 0, 0), "
            f"diameter={diameter_expr}, ref_wavelengths={wavelengths})"
        )

    if etype == "polarizing_interface":
        subtype = iface_dict.get("polarizer_subtype", "waveplate")
        if subtype == "waveplate":
            phase = iface_dict.get("phase_shift_deg", 90.0)
            retardance = phase / 360.0
            fast_axis = iface_dict.get("fast_axis_deg", 0.0)
            return (
                f"Waveplate(position=(0, 0, 0), rotation=(0, 0, 0), "
                f"diameter={diameter_expr}, retardance={retardance:.4f}, "
                f"fast_axis_angle={fast_axis:.1f})"
            )
        return None

    if etype == "beam_block":
        return f"Stop(position=(0, 0, 0), rotation=(0, 0, 0), diameter={diameter_expr})"

    return None


# ---------------------------------------------------------------------------
# Scene analysis
# ---------------------------------------------------------------------------


@dataclass
class ExportItem:
    """A scene item ready for export."""

    label: str
    x_mm: float
    y_mm: float
    angle_deg: float
    step_file_path: str | None
    step_filename: str | None
    interfaces: list[dict[str, Any]]
    is_source: bool = False
    wavelength_nm: float = 633.0
    item_type: str = "component"


def analyse_scene(scene_data: dict[str, Any]) -> tuple[list[ExportItem], list[str]]:
    """Parse a serialised Optiverse scene into ExportItems.

    Returns:
        (items, warnings) where *warnings* lists components missing STEP files.
    """
    items: list[ExportItem] = []
    warnings: list[str] = []

    for item_data in scene_data.get("items", []):
        item_type = item_data.get("_type", "")

        if item_type == "source":
            items.append(ExportItem(
                label=f"Source ({item_data.get('wavelength_nm', 633.0):.0f} nm)",
                x_mm=item_data.get("x_mm", 0.0),
                y_mm=item_data.get("y_mm", 0.0),
                angle_deg=item_data.get("angle_deg", 0.0),
                step_file_path=None,
                step_filename=None,
                interfaces=[],
                is_source=True,
                wavelength_nm=item_data.get("wavelength_nm", 633.0),
                item_type="source",
            ))
            continue

        if item_type == "component":
            name = item_data.get("name") or "Component"
            step = item_data.get("step_file_path") or ""
            interfaces = item_data.get("interfaces", [])

            if not step:
                warnings.append(name)

            items.append(ExportItem(
                label=name,
                x_mm=item_data.get("x_mm", 0.0),
                y_mm=item_data.get("y_mm", 0.0),
                angle_deg=item_data.get("angle_deg", 0.0),
                step_file_path=step or None,
                step_filename=os.path.basename(step) if step else None,
                interfaces=interfaces if isinstance(interfaces, list) else [],
                item_type="component",
            ))

    return items, warnings


# ---------------------------------------------------------------------------
# Coordinate transforms
# ---------------------------------------------------------------------------


def _compute_baseplate_bounds(
    items: list[ExportItem], gap_mm: float
) -> tuple[float, float, float, float]:
    """Return (x_offset, y_offset, width, height) for the baseplate."""
    if not items:
        return 0.0, 0.0, 200.0, 150.0

    xs = [it.x_mm for it in items]
    ys = [it.y_mm for it in items]

    x_min = min(xs) - gap_mm - 25.0  # 25 mm margin
    y_min = min(ys) - gap_mm - 25.0
    x_max = max(xs) + gap_mm + 25.0
    y_max = max(ys) + gap_mm + 25.0

    # Round up to nearest inch grid
    inch = 25.4
    width = math.ceil((x_max - x_min) / inch) * inch
    height = math.ceil((y_max - y_min) / inch) * inch

    return x_min, y_min, max(width, inch), max(height, inch)


def _optiverse_angle_to_pyopticl(angle_deg: float) -> float:
    """Convert Optiverse angle convention to PyOpticL rotation (degrees around Z)."""
    # Optiverse: 0° = right (+X), 90° = down (+Y in display / -Y in storage)
    # PyOpticL:  rotation around Z in standard math convention
    return -angle_deg


# ---------------------------------------------------------------------------
# Script generation
# ---------------------------------------------------------------------------


def generate_script(
    items: list[ExportItem],
    options: BaseplateOptions,
) -> str:
    """Generate a PyOpticL v2 Python script from analysed scene items."""

    x_off, y_off, auto_w, auto_h = _compute_baseplate_bounds(items, options.gap_mm)
    bp_w = options.width_mm if options.width_mm > 0 else auto_w
    bp_h = options.height_mm if options.height_mm > 0 else auto_h

    lines: list[str] = []

    # Header
    lines.append('"""')
    lines.append("PyOpticL layout exported from Optiverse")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append('"""')
    lines.append("")
    lines.append(
        "from PyOpticL.beam_path import BeamPath, Lens, Reflection, Stop, Waveplate"
    )
    lines.append("from PyOpticL.layout import Component")
    lines.append("from PyOpticL.library import baseplate")
    lines.append(
        "from PyOpticL.utils import Dimension as dim, import_model, "
        "fix_relative_imports"
    )
    lines.append("from PyOpticL.utils import cylinder_shape, box_shape")
    lines.append("")
    lines.append("fix_relative_imports()")
    lines.append("")

    if options.metric:
        lines.append("from PyOpticL.settings import set_measurement_system")
        lines.append('set_measurement_system("metric")')
        lines.append("")

    # Warn about identity orientation on imported models
    has_step = any(
        not it.is_source and it.step_file_path for it in items
    )
    if has_step:
        lines.append(
            "# NOTE: Imported STEP model orientations are set to identity."
        )
        lines.append(
            "# Open each model's .json file in models/ and use PyOpticL's"
        )
        lines.append(
            "# 'Get Orientation' tool in FreeCAD to set correct values."
        )
        lines.append("")

    lines.append("")

    # Component definitions
    comp_class_map: dict[int, str] = {}
    class_counter = 0

    for idx, item in enumerate(items):
        if item.is_source:
            continue

        # Determine if this component has exportable interfaces
        iface_strs: list[str] = []
        for iface in item.interfaces:
            code = _interface_to_pyopticl(iface)
            if code:
                iface_strs.append(code)

        if item.step_file_path:
            # Component with STEP file: use mesh class variable
            class_counter += 1
            class_name = f"component_{class_counter}_def"
            comp_class_map[idx] = class_name

            step_stem = _sanitize_stem(
                os.path.splitext(item.step_filename or "part")[0]
            )

            lines.append(f"class {class_name}:")
            lines.append(f'    """Definition for: {item.label}"""')
            lines.append('    object_group = "optics"')
            lines.append("    object_color = (0.5, 0.5, 0.8)")
            lines.append(
                f'    mesh = import_model("{step_stem}", directory="models")'
            )
            lines.append("")

            if iface_strs:
                lines.append("    def interfaces(self):")
                lines.append("        return [")
                for s in iface_strs:
                    lines.append(f"            {s},")
                lines.append("        ]")
            lines.append("")
            lines.append("")

        elif iface_strs:
            # Component without STEP but with exportable interfaces:
            # generate a definition with primitive geometry so beam
            # path simulation still works.
            class_counter += 1
            class_name = f"component_{class_counter}_def"
            comp_class_map[idx] = class_name

            # Use the first interface's diameter for simple geometry
            first_iface = item.interfaces[0] if item.interfaces else {}
            x1 = first_iface.get("x1_mm", 0.0)
            y1 = first_iface.get("y1_mm", 0.0)
            x2 = first_iface.get("x2_mm", 0.0)
            y2 = first_iface.get("y2_mm", 0.0)
            iface_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if iface_len < 1.0:
                iface_len = 25.4  # default 1 inch

            lines.append(f"class {class_name}:")
            lines.append(f'    """Definition for: {item.label} (no 3D model)"""')
            lines.append('    object_group = "optics"')
            lines.append("    object_color = (0.5, 0.5, 0.8)")
            lines.append("    object_transparency = 50")
            lines.append("")
            lines.append("    def shape(self):")
            lines.append(
                f"        return cylinder_shape("
                f"diameter={iface_len:.1f}, height=3.0, "
                f"rotation=(0, 90, 0))"
            )
            lines.append("")
            lines.append("    def interfaces(self):")
            lines.append("        return [")
            for s in iface_strs:
                lines.append(f"            {s},")
            lines.append("        ]")
            lines.append("")
            lines.append("")

    # Layout function
    lines.append("def exported_layout(x=0, y=0, angle=0):")
    lines.append("    bp = Component(")
    lines.append(f'        label="{options.label}",')
    lines.append("        definition=baseplate(")
    lines.append(f'            dimensions=(dim({bp_w:.1f}, "mm"), dim({bp_h:.1f}, "mm"), '
                 f'dim({options.thickness_mm:.1f}, "mm")),')
    lines.append(f'            optical_height=dim({options.optical_height_mm:.1f}, "mm"),')
    lines.append("        ),")
    lines.append("    )")
    lines.append("")

    # Place sources as BeamPaths
    beam_counter = 0
    for item in items:
        if not item.is_source:
            continue
        beam_counter += 1
        bx = item.x_mm - x_off
        by = item.y_mm - y_off
        rot = _optiverse_angle_to_pyopticl(item.angle_deg)
        lines.append(f"    beam_{beam_counter} = bp.add(")
        lines.append(
            f'        BeamPath(label="{item.label}", wavelength={item.wavelength_nm:.0f}),'
        )
        lines.append(f"        position=({bx:.2f}, {by:.2f}, 0),")
        lines.append(f"        rotation={rot:.2f},")
        lines.append("    )")
        lines.append("")

    # Place components
    for idx, item in enumerate(items):
        if item.is_source:
            continue
        cx = item.x_mm - x_off
        cy = item.y_mm - y_off
        rot = _optiverse_angle_to_pyopticl(item.angle_deg)

        if idx in comp_class_map:
            lines.append("    bp.add(")
            lines.append(f'        Component(label="{item.label}", '
                         f'definition={comp_class_map[idx]}()),')
            lines.append(f"        position=({cx:.2f}, {cy:.2f}, 0),")
            lines.append(f"        rotation={rot:.2f},")
            lines.append("    )")
        else:
            lines.append(
                f"    # SKIPPED: {item.label} (no STEP file or interfaces)"
            )
        lines.append("")

    lines.append("    return bp")
    lines.append("")
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    exported_layout().recompute()")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full export orchestration
# ---------------------------------------------------------------------------


def export_scene(
    scene_data: dict[str, Any],
    export_dir: str,
    options: BaseplateOptions,
) -> tuple[bool, list[str]]:
    """Export an Optiverse scene to a PyOpticL layout folder.

    Produces the folder layout expected by ``PyOpticL.utils.import_model``:

        <export_dir>/<export_dir_name>.py
        <export_dir>/models/<stem>/<stem>.step
        <export_dir>/models/<stem>/<stem>.json

    The per-model ``.json`` file is required by PyOpticL and stores the
    translation/rotation applied to the imported mesh; Optiverse has no
    additional STEP orientation data, so identity transforms are written.

    Args:
        scene_data: Serialised scene dict (from SceneFileManager.serialize_scene).
        export_dir: Destination folder. Created if it doesn't exist.
        options: Baseplate configuration.

    Returns:
        ``(success, warnings)`` where warnings lists component names that were
        skipped due to missing STEP files.
    """
    items, warnings = analyse_scene(scene_data)

    script = generate_script(items, options)

    folder_name = os.path.basename(os.path.normpath(export_dir)) or "pyopticl_export"
    script_path = os.path.join(export_dir, f"{_sanitize_stem(folder_name)}.py")
    models_root = os.path.join(export_dir, "models")

    try:
        os.makedirs(export_dir, exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
    except OSError:
        _logger.exception("Failed to write PyOpticL script: %s", script_path)
        return False, warnings

    for item in items:
        if not item.step_file_path:
            _logger.info("STEP skip (no path): %s", item.label)
            continue
        if not os.path.isfile(item.step_file_path):
            _logger.info(
                "STEP skip (file missing): %s -> %s",
                item.label, item.step_file_path,
            )
            continue
        stem = _sanitize_stem(os.path.splitext(item.step_filename or "part")[0])
        model_dir = os.path.join(models_root, stem)
        try:
            os.makedirs(model_dir, exist_ok=True)
            shutil.copy2(item.step_file_path, os.path.join(model_dir, f"{stem}.step"))
            _logger.info("STEP copied: %s -> %s", item.label, model_dir)
            with open(os.path.join(model_dir, f"{stem}.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "translation": [0.0, 0.0, 0.0],
                        "rotation": [0.0, 0.0, 0.0],
                        "_note": (
                            "Run PyOpticL 'Get Orientation' in FreeCAD"
                            " to set correct values"
                        ),
                    },
                    f,
                    indent=2,
                )
        except OSError:
            _logger.warning("Could not write model files for: %s", item.step_file_path)

    return True, warnings
