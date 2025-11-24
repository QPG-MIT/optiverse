"""
Simplified raytracing engine using polymorphic elements.

This replaces the complex 358-line _trace_single_ray_worker function
with a clean, extensible 50-line implementation.
"""
from typing import List, Tuple
import numpy as np
import math

from .ray import Ray, RayPath, Polarization
from .elements.base import IOpticalElement, RayIntersection
from ..core.raytracing_math import ray_hit_element, deg2rad
from ..core.color_utils import qcolor_from_hex, wavelength_to_rgb
from ..core.models import SourceParams


def trace_rays_polymorphic(
    elements: List[IOpticalElement],
    sources: List[SourceParams],
    max_events: int = 80,
    epsilon: float = 1e-3,
    min_intensity: float = 0.02
) -> List[RayPath]:
    """
    Trace rays from sources through optical elements using polymorphism.
    
    This is the new, simplified raytracing engine that uses polymorphism
    instead of string-based type checking.
    
    Args:
        elements: List of optical elements implementing IOpticalElement
        sources: List of light sources (SourceParams objects)
        max_events: Maximum interactions per ray
        epsilon: Small distance to advance ray after interaction (prevents re-intersection)
        min_intensity: Minimum intensity threshold to continue tracing
        
    Returns:
        List of ray paths for visualization
        
    Complexity:
        - Before: O(6n) per ray (6 separate loops for pre-filtering)
        - After: O(n) per ray (single loop with polymorphism)
        - With BVH (Phase 4): O(log n) per ray
    """
    paths = []
    
    # Generate and trace rays from each source
    for source in sources:
        # Generate initial rays from this source
        initial_rays = _generate_rays_from_source(source)
        
        # Trace each ray
        for ray in initial_rays:
            ray_paths = _trace_single_ray(ray, elements, max_events, epsilon, min_intensity, source)
            paths.extend(ray_paths)
    
    return paths


def _generate_rays_from_source(source: SourceParams) -> List[Ray]:
    """
    Generate initial rays from a source configuration.
    
    Args:
        source: SourceParams object
        
    Returns:
        List of Ray objects
    """
    base = -deg2rad(source.angle_deg)  # Convert user (CW) to math (CCW) convention
    spread = deg2rad(source.spread_deg)
    
    # Generate ray positions
    if source.n_rays <= 1 or source.size_mm == 0:
        y_offsets = [0.0]
    else:
        y_offsets = list(np.linspace(-source.size_mm/2, source.size_mm/2, source.n_rays))
    
    # Generate ray angles
    if spread == 0 or source.n_rays <= 1:
        angles = [base] * len(y_offsets)
    else:
        fan = np.linspace(-spread, +spread, len(y_offsets))
        angles = [base + a for a in fan]
    
    # Get initial polarization
    initial_polarization = source.get_polarization()
    
    # Get color from source
    src_col = qcolor_from_hex(source.color_hex)
    base_rgb = (src_col.red(), src_col.green(), src_col.blue())
    
    # Create rays
    rays = []
    for i, y_offset in enumerate(y_offsets):
        angle = angles[i]
        direction = np.array([math.cos(angle), math.sin(angle)], dtype=float)
        # Apply offset perpendicular to ray direction (90° CCW from direction)
        perpendicular = np.array([-math.sin(angle), math.cos(angle)], dtype=float)
        position = np.array([source.x_mm, source.y_mm], dtype=float) + y_offset * perpendicular
        
        ray = Ray(
            position=position,
            direction=direction,
            remaining_length=source.ray_length_mm,
            polarization=initial_polarization,
            wavelength_nm=source.wavelength_nm,
            base_rgb=base_rgb,
            intensity=1.0,
            events=0,
            path_points=[position.copy()]  # Initialize with starting position
        )
        rays.append(ray)
    
    return rays


def _trace_single_ray(
    ray: Ray,
    elements: List[IOpticalElement],
    max_events: int,
    epsilon: float,
    min_intensity: float,
    source: SourceParams
) -> List[RayPath]:
    """
    Trace a single ray through elements.
    
    This is the core of the new architecture - clean and simple!
    No string-based dispatch, no pre-filtering, just pure polymorphism.
    
    Args:
        ray: Initial ray state
        elements: List of optical elements
        max_events: Maximum interactions
        epsilon: Small distance to advance after interaction
        min_intensity: Minimum intensity to continue
        source: Source parameters (for color/wavelength info)
        
    Returns:
        List of RayPath objects (can be multiple due to beamsplitters)
    """
    paths = []
    base_rgb = ray.base_rgb
    
    # Stack for ray processing (enables beam splitting)
    # Each stack item is a Ray object
    stack = [ray]
    last_element_for_ray = {}  # Track last interacted element to prevent re-intersection
    
    while stack:
        current_ray = stack.pop()
        
        # Check termination conditions
        if current_ray.events >= max_events or current_ray.intensity < min_intensity or current_ray.remaining_length <= 0:
            # Finalize this path
            if len(current_ray.path_points) >= 2:
                alpha = int(255 * max(0.0, min(1.0, current_ray.intensity)))
                paths.append(RayPath(
                    points=current_ray.path_points,
                    rgba=(base_rgb[0], base_rgb[1], base_rgb[2], alpha),
                    polarization=current_ray.polarization,
                    wavelength_nm=current_ray.wavelength_nm
                ))
            continue
        
        # Find nearest intersection
        # TODO Phase 4: Replace with BVH spatial index for O(log n)
        nearest_element = None
        nearest_distance = float('inf')
        nearest_intersection = None
        last_elem = last_element_for_ray.get(id(current_ray), None)
        
        for element in elements:
            # Skip the last element this ray interacted with
            if element is last_elem:
                continue
                
            # Get geometry (may be LineSegment or CurvedSegment)
            geometry = getattr(element, '_geometry', None)
            
            if geometry is not None:
                # NEW: Support for curved surfaces!
                is_curved = getattr(geometry, 'is_curved', False)
                
                if is_curved:
                    # Use curved intersection for curved surfaces
                    from ...core.raytracing_math import ray_hit_curved_element
                    result = ray_hit_curved_element(
                        current_ray.position,
                        current_ray.direction,
                        geometry.get_center(),
                        geometry.get_radius(),
                        geometry.p1,
                        geometry.p2
                    )
                else:
                    # Use flat intersection for flat surfaces
                    result = ray_hit_element(current_ray.position, current_ray.direction, geometry.p1, geometry.p2)
            else:
                # Fallback for elements without _geometry attribute (legacy)
                p1, p2 = element.get_geometry()
                result = ray_hit_element(current_ray.position, current_ray.direction, p1, p2)
            
            if result is not None:
                t, hit_point, tangent, normal, center, length = result
                distance = t
                
                # Check if within remaining ray length
                if distance * np.linalg.norm(current_ray.direction) > current_ray.remaining_length:
                    continue
                
                if distance < nearest_distance and distance > epsilon:  # epsilon prevents immediate re-intersection
                    nearest_distance = distance
                    nearest_element = element
                    # Get the optical interface from the element
                    # Assuming elements have an 'interface' attribute from Phase 2
                    nearest_intersection = RayIntersection(
                        distance=distance,
                        point=hit_point,
                        tangent=tangent,
                        normal=normal,
                        center=center,
                        length=length,
                        interface=getattr(element, 'interface', None)
                    )
        
        # No intersection - ray escapes
        if nearest_element is None:
            # Extend ray to remaining length
            final_point = current_ray.position + current_ray.direction * current_ray.remaining_length
            current_ray.path_points.append(final_point)
            
            alpha = int(255 * max(0.0, min(1.0, current_ray.intensity)))
            paths.append(RayPath(
                points=current_ray.path_points,
                rgba=(base_rgb[0], base_rgb[1], base_rgb[2], alpha),
                polarization=current_ray.polarization,
                wavelength_nm=current_ray.wavelength_nm
            ))
            continue
        
        # Add intersection point to path before interaction
        current_ray.path_points.append(nearest_intersection.point)
        
        # Interact with element - POLYMORPHIC DISPATCH!
        # This is the magic: no type checking, no if-elif chains
        # Just call element.interact() and it does the right thing!
        output_rays = nearest_element.interact(
            current_ray,
            nearest_intersection.point,
            nearest_intersection.normal,
            nearest_intersection.tangent
        )
        
        # Track last element and propagate engine-specific fields to output rays
        for out_ray in output_rays:
            last_element_for_ray[id(out_ray)] = nearest_element
            
            # Propagate engine-specific fields that interact() doesn't know about
            if not hasattr(out_ray, 'base_rgb') or out_ray.base_rgb is None:
                out_ray.base_rgb = base_rgb
            if not hasattr(out_ray, 'remaining_length'):
                out_ray.remaining_length = current_ray.remaining_length - nearest_distance
            if not hasattr(out_ray, 'path_points') or len(out_ray.path_points) == 0:
                # Copy path points from current ray (which includes the interaction point)
                out_ray.path_points = current_ray.path_points.copy()
        
        # Add output rays to stack for processing
        stack.extend(output_rays)
    
    return paths


# Convenience alias for the main function
trace_rays = trace_rays_polymorphic

