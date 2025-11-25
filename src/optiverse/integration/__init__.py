"""
Integration layer for connecting legacy interfaces to the new polymorphic raytracing system.

This module provides adapters and utilities for:
1. Converting legacy InterfaceDefinition/RefractiveInterface to OpticalInterface (Phase 1)
2. Converting OpticalInterface to IOpticalElement (Phase 2)
3. Providing a unified API for the MainWindow to use either system
"""

from .adapter import (
    convert_legacy_interfaces,
    convert_scene_to_polymorphic,
    create_polymorphic_element,
)

__all__ = [
    "create_polymorphic_element",
    "convert_legacy_interfaces",
    "convert_scene_to_polymorphic",
]
