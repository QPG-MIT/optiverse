"""
Pure data models for optical components.

This module contains data structures with no UI or framework dependencies.
All models are serializable and can be used independently of PyQt.
"""

from .geometry import CurvedSegment, GeometrySegment, LineSegment
from .optical_interface import OpticalInterface
from .optical_properties import (
    BeamBlockProperties,
    BeamsplitterProperties,
    DichroicProperties,
    LensProperties,
    MirrorProperties,
    OpticalProperties,
    RefractiveProperties,
    WaveplateProperties,
)

__all__ = [
    "LineSegment",
    "CurvedSegment",
    "GeometrySegment",
    "RefractiveProperties",
    "LensProperties",
    "MirrorProperties",
    "BeamsplitterProperties",
    "WaveplateProperties",
    "DichroicProperties",
    "BeamBlockProperties",
    "OpticalProperties",
    "OpticalInterface",
]
