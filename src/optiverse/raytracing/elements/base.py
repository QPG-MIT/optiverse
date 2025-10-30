"""
Base interface for all optical elements.

Defines the contract that all optical elements must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np

# Import RayState from parent package
from ..ray import RayState


class IOpticalElement(ABC):
    """
    Interface for all optical elements.
    
    This is the key to the polymorphic architecture. Each element type
    implements this interface, allowing the raytracing engine to work
    with any element without type checking.
    
    Design:
    - get_geometry() returns the line segment representing the element
    - interact() processes ray-element interaction
    - get_bounding_box() for spatial indexing (Phase 4)
    """
    
    @abstractmethod
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get element geometry as line segment.
        
        Returns:
            Tuple of (p1, p2) where p1 and p2 are endpoints in mm
        """
        pass
    
    @abstractmethod
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Process ray interaction with this element.
        
        This is the core method that implements optical physics.
        Each element type has its own physics.
        
        Args:
            ray: Incoming ray state
            hit_point: Intersection point in mm
            normal: Surface normal at hit point (normalized)
            tangent: Surface tangent at hit point (normalized)
            
        Returns:
            List of output rays (e.g., [transmitted, reflected])
            Empty list means ray was absorbed
        """
        pass
    
    @abstractmethod
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get axis-aligned bounding box for spatial indexing.
        
        Returns:
            Tuple of (min_corner, max_corner) where each is [x, y] in mm
        """
        pass

