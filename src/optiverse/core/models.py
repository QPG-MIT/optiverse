from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

from .interface_definition import InterfaceDefinition

# Import path utilities for relative/absolute path conversion
from ..platform.paths import (
    to_relative_path,
    to_absolute_path,
    make_library_relative,
    get_all_library_roots
)


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

    INTERFACE-BASED DESIGN:
    - Component can contain multiple interfaces, each with its own type
    - interfaces: List of InterfaceDefinition objects
    - Coordinates stored in mm in local coordinate system (centered, Y-up)
    - Interfaces can be reordered, optical effect determined by spatial position
    - First interface is used as reference line for sprite positioning

    COORDINATE SYSTEMS:
    - interfaces[].xN_mm: Millimeters in local coordinate system
    - object_height_mm: Physical size for calibration (mm)
    """
    name: str
    image_path: str = ""
    object_height_mm: float = 25.4  # Physical size (mm) of the optical element

    # Interface-based format
    interfaces: Optional[List] = None  # List[InterfaceDefinition] when available

    # Common properties
    angle_deg: float = 0.0  # optical axis angle (degrees)
    category: str = ""  # Component category (e.g., "background", "lenses", "mirrors")
    notes: str = ""


def serialize_component(rec: ComponentRecord, settings_service=None) -> Dict[str, Any]:
    """
    Serialize ComponentRecord to dict for JSON storage.

    Image paths are stored using the following priority:
    1. Library-relative format (@library/...) if within a configured library
    2. Package-relative format if within the package (built-in components)
    3. Absolute path as fallback

    This makes assemblies portable across different computers while maintaining
    backward compatibility with absolute paths.

    Args:
        rec: ComponentRecord to serialize
        settings_service: Optional SettingsService for loading library paths

    Returns:
        Dictionary with serialized component data
    """
    # Determine best path format for image
    image_path_serialized = ""
    if rec.image_path:
        # Try library-relative first (makes assemblies portable)
        library_roots = get_all_library_roots(settings_service)
        library_relative = make_library_relative(rec.image_path, library_roots)

        if library_relative:
            # Use library-relative format
            image_path_serialized = library_relative
        else:
            # Fall back to package-relative (for built-in components)
            image_path_serialized = to_relative_path(rec.image_path)

    base = {
        "name": rec.name,
        "image_path": image_path_serialized,
        "object_height_mm": float(rec.object_height_mm),
        "angle_deg": float(rec.angle_deg),
        "notes": rec.notes or "",
    }

    # Include category if present
    if rec.category:
        base["category"] = rec.category

    # Serialize interfaces
    if rec.interfaces:
        base["interfaces"] = [iface.to_dict() for iface in rec.interfaces]

    return base


def deserialize_component(data: Dict[str, Any], settings_service=None) -> Optional[ComponentRecord]:
    """
    Deserialize dict to ComponentRecord.

    Image paths are converted to absolute paths using the following resolution:
    1. Library-relative (@library/...) resolved against configured libraries
    2. Package-relative resolved against package root
    3. Absolute paths used as-is (backward compatibility)

    Args:
        data: Dictionary with component data
        settings_service: Optional SettingsService for loading library paths

    Returns:
        ComponentRecord if successful, None otherwise
    """
    if not isinstance(data, dict):
        return None

    # Common fields
    name = str(data.get("name", "") or "(unnamed)")
    image_path_raw = str(data.get("image_path", ""))

    # Convert paths to absolute
    if image_path_raw:
        library_roots = get_all_library_roots(settings_service)
        image_path = to_absolute_path(image_path_raw, library_roots)
    else:
        image_path = ""

    try:
        object_height_mm = float(data.get("object_height_mm", 25.4))
    except (TypeError, ValueError):
        object_height_mm = 25.4

    try:
        angle_deg = float(data.get("angle_deg", 0.0))
    except (TypeError, ValueError):
        angle_deg = 0.0

    category = str(data.get("category", ""))
    notes = str(data.get("notes", ""))

    # Deserialize interfaces (single current schema, Y-up; no legacy fallback)
    interfaces: List[InterfaceDefinition] = []
    interfaces_data = data.get("interfaces")
    if isinstance(interfaces_data, list):
        interfaces = [InterfaceDefinition.from_dict(iface_data) for iface_data in interfaces_data if isinstance(iface_data, dict)]

    return ComponentRecord(
        name=name,
        image_path=image_path,
        object_height_mm=object_height_mm,
        interfaces=interfaces,
        angle_deg=angle_deg,
        category=category,
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
class BaseOpticalParams:
    """
    Base class for optical component parameters.

    Contains common fields shared by all optical components:
    - Position (x_mm, y_mm)
    - Orientation (angle_deg)
    - Physical size (object_height_mm, mm_per_pixel)
    - Display (name, image_path)
    - Interfaces

    Subclasses add component-specific fields (efl_mm for lenses, split_T/R for
    beamsplitters, etc.)
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    object_height_mm: float = 60.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    name: Optional[str] = None
    interfaces: Optional[List] = None  # List[InterfaceDefinition] when available

    def __post_init__(self):
        """Ensure interfaces list exists."""
        if self.interfaces is None:
            self.interfaces = []


@dataclass
class LensParams(BaseOpticalParams):
    """Lens parameters with effective focal length."""
    x_mm: float = -150.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    object_height_mm: float = 60.0
    efl_mm: float = 100.0  # Effective focal length


@dataclass
class MirrorParams(BaseOpticalParams):
    """Mirror parameters."""
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0


@dataclass
class BlockParams(BaseOpticalParams):
    """Beam block parameters."""
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    object_height_mm: float = 80.0


@dataclass
class SLMParams(BaseOpticalParams):
    """Spatial Light Modulator parameters (acts as a mirror)."""
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    object_height_mm: float = 80.0


@dataclass
class BeamsplitterParams(BaseOpticalParams):
    """Beamsplitter parameters with transmission/reflection ratios."""
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    split_T: float = 50.0  # Transmission ratio (%)
    split_R: float = 50.0  # Reflection ratio (%)
    is_polarizing: bool = False  # True for PBS (Polarizing Beam Splitter)
    pbs_transmission_axis_deg: float = 0.0  # PBS transmission axis angle (degrees)


@dataclass
class WaveplateParams(BaseOpticalParams):
    """
    Waveplate parameters.

    Waveplates introduce a phase shift between orthogonal polarization components.
    - Quarter waveplate (QWP): 90° phase shift
    - Half waveplate (HWP): 180° phase shift
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    object_height_mm: float = 36.6
    phase_shift_deg: float = 90.0  # Phase shift (90° for QWP, 180° for HWP)
    fast_axis_deg: float = 0.0  # Fast axis angle (degrees)


@dataclass
class DichroicParams(BaseOpticalParams):
    """
    Dichroic mirror parameters.

    Selectively reflects or transmits light based on wavelength:
    - Long pass: reflects short wavelengths, transmits long
    - Short pass: reflects long wavelengths, transmits short
    """
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    cutoff_wavelength_nm: float = 550.0  # Cutoff wavelength (nm)
    transition_width_nm: float = 50.0  # Transition width (nm)
    pass_type: str = "longpass"  # "longpass" or "shortpass"


@dataclass
class RefractiveInterface:
    """
    A single refractive interface with refractive indices on both sides.

    This represents a planar surface separating two media with different refractive indices.
    Handles both refraction (Snell's law) and partial reflection (Fresnel equations).

    COORDINATE SYSTEM:
    - Origin (0,0) is at the IMAGE CENTER
    - X-axis: positive right, negative left
    - Y-axis: positive UP, negative DOWN (Y-up, mathematical convention)
    - Units: millimeters

    Note: This matches the InterfaceDefinition coordinate system (Y-up, centered).
    Conversion to Qt's Y-down display happens in ComponentSprite.
    """
    # Interface geometry in local coordinates relative to image center (Y-up, mm)
    x1_mm: float = 0.0  # Start point x
    y1_mm: float = 0.0  # Start point y
    x2_mm: float = 0.0  # End point x
    y2_mm: float = 0.0  # End point y
    # Refractive indices
    n1: float = 1.0  # Refractive index on the "left" side (ray coming from this side)
    n2: float = 1.5  # Refractive index on the "right" side (ray going to this side)
    # Curved surface properties (for Zemax import)
    is_curved: bool = False  # True if this is a curved surface
    radius_of_curvature_mm: float = 0.0  # Radius of curvature (+ or -, 0 = flat)
    # Special properties
    is_beam_splitter: bool = False  # If True, apply beam splitting logic
    split_T: float = 50.0  # Transmission ratio for beam splitter interface
    split_R: float = 50.0  # Reflection ratio for beam splitter interface
    is_polarizing: bool = False  # If True, acts as PBS
    pbs_transmission_axis_deg: float = 0.0  # PBS axis for polarizing interface


@dataclass
class ComponentParams:
    """
    Universal component parameters for any optical component.

    Supports any combination of interface types. Each interface
    behaves independently based on its element_type.

    The component is just a container/grouping mechanism - the
    optical behavior is determined by individual interfaces.
    """
    # Position and orientation
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 0.0

    # Physical properties
    object_height_mm: float = 60.0
    mm_per_pixel: float = 0.1

    # Display properties
    name: Optional[str] = None
    image_path: Optional[str] = None

    # Sprite positioning - reference line in mm coordinates (x1, y1, x2, y2)
    # Used to align the sprite to the optical axis. If None, computed from first interface.
    reference_line_mm: Optional[Tuple[float, float, float, float]] = None

    # Optical interfaces (InterfaceDefinition objects)
    interfaces: Optional[List] = None  # List[InterfaceDefinition] when available

    # Metadata
    category: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Ensure interfaces list exists."""
        if self.interfaces is None:
            self.interfaces = []


@dataclass
class RefractiveObjectParams:
    """
    Refractive object with multiple optical interfaces.

    This represents a complex optical component like a beam splitter cube, prism,
    or any object with multiple refracting surfaces. Each interface is defined
    in local coordinates relative to the component's origin.

    The first interface is used as the reference line for sprite positioning.
    """
    x_mm: float = 0.0  # Component center position
    y_mm: float = 0.0
    angle_deg: float = 45.0  # Component rotation
    object_height_mm: float = 80.0  # Physical size for rendering
    interfaces: List['RefractiveInterface'] = None  # List of refractive interfaces
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
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




