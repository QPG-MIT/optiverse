from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

# Import new interface definition
try:
    from .interface_definition import InterfaceDefinition
    HAS_INTERFACE_DEFINITION = True
except ImportError:
    HAS_INTERFACE_DEFINITION = False

# Import path utilities for relative/absolute path conversion
from ..platform.paths import to_relative_path, to_absolute_path


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
    
    GENERALIZED INTERFACE-BASED DESIGN (v2):
    - Component can contain multiple interfaces, each with its own type
    - interfaces_v2: List of InterfaceDefinition objects (new format)
    - Coordinates stored in mm in local coordinate system
    - Interfaces can be reordered, optical effect determined by spatial position
    
    LEGACY SUPPORT (v1):
    - kind: Component type (auto-computed from interfaces_v2 if not set)
    - line_px: Calibration line in normalized 1000px space (legacy)
    - Type-specific fields (efl_mm, split_TR, etc.) kept for backward compatibility
    - Legacy components automatically migrated to v2 format on first access
    
    COORDINATE SYSTEMS:
    - line_px: Normalized 1000px space (legacy, still used for simple components)
    - interfaces_v2[].xN_mm: Millimeters in local coordinate system
    - object_height_mm: Physical size for calibration (mm)
    """
    name: str
    image_path: str = ""
    object_height_mm: float = 25.4  # Physical size (mm) of the optical element
    
    # NEW: Interface-based format (v2)
    interfaces_v2: Optional[List] = None  # List[InterfaceDefinition] when available
    
    # LEGACY: Component type and calibration
    kind: str = ""  # Auto-computed from interfaces_v2, or legacy type
    line_px: Tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)
    
    # LEGACY: Type-specific properties (kept for backward compatibility)
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
    pass_type: str = "longpass"  # "longpass" or "shortpass"
    # refractive_object only (old format)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)  # Legacy interface dicts
    
    # Common properties
    angle_deg: float = 0.0  # optical axis angle (degrees)
    notes: str = ""
    
    def __post_init__(self):
        """Initialize and validate component data."""
        # Auto-compute kind from interfaces_v2 if available
        if self.interfaces_v2 is not None and len(self.interfaces_v2) > 0 and not self.kind:
            self.kind = self._compute_kind()
        
        # Ensure kind has a value
        if not self.kind:
            self.kind = "lens"  # Default fallback
    
    def _compute_kind(self) -> str:
        """
        Compute component kind from interfaces_v2.
        
        Returns:
            - Single interface type if only one interface
            - "multi_element" if multiple interfaces
            - "empty" if no interfaces
        """
        if self.interfaces_v2 is None or len(self.interfaces_v2) == 0:
            return "empty"
        elif len(self.interfaces_v2) == 1:
            return self.interfaces_v2[0].element_type
        else:
            return "multi_element"
    
    def is_v2_format(self) -> bool:
        """Check if this component uses the new v2 interface format."""
        return self.interfaces_v2 is not None and len(self.interfaces_v2) > 0


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
    
    Supports both v2 (interface-based) and legacy (type-based) formats.
    V2 format takes precedence if available.
    
    Image paths are stored as relative paths if within the package,
    otherwise as absolute paths.
    """
    base = {
        "name": rec.name,
        "image_path": to_relative_path(rec.image_path),
        "object_height_mm": float(rec.object_height_mm),
        "angle_deg": float(rec.angle_deg),
        "notes": rec.notes or ""
    }
    
    # V2 format: Interface-based (new)
    if rec.is_v2_format() and HAS_INTERFACE_DEFINITION:
        base["format_version"] = 2
        base["interfaces_v2"] = [iface.to_dict() for iface in rec.interfaces_v2]
        # Include computed kind for display
        base["kind"] = rec.kind
    else:
        # Legacy format (v1)
        base["format_version"] = 1
        base["kind"] = rec.kind
        base["line_px"] = [float(x) for x in rec.line_px]
        
        # Type-specific fields
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
            base["pass_type"] = str(rec.pass_type)
        elif rec.kind == "refractive_object":
            # Store interfaces as list of dicts
            base["interfaces"] = rec.interfaces if rec.interfaces else []
        # mirror: no extra fields
    
    return base


def deserialize_component(data: Dict[str, Any]) -> Optional[ComponentRecord]:
    """
    Deserialize dict to ComponentRecord.
    
    Supports both v2 (interface-based) and legacy (v1) formats.
    Automatically migrates legacy components to v2 format if InterfaceDefinition is available.
    Handles backward compatibility with all legacy field names.
    
    Image paths are converted from relative (package-relative) to absolute paths.
    """
    if not isinstance(data, dict):
        return None

    # Detect format version
    format_version = data.get("format_version", 1)
    
    # Common fields
    name = str(data.get("name", "") or "(unnamed)")
    image_path_raw = str(data.get("image_path", ""))
    # Convert relative paths to absolute
    image_path = to_absolute_path(image_path_raw) if image_path_raw else ""
    
    try:
        object_height_mm = float(data.get("object_height_mm", data.get("object_height", data.get("length_mm", 25.4))))
    except Exception:
        object_height_mm = 25.4
    
    try:
        angle_deg = float(data.get("angle_deg", 0.0))
    except Exception:
        angle_deg = 0.0
    
    notes = str(data.get("notes", ""))
    
    # V2 format: Interface-based
    if format_version == 2 and "interfaces_v2" in data and HAS_INTERFACE_DEFINITION:
        try:
            from .interface_definition import InterfaceDefinition
            interfaces_v2 = [InterfaceDefinition.from_dict(iface_data) for iface_data in data["interfaces_v2"]]
            kind = data.get("kind", "multi_element")
        except Exception:
            # Fallback to legacy if v2 loading fails
            interfaces_v2 = None
            kind = data.get("kind", "lens")
        
        return ComponentRecord(
            name=name,
            image_path=image_path,
            object_height_mm=object_height_mm,
            interfaces_v2=interfaces_v2 if interfaces_v2 else None,
            kind=kind,
            angle_deg=angle_deg,
            notes=notes
        )
    
    # Legacy format (v1): Load type-specific fields
    kind = str(data.get("kind", "lens"))
    
    line_px = _coerce_line_px(data.get("line_px", (0, 0, 100, 100)))
    if not line_px:
        line_px = (0.0, 0.0, 100.0, 100.0)
    
    # Type-specific fields
    efl_mm = 0.0
    split_TR = (50.0, 50.0)
    phase_shift_deg = 90.0
    fast_axis_deg = 0.0
    cutoff_wavelength_nm = 550.0
    transition_width_nm = 50.0
    pass_type = "longpass"
    interfaces = []

    if kind == "lens":
        try:
            efl_mm = float(data.get("efl_mm", 100.0))
        except Exception:
            efl_mm = 100.0
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
        try:
            pass_type = str(data.get("pass_type", "longpass"))
        except Exception:
            pass_type = "longpass"
    elif kind == "refractive_object":
        # Load interfaces
        try:
            interfaces = data.get("interfaces", [])
            if not isinstance(interfaces, list):
                interfaces = []
        except Exception:
            interfaces = []

    return ComponentRecord(
        name=name,
        kind=kind,
        image_path=image_path,
        line_px=line_px,
        object_height_mm=object_height_mm,
        interfaces_v2=None,  # Will be populated by migration if needed
        efl_mm=efl_mm,
        split_TR=split_TR,
        phase_shift_deg=phase_shift_deg,
        fast_axis_deg=fast_axis_deg,
        cutoff_wavelength_nm=cutoff_wavelength_nm,
        transition_width_nm=transition_width_nm,
        pass_type=pass_type,
        interfaces=interfaces,
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
    # Wavelength (in nanometers) - used for physics calculations (dichroics, etc.)
    # Display color is always taken from color_hex, independent of wavelength
    wavelength_nm: float = 633.0  # Default: 633nm (HeNe laser, red)
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
    - Long pass: reflects short wavelengths (< cutoff), transmits long wavelengths (> cutoff)
    - Short pass: reflects long wavelengths (> cutoff), transmits short wavelengths (< cutoff)
    
    The transition is smooth with a characteristic width.
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0  # Typically 45° for beam combining/splitting
    object_height_mm: float = 80.0  # Physical size of optical element
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength (nm) - green
    transition_width_nm: float = 50.0  # Width of transition region (nm)
    pass_type: str = "longpass"  # "longpass" or "shortpass"
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None


@dataclass
class RefractiveInterface:
    """
    A single refractive interface with refractive indices on both sides.
    
    This represents a planar surface separating two media with different refractive indices.
    Handles both refraction (Snell's law) and partial reflection (Fresnel equations).
    """
    # Interface geometry in local coordinates relative to component origin
    x1_mm: float = 0.0  # Start point x
    y1_mm: float = 0.0  # Start point y
    x2_mm: float = 0.0  # End point x
    y2_mm: float = 0.0  # End point y
    # Refractive indices
    n1: float = 1.0  # Refractive index on the "left" side (ray coming from this side)
    n2: float = 1.5  # Refractive index on the "right" side (ray going to this side)
    # Special properties
    is_beam_splitter: bool = False  # If True, apply beam splitting logic
    split_T: float = 50.0  # Transmission ratio for beam splitter interface
    split_R: float = 50.0  # Reflection ratio for beam splitter interface
    is_polarizing: bool = False  # If True, acts as PBS
    pbs_transmission_axis_deg: float = 0.0  # PBS axis for polarizing interface


@dataclass
class RefractiveObjectParams:
    """
    Refractive object with multiple optical interfaces.
    
    This represents a complex optical component like a beam splitter cube, prism,
    or any object with multiple refracting surfaces. Each interface is defined
    in local coordinates relative to the component's origin.
    """
    x_mm: float = 0.0  # Component center position
    y_mm: float = 0.0
    angle_deg: float = 45.0  # Component rotation
    object_height_mm: float = 80.0  # Physical size for rendering
    interfaces: List['RefractiveInterface'] = None  # List of refractive interfaces
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None  # Optional reference line for calibration
    name: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default interfaces if none provided."""
        if self.interfaces is None:
            self.interfaces = []


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
    angle_deg: float = 90.0  # Waveplate orientation angle (for directionality detection)
    # Dichroic properties
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength for dichroic mirrors
    transition_width_nm: float = 50.0  # Width of transition region
    pass_type: str = "longpass"  # "longpass" or "shortpass"


@dataclass
class RayPath:
    points: List[np.ndarray]
    rgba: Tuple[int, int, int, int]  # color with alpha
    polarization: Optional[Polarization] = None  # Polarization state of this ray
    wavelength_nm: float = 0.0  # Wavelength in nanometers (0 = not specified)


