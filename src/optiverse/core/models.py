from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import numpy as np


@dataclass
class ComponentRecord:
    """
    Persistent component data for library storage.
    Represents a physical optical component with calibrated dimensions.
    """
    name: str
    kind: str  # 'lens' | 'mirror' | 'beamsplitter'
    image_path: str
    mm_per_pixel: float
    line_px: Tuple[float, float, float, float]  # x1,y1,x2,y2 (logical px)
    length_mm: float
    # lens only
    efl_mm: float = 0.0
    # beamsplitter only
    split_TR: Tuple[float, float] = (50.0, 50.0)
    # misc
    notes: str = ""


def _coerce_line_px(val: Any) -> Optional[Tuple[float, float, float, float]]:
    """Convert various line_px formats to canonical tuple."""
    try:
        if isinstance(val, (list, tuple)) and len(val) == 4:
            return (float(val[0]), float(val[1]), float(val[2]), float(val[3]))
    except Exception:
        pass
    return None


def serialize_component(rec: ComponentRecord) -> Dict[str, Any]:
    """
    Serialize ComponentRecord to dict for JSON storage.
    Only includes fields relevant to component kind.
    For beamsplitter, also writes legacy split_T/split_R for backward compatibility.
    """
    base = {
        "name": rec.name,
        "kind": rec.kind,
        "image_path": rec.image_path,
        "mm_per_pixel": float(rec.mm_per_pixel),
        "line_px": [float(x) for x in rec.line_px],
        "length_mm": float(rec.length_mm),
        "notes": rec.notes or ""
    }
    if rec.kind == "lens":
        base["efl_mm"] = float(rec.efl_mm)
    elif rec.kind == "beamsplitter":
        t, r = rec.split_TR
        base["split_TR"] = [float(t), float(r)]
        # Legacy for backward compatibility
        base["split_T"] = float(t)
        base["split_R"] = float(r)
    # mirror: no extra fields
    return base


def deserialize_component(data: Dict[str, Any]) -> Optional[ComponentRecord]:
    """
    Deserialize dict to ComponentRecord.
    Handles both new split_TR and legacy split_T/split_R formats.
    Ignores unknown keys. Returns None if core fields are malformed.
    """
    if not isinstance(data, dict):
        return None

    name = str(data.get("name", "") or "(unnamed)")
    kind = str(data.get("kind", "lens"))
    image_path = str(data.get("image_path", ""))
    
    try:
        mm_per_pixel = float(data.get("mm_per_pixel", 0.1))
    except Exception:
        mm_per_pixel = 0.1

    line_px = _coerce_line_px(data.get("line_px", (0, 0, 1, 0)))
    if not line_px:
        # Core geometry missing → invalid
        return None

    try:
        length_mm = float(data.get("length_mm", 60.0))
    except Exception:
        length_mm = 60.0
    
    notes = str(data.get("notes", ""))

    # Type-specific
    efl_mm = 0.0
    split_TR = (50.0, 50.0)

    if kind == "lens":
        try:
            efl_mm = float(data.get("efl_mm", 0.0))
        except Exception:
            efl_mm = 0.0
    elif kind == "beamsplitter":
        if "split_TR" in data and isinstance(data["split_TR"], (list, tuple)) and len(data["split_TR"]) == 2:
            try:
                split_TR = (float(data["split_TR"][0]), float(data["split_TR"][1]))
            except Exception:
                split_TR = (50.0, 50.0)
        else:
            # Legacy keys
            try:
                t = float(data.get("split_T", 50.0))
                r = float(data.get("split_R", 50.0))
                split_TR = (t, r)
            except Exception:
                split_TR = (50.0, 50.0)

    return ComponentRecord(
        name=name,
        kind=kind,
        image_path=image_path,
        mm_per_pixel=mm_per_pixel,
        line_px=line_px,
        length_mm=length_mm,
        efl_mm=efl_mm,
        split_TR=split_TR,
        notes=notes
    )


@dataclass
class SourceParams:
    x_mm: float = -400.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    size_mm: float = 10.0
    n_rays: int = 9
    ray_length_mm: float = 1000.0
    spread_deg: float = 0.0
    color_hex: str = "#DC143C"  # crimson default


@dataclass
class LensParams:
    x_mm: float = -150.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    efl_mm: float = 100.0
    length_mm: float = 60.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class MirrorParams:
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    length_mm: float = 80.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class BeamsplitterParams:
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    length_mm: float = 80.0
    split_T: float = 50.0
    split_R: float = 50.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class OpticalElement:
    kind: str  # 'lens' | 'mirror' | 'bs'
    p1: np.ndarray
    p2: np.ndarray
    efl_mm: float = 0.0
    split_T: float = 50.0
    split_R: float = 50.0


@dataclass
class RayPath:
    points: List[np.ndarray]
    rgba: Tuple[int, int, int, int]  # color with alpha


