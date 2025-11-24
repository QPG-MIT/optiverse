"""
Component type definitions.

Provides type-safe enums for component types, replacing magic strings.
"""
from __future__ import annotations

from enum import Enum


class ComponentType(str, Enum):
    """
    Types of optical components that can be placed on the canvas.
    
    Inherits from str to allow string comparison for backward compatibility.
    """
    SOURCE = "source"
    LENS = "lens"
    MIRROR = "mirror"
    BEAMSPLITTER = "beamsplitter"
    WAVEPLATE = "waveplate"
    DICHROIC = "dichroic"
    TEXT = "text"
    RECTANGLE = "rectangle"
    RULER = "ruler"
    BLOCK = "block"
    SLM = "slm"
    
    @classmethod
    def is_optical(cls, component_type: "ComponentType | str") -> bool:
        """Check if a component type is an optical element (not annotation)."""
        optical_types = {
            cls.SOURCE, cls.LENS, cls.MIRROR, cls.BEAMSPLITTER,
            cls.WAVEPLATE, cls.DICHROIC, cls.BLOCK, cls.SLM
        }
        if isinstance(component_type, str):
            try:
                component_type = cls(component_type)
            except ValueError:
                return False
        return component_type in optical_types
    
    @classmethod
    def is_annotation(cls, component_type: "ComponentType | str") -> bool:
        """Check if a component type is an annotation (not optical)."""
        annotation_types = {cls.TEXT, cls.RECTANGLE, cls.RULER}
        if isinstance(component_type, str):
            try:
                component_type = cls(component_type)
            except ValueError:
                return False
        return component_type in annotation_types

