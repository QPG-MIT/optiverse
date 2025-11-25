"""
Pure Python raytracing engine using polymorphism.

This module provides a clean, polymorphic raytracing implementation with
no UI dependencies. Can be used independently or in background threads.

Architecture:
    - Ray: Data structure for ray state
    - RayPath: Data structure for traced path
    - Polarization: Jones vector formalism
    - IOpticalElement: Interface for all optical elements
    - Concrete elements: Mirror, Lens, Refractive, Beamsplitter, Waveplate, Dichroic
    - trace_rays_polymorphic: Main raytracing engine (O(n) per ray)
"""

from .ray import Ray, RayPath, Polarization
from .elements.base import IOpticalElement, RayIntersection
from .elements import (
    Mirror,
    Lens,
    RefractiveInterfaceElement,
    Beamsplitter,
    Waveplate,
    Dichroic
)
from .engine import trace_rays_polymorphic

__all__ = [
    # Ray data structures
    "Ray",
    "RayPath",
    "Polarization",
    # Element interface and implementations
    "IOpticalElement",
    "RayIntersection",
    "Mirror",
    "Lens",
    "RefractiveInterfaceElement",
    "Beamsplitter",
    "Waveplate",
    "Dichroic",
    # Raytracing engine
    "trace_rays_polymorphic",
]



