"""
Ray data structures for raytracing.

Pure data structures with no UI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core.models import Polarization


@dataclass
class RayState:
    """
    Complete state of a ray during propagation.

    This is a pure data structure with no methods that modify state.
    Immutable pattern: methods return new RayState objects.
    """

    position: np.ndarray  # Current position [x, y] in mm
    direction: np.ndarray  # Normalized direction vector
    intensity: float  # Current intensity (0.0 to 1.0)
    polarization: Polarization  # Jones vector polarization state
    wavelength_nm: float  # Wavelength in nanometers
    path: list[np.ndarray] = field(
        default_factory=list
    )  # List of positions visited (deprecated, use path_points)
    events: int = 0  # Number of interactions so far
    # Additional fields for engine compatibility
    remaining_length: float = 1000.0  # Maximum remaining propagation length in mm
    base_rgb: tuple[int, int, int] = (220, 20, 60)  # Base color as RGB tuple
    path_points: list[np.ndarray] = field(default_factory=list)  # List of points for visualization

    def advance(self, distance: float) -> RayState:
        """
        Create new RayState advanced along direction by distance.

        Args:
            distance: Distance to advance in mm

        Returns:
            New RayState at advanced position
        """
        new_position = self.position + self.direction * distance

        return RayState(
            position=new_position,
            direction=self.direction,
            intensity=self.intensity,
            polarization=self.polarization,
            wavelength_nm=self.wavelength_nm,
            path=self.path + [new_position],
            events=self.events,
        )

    def with_direction(self, new_direction: np.ndarray) -> RayState:
        """Create new RayState with different direction"""
        return RayState(
            position=self.position,
            direction=new_direction,
            intensity=self.intensity,
            polarization=self.polarization,
            wavelength_nm=self.wavelength_nm,
            path=self.path,
            events=self.events,
        )

    def with_intensity(self, new_intensity: float) -> RayState:
        """Create new RayState with different intensity"""
        return RayState(
            position=self.position,
            direction=self.direction,
            intensity=new_intensity,
            polarization=self.polarization,
            wavelength_nm=self.wavelength_nm,
            path=self.path,
            events=self.events,
        )

    def with_polarization(self, new_polarization: Polarization) -> RayState:
        """Create new RayState with different polarization"""
        return RayState(
            position=self.position,
            direction=self.direction,
            intensity=self.intensity,
            polarization=new_polarization,
            wavelength_nm=self.wavelength_nm,
            path=self.path,
            events=self.events,
        )

    def increment_events(self) -> RayState:
        """Create new RayState with events incremented"""
        return RayState(
            position=self.position,
            direction=self.direction,
            intensity=self.intensity,
            polarization=self.polarization,
            wavelength_nm=self.wavelength_nm,
            path=self.path,
            events=self.events + 1,
        )


@dataclass
class RayPath:
    """
    Complete path of a ray for visualization.

    This is the final output format from raytracing.
    """

    points: list[np.ndarray]  # Sequence of points along path
    rgba: tuple[int, int, int, int]  # Color with alpha
    polarization: Polarization  # Final polarization state
    wavelength_nm: float  # Wavelength in nanometers


# Alias for backward compatibility and simpler imports
Ray = RayState
