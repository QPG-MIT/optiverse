from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import numpy as np


@dataclass
class Polarization:
    """
    Represents polarization state using Jones vector formalism.
    Jones vector: [Ex, Ey] complex amplitudes in horizontal and vertical directions.
    
    Common polarization states:
    - Horizontal: (1, 0)
    - Vertical: (0, 1)
    - +45°: (1, 1)/√2
    - -45°: (1, -1)/√2
    - Right circular: (1, 1j)/√2
    - Left circular: (1, -1j)/√2
    """
    jones_vector: np.ndarray  # 2-element complex array [Ex, Ey]
    
    def __post_init__(self):
        """Ensure jones_vector is a proper complex numpy array."""
        if not isinstance(self.jones_vector, np.ndarray):
            self.jones_vector = np.array(self.jones_vector, dtype=complex)
        if self.jones_vector.shape != (2,):
            raise ValueError(f"Jones vector must be 2-element array, got shape {self.jones_vector.shape}")
    
    @classmethod
    def horizontal(cls) -> 'Polarization':
        """Create horizontal linear polarization."""
        return cls(np.array([1.0, 0.0], dtype=complex))
    
    @classmethod
    def vertical(cls) -> 'Polarization':
        """Create vertical linear polarization."""
        return cls(np.array([0.0, 1.0], dtype=complex))
    
    @classmethod
    def diagonal_plus_45(cls) -> 'Polarization':
        """Create +45° linear polarization."""
        return cls(np.array([1.0, 1.0], dtype=complex) / np.sqrt(2))
    
    @classmethod
    def diagonal_minus_45(cls) -> 'Polarization':
        """Create -45° linear polarization."""
        return cls(np.array([1.0, -1.0], dtype=complex) / np.sqrt(2))
    
    @classmethod
    def circular_right(cls) -> 'Polarization':
        """Create right circular polarization."""
        return cls(np.array([1.0, 1j], dtype=complex) / np.sqrt(2))
    
    @classmethod
    def circular_left(cls) -> 'Polarization':
        """Create left circular polarization."""
        return cls(np.array([1.0, -1j], dtype=complex) / np.sqrt(2))
    
    @classmethod
    def linear(cls, angle_deg: float) -> 'Polarization':
        """Create linear polarization at specified angle (degrees from horizontal)."""
        angle_rad = np.deg2rad(angle_deg)
        return cls(np.array([np.cos(angle_rad), np.sin(angle_rad)], dtype=complex))
    
    def normalize(self) -> 'Polarization':
        """Return normalized polarization state."""
        norm = np.linalg.norm(self.jones_vector)
        if norm > 0:
            return Polarization(self.jones_vector / norm)
        return self
    
    def intensity(self) -> float:
        """Calculate total intensity (squared magnitude)."""
        return float(np.abs(np.vdot(self.jones_vector, self.jones_vector)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "Ex_real": float(self.jones_vector[0].real),
            "Ex_imag": float(self.jones_vector[0].imag),
            "Ey_real": float(self.jones_vector[1].real),
            "Ey_imag": float(self.jones_vector[1].imag),
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Polarization':
        """Deserialize from dictionary."""
        ex = complex(d.get("Ex_real", 1.0), d.get("Ex_imag", 0.0))
        ey = complex(d.get("Ey_real", 0.0), d.get("Ey_imag", 0.0))
        return cls(np.array([ex, ey], dtype=complex))


@dataclass
class ComponentRecord:
    """
    Persistent component data for library storage.
    Represents a physical optical component with calibrated dimensions.
    
    NORMALIZED 1000px COORDINATE SYSTEM:
    - line_px coordinates are in normalized 1000px space (regardless of actual image size)
    - object_height_mm represents the physical size of the optical element (picked line)
    - When rendering, line_px must be denormalized: actual_coords = line_px * (actual_image_height / 1000.0)
    - mm_per_pixel is then computed as: object_height_mm / picked_line_length_actual_px
    - Images saved by the component editor are normalized to 1000px height, but legacy images may vary
    """
    name: str
    kind: str  # 'lens' | 'mirror' | 'beamsplitter' | 'waveplate' | 'dichroic'
    image_path: str
    line_px: Tuple[float, float, float, float]  # x1,y1,x2,y2 in normalized 1000px coordinate space
    object_height_mm: float  # Physical size (mm) of the optical element (picked line length in mm)
    # mm_per_pixel is computed at render time: object_height_mm / picked_line_length_actual_px (not stored)
    # lens only
    efl_mm: float = 0.0
    # beamsplitter only
    split_TR: Tuple[float, float] = (50.0, 50.0)
    # waveplate only
    phase_shift_deg: float = 90.0  # Phase shift in degrees (90° for QWP, 180° for HWP)
    fast_axis_deg: float = 0.0  # Fast axis angle in lab frame (degrees)
    # dichroic only
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength for dichroic mirrors
    transition_width_nm: float = 50.0  # Width of transition region
    # optical axis angle (degrees) - default orientation when placed
    angle_deg: float = 0.0
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
    # mm_per_pixel not stored - computed at render time from object_height_mm and actual image dimensions
    base = {
        "name": rec.name,
        "kind": rec.kind,
        "image_path": rec.image_path,
        "line_px": [float(x) for x in rec.line_px],
        "object_height_mm": float(rec.object_height_mm),
        "angle_deg": float(rec.angle_deg),  # Optical axis angle
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
    elif rec.kind == "waveplate":
        base["phase_shift_deg"] = float(rec.phase_shift_deg)
        base["fast_axis_deg"] = float(rec.fast_axis_deg)
    elif rec.kind == "dichroic":
        base["cutoff_wavelength_nm"] = float(rec.cutoff_wavelength_nm)
        base["transition_width_nm"] = float(rec.transition_width_nm)
    # mirror: no extra fields
    return base


def deserialize_component(data: Dict[str, Any]) -> Optional[ComponentRecord]:
    """
    Deserialize dict to ComponentRecord.
    Handles both new split_TR and legacy split_T/split_R formats.
    Handles both object_height_mm and legacy object_height/length_mm.
    Ignores unknown keys. Returns None if core fields are malformed.
    """
    if not isinstance(data, dict):
        return None

    name = str(data.get("name", "") or "(unnamed)")
    kind = str(data.get("kind", "lens"))
    image_path = str(data.get("image_path", ""))
    
    # Legacy: mm_per_pixel is no longer used - computed at render time from object_height_mm
    # Old JSON files with mm_per_pixel are ignored

    line_px = _coerce_line_px(data.get("line_px", (0, 0, 1, 0)))
    if not line_px:
        # Core geometry missing → invalid
        return None

    # Support legacy field names: object_height_mm (new) or object_height or length_mm (legacy)
    try:
        object_height_mm = float(data.get("object_height_mm", data.get("object_height", data.get("length_mm", 60.0))))
    except Exception:
        object_height_mm = 60.0
    
    try:
        angle_deg = float(data.get("angle_deg", 0.0))
    except Exception:
        angle_deg = 0.0
    
    notes = str(data.get("notes", ""))

    # Type-specific
    efl_mm = 0.0
    split_TR = (50.0, 50.0)
    phase_shift_deg = 90.0
    fast_axis_deg = 0.0
    cutoff_wavelength_nm = 550.0
    transition_width_nm = 50.0

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
    elif kind == "waveplate":
        try:
            phase_shift_deg = float(data.get("phase_shift_deg", 90.0))
        except Exception:
            phase_shift_deg = 90.0
        try:
            fast_axis_deg = float(data.get("fast_axis_deg", 0.0))
        except Exception:
            fast_axis_deg = 0.0
    elif kind == "dichroic":
        try:
            cutoff_wavelength_nm = float(data.get("cutoff_wavelength_nm", 550.0))
        except Exception:
            cutoff_wavelength_nm = 550.0
        try:
            transition_width_nm = float(data.get("transition_width_nm", 50.0))
        except Exception:
            transition_width_nm = 50.0

    return ComponentRecord(
        name=name,
        kind=kind,
        image_path=image_path,
        line_px=line_px,
        object_height_mm=object_height_mm,
        efl_mm=efl_mm,
        split_TR=split_TR,
        phase_shift_deg=phase_shift_deg,
        fast_axis_deg=fast_axis_deg,
        cutoff_wavelength_nm=cutoff_wavelength_nm,
        transition_width_nm=transition_width_nm,
        angle_deg=angle_deg,
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
    # Wavelength (in nanometers) - if 0, use color_hex directly
    wavelength_nm: float = 0.0  # 0 = use color_hex, >0 = compute color from wavelength
    # Polarization parameters
    polarization_type: str = "horizontal"  # horizontal, vertical, +45, -45, circular_right, circular_left, linear
    polarization_angle_deg: float = 0.0  # Used when polarization_type is "linear"
    # Custom Jones vector (optional override)
    custom_jones_ex_real: float = 1.0
    custom_jones_ex_imag: float = 0.0
    custom_jones_ey_real: float = 0.0
    custom_jones_ey_imag: float = 0.0
    use_custom_jones: bool = False
    
    def get_polarization(self) -> Polarization:
        """Get Polarization object based on current parameters."""
        if self.use_custom_jones:
            ex = complex(self.custom_jones_ex_real, self.custom_jones_ex_imag)
            ey = complex(self.custom_jones_ey_real, self.custom_jones_ey_imag)
            return Polarization(np.array([ex, ey], dtype=complex))
        
        pol_type = self.polarization_type.lower()
        if pol_type == "horizontal":
            return Polarization.horizontal()
        elif pol_type == "vertical":
            return Polarization.vertical()
        elif pol_type == "+45":
            return Polarization.diagonal_plus_45()
        elif pol_type == "-45":
            return Polarization.diagonal_minus_45()
        elif pol_type == "circular_right":
            return Polarization.circular_right()
        elif pol_type == "circular_left":
            return Polarization.circular_left()
        elif pol_type == "linear":
            return Polarization.linear(self.polarization_angle_deg)
        else:
            return Polarization.horizontal()  # Default fallback


@dataclass
class LensParams:
    x_mm: float = -150.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    efl_mm: float = 100.0
    object_height_mm: float = 60.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class MirrorParams:
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class SLMParams:
    """Spatial Light Modulator parameters (acts as a mirror)."""
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    object_height_mm: float = 80.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class BeamsplitterParams:
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    split_T: float = 50.0
    split_R: float = 50.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None
    # Polarization properties
    is_polarizing: bool = False  # True for PBS (Polarizing Beam Splitter)
    # For PBS: s-polarization (perpendicular) reflects, p-polarization (parallel) transmits
    pbs_transmission_axis_deg: float = 0.0  # ABSOLUTE angle of transmission axis in lab frame (degrees)


@dataclass
class WaveplateParams:
    """
    Waveplate component parameters.
    
    Waveplates introduce a phase shift between orthogonal polarization components.
    - Quarter waveplate (QWP): π/2 phase shift (90°)
    - Half waveplate (HWP): π phase shift (180°)
    
    The fast axis is the axis along which light travels faster (lower refractive index).
    The slow axis is perpendicular to the fast axis.
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 90.0  # Orientation of the waveplate element
    object_height_mm: float = 36.6  # Physical size of optical element
    phase_shift_deg: float = 90.0  # Phase shift in degrees (90° for QWP, 180° for HWP)
    fast_axis_deg: float = 0.0  # ABSOLUTE angle of fast axis in lab frame (degrees)
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class DichroicParams:
    """
    Dichroic mirror component parameters.
    
    Dichroic mirrors selectively reflect or transmit light based on wavelength.
    Typically:
    - Short wavelengths (< cutoff) reflect
    - Long wavelengths (> cutoff) transmit
    
    The transition is smooth with a characteristic width.
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0  # Typically 45° for beam combining/splitting
    object_height_mm: float = 80.0  # Physical size of optical element
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength (nm) - green
    transition_width_nm: float = 50.0  # Width of transition region (nm)
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class OpticalElement:
    kind: str  # 'lens' | 'mirror' | 'bs' | 'waveplate' | 'dichroic'
    p1: np.ndarray
    p2: np.ndarray
    efl_mm: float = 0.0
    split_T: float = 50.0
    split_R: float = 50.0
    # Polarization properties
    is_polarizing: bool = False  # For PBS mode
    pbs_transmission_axis_deg: float = 0.0  # PBS transmission axis angle
    # Waveplate properties
    phase_shift_deg: float = 90.0  # Phase shift for waveplates
    fast_axis_deg: float = 0.0  # Fast axis angle for waveplates
    # Dichroic properties
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength for dichroic mirrors
    transition_width_nm: float = 50.0  # Width of transition region


@dataclass
class RayPath:
    points: List[np.ndarray]
    rgba: Tuple[int, int, int, int]  # color with alpha
    polarization: Optional[Polarization] = None  # Polarization state of this ray
    wavelength_nm: float = 0.0  # Wavelength in nanometers (0 = not specified)


