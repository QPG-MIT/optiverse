"""
Pure data models for optical components.

This module contains data structures with no UI or framework dependencies.
All models are serializable and can be used independently of PyQt.
"""

from .geometry import LineSegment, CurvedSegment, GeometrySegment
from .optical_properties import (
    RefractiveProperties,
    LensProperties,
    MirrorProperties,
    BeamsplitterProperties,
    WaveplateProperties,
    DichroicProperties,
    OpticalProperties,
)
from .optical_interface import OpticalInterface

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
    "OpticalProperties",
    "OpticalInterface",
]



