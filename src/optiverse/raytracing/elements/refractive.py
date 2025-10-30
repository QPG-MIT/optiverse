"""
Refractive interface element implementation.

Implements Snell's law and Fresnel equations for refraction and partial reflection.
"""
from typing import List, Tuple
import numpy as np
import math

from .base import IOpticalElement
from ..ray import RayState
from ...core.geometry import (
    normalize, reflect_vec,
    refract_vector_snell, fresnel_coefficients,
    transform_polarization_mirror
)


class RefractiveElement(IOpticalElement):
    """
    Refractive interface between two media.
    
    Implements:
    - Snell's law for refraction
    - Fresnel equations for partial reflection
    - Total internal reflection
    """
    
    def __init__(self, p1: np.ndarray, p2: np.ndarray, n1: float, n2: float):
        """
        Initialize refractive interface.
        
        Args:
            p1: Start point of interface line segment [x, y] in mm
            p2: End point of interface line segment [x, y] in mm
            n1: Refractive index on "left" side (incident medium)
            n2: Refractive index on "right" side (transmitted medium)
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.n1 = n1
        self.n2 = n2
    
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get interface line segment"""
        return self.p1, self.p2
    
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Apply Snell's law and Fresnel equations.
        
        Physics:
        - Snell's law: n1*sin(θ1) = n2*sin(θ2)
        - Fresnel equations determine R (reflection) and T (transmission) coefficients
        - Total internal reflection when θ1 > critical angle
        """
        # Determine which direction ray is traveling (which side of interface)
        dot_v_n = float(np.dot(ray.direction, normal))
        
        if dot_v_n < 0:
            # Ray traveling in direction of normal (n1 → n2)
            n_incident = self.n1
            n_transmitted = self.n2
            surface_normal = normal
        else:
            # Ray traveling against normal (n2 → n1)
            n_incident = self.n2
            n_transmitted = self.n1
            surface_normal = -normal
        
        # Apply Snell's law
        direction_refracted, is_total_reflection = refract_vector_snell(
            ray.direction,
            surface_normal,
            n_incident,
            n_transmitted
        )
        
        output_rays = []
        EPS_ADV = 1e-3
        MIN_INTENSITY = 0.02  # Threshold for ray continuation
        
        if is_total_reflection:
            # Total internal reflection - all light reflects
            direction_reflected = normalize(direction_refracted)
            polarization_reflected = transform_polarization_mirror(
                ray.polarization,
                ray.direction,
                surface_normal
            )
            
            reflected_ray = RayState(
                position=hit_point + direction_reflected * EPS_ADV,
                direction=direction_reflected,
                intensity=ray.intensity,  # All light reflected
                polarization=polarization_reflected,
                wavelength_nm=ray.wavelength_nm,
                path=ray.path + [hit_point],
                events=ray.events + 1
            )
            output_rays.append(reflected_ray)
        else:
            # Partial reflection and transmission
            # Compute Fresnel coefficients
            theta_incident = abs(math.acos(
                max(-1.0, min(1.0, -np.dot(ray.direction, surface_normal)))
            ))
            R, T = fresnel_coefficients(theta_incident, n_incident, n_transmitted)
            
            # Transmitted (refracted) ray
            if T > MIN_INTENSITY / ray.intensity:
                direction_transmitted = normalize(direction_refracted)
                
                transmitted_ray = RayState(
                    position=hit_point + direction_transmitted * EPS_ADV,
                    direction=direction_transmitted,
                    intensity=ray.intensity * T,
                    polarization=ray.polarization,  # Simplified: polarization preserved
                    wavelength_nm=ray.wavelength_nm,
                    path=ray.path + [hit_point],
                    events=ray.events + 1
                )
                output_rays.append(transmitted_ray)
            
            # Reflected ray (Fresnel reflection)
            if R > MIN_INTENSITY / ray.intensity:
                direction_reflected = normalize(reflect_vec(ray.direction, surface_normal))
                polarization_reflected = transform_polarization_mirror(
                    ray.polarization,
                    ray.direction,
                    surface_normal
                )
                
                reflected_ray = RayState(
                    position=hit_point + direction_reflected * EPS_ADV,
                    direction=direction_reflected,
                    intensity=ray.intensity * R,
                    polarization=polarization_reflected,
                    wavelength_nm=ray.wavelength_nm,
                    path=ray.path + [hit_point],
                    events=ray.events + 1
                )
                output_rays.append(reflected_ray)
        
        return output_rays
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner

