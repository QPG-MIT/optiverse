"""
Polymorphic optical element implementations.

Each element type implements the IOpticalElement interface.
"""

# No imports needed - types are only used in type hints elsewhere

from .base import IOpticalElement
from .beamsplitter import BeamsplitterElement
from .dichroic import DichroicElement
from .lens import LensElement
from .mirror import MirrorElement
from .refractive import RefractiveElement
from .waveplate import WaveplateElement


# Wrapper classes that accept OpticalInterface and store curved geometry
class Mirror(MirrorElement):
    """Mirror that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            reflectivity=optical_iface.properties.reflectivity,
        )


class Lens(LensElement):
    """Lens that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            efl_mm=optical_iface.properties.efl_mm,
        )


class RefractiveInterfaceElement(RefractiveElement):
    """Refractive interface that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            n1=optical_iface.properties.n1,
            n2=optical_iface.properties.n2,
        )


class Beamsplitter(BeamsplitterElement):
    """Beamsplitter that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            transmission=optical_iface.properties.transmission,
            reflection=optical_iface.properties.reflection,
            is_polarizing=optical_iface.properties.is_polarizing,
            polarization_axis_deg=optical_iface.properties.polarization_axis_deg,
        )


class Waveplate(WaveplateElement):
    """Waveplate that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            phase_shift_deg=optical_iface.properties.phase_shift_deg,
            fast_axis_deg=optical_iface.properties.fast_axis_deg,
        )


class Dichroic(DichroicElement):
    """Dichroic that accepts OpticalInterface with curved geometry support."""

    def __init__(self, optical_iface):
        self._geometry = optical_iface.geometry
        self.interface = optical_iface
        super().__init__(
            p1=optical_iface.geometry.p1,
            p2=optical_iface.geometry.p2,
            cutoff_wavelength_nm=optical_iface.properties.cutoff_wavelength_nm,
            transition_width_nm=optical_iface.properties.transition_width_nm,
            pass_type=optical_iface.properties.pass_type,
        )


__all__ = [
    "IOpticalElement",
    # Base element classes
    "MirrorElement",
    "LensElement",
    "RefractiveElement",
    "BeamsplitterElement",
    "WaveplateElement",
    "DichroicElement",
    # Wrapper classes with curved geometry support
    "Mirror",
    "Lens",
    "RefractiveInterfaceElement",
    "Beamsplitter",
    "Waveplate",
    "Dichroic",
]
