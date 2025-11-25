"""
Core utility functions for Optiverse.

This module provides common utility functions used across the codebase.
"""
from __future__ import annotations

import re


def slugify(name: str, separator: str = "_") -> str:
    """
    Convert a name to a filesystem-safe slug.

    Args:
        name: The name to convert
        separator: The separator to use (default: "_")

    Returns:
        A lowercase, filesystem-safe version of the name

    Examples:
        >>> slugify("My Component")
        'my_component'
        >>> slugify("AC254-100-B", separator="-")
        'ac254-100-b'
    """
    s = name.strip().lower()
    # Replace any non-alphanumeric characters with the separator
    s = re.sub(r"[^a-z0-9]+", separator, s).strip(separator)
    return s or "component"



