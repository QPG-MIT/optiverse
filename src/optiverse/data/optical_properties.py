"""
Optical properties for different interface types.

Type-safe property classes that can be used with Union types for
compile-time type checking.
"""
from dataclasses import dataclass
from typing import Union, Optional


@dataclass
class RefractiveProperties:
    """
    Properties for a refractive interface (Snell's law + Fresnel equations).

    Represents a boundary between two media with different refractive indices.
    """
    n1: float  # Refractive index on "left" side
    n2: float  # Refractive index on "right" side
    curvature_radius_mm: Optional[float] = None  # Radius of curvature (None or 0 = flat)


@dataclass
class LensProperties:
    """
    Properties for a thin lens (paraxial approximation).

    Uses the thin lens equation: 1/f = 1/s_o + 1/s_i
    """
    efl_mm: float  # Effective focal length in millimeters


@dataclass
class MirrorProperties:
    """
    Properties for a reflective surface (mirror).

    Follows the law of reflection: angle of incidence = angle of reflection.
    """
    reflectivity: float = 1.0  # Reflectivity (0.0 to 1.0)


@dataclass
class BeamsplitterProperties:
    """
    Properties for a beamsplitter (partial reflection + transmission).

    Can be non-polarizing (splits by intensity) or polarizing (PBS - splits by polarization).
    """
    transmission: float  # Transmission coefficient (0.0 to 1.0)
    reflection: float    # Reflection coefficient (0.0 to 1.0)
    is_polarizing: bool = False  # True for PBS (Polarizing Beam Splitter)
    polarization_axis_deg: float = 0.0  # Transmission axis angle for PBS (degrees)


@dataclass
class WaveplateProperties:
    """
    Properties for a waveplate (introduces phase shift between polarization components).

    Common types:
    - Quarter waveplate (QWP): phase_shift_deg = 90.0
    - Half waveplate (HWP): phase_shift_deg = 180.0
    """
    phase_shift_deg: float  # Phase shift in degrees (90° for QWP, 180° for HWP)
    fast_axis_deg: float    # Fast axis angle in lab frame (degrees)


@dataclass
class DichroicProperties:
    """
    Properties for a dichroic mirror (wavelength-dependent reflection/transmission).

    Reflects short wavelengths and transmits long wavelengths (longpass) or vice versa (shortpass).
    """
    cutoff_wavelength_nm: float    # Cutoff wavelength in nanometers
    transition_width_nm: float     # Width of transition region in nanometers
    pass_type: str                 # "longpass" or "shortpass"


# Union type for type-safe property handling
OpticalProperties = Union[
    RefractiveProperties,
    LensProperties,
    MirrorProperties,
    BeamsplitterProperties,
    WaveplateProperties,
    DichroicProperties,
]



