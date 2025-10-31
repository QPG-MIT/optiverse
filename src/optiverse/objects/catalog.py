from __future__ import annotations

from typing import List, Dict, Any

from .definitions_loader import load_component_dicts
from .component_registry import ComponentRegistry


def list() -> List[Dict[str, Any]]:
    """Return all standard components as JSON-serializable dicts."""
    return load_component_dicts()


def grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Return components grouped into UI categories using a single helper."""
    categories: Dict[str, List[Dict[str, Any]]] = {
        "Lenses": [],
        "Objectives": [],
        "Mirrors": [],
        "Beamsplitters": [],
        "Dichroics": [],
        "Waveplates": [],
        "Sources": [],
        "Background": [],
        "Misc": [],
        "Other": [],
    }
    for rec in list():
        name = rec.get("name", "")
        interfaces = rec.get("interfaces", [])
        if interfaces and len(interfaces) > 0:
            element_type = interfaces[0].get("element_type", "lens")
            category = ComponentRegistry.get_category_for_element_type(element_type, name)
        else:
            category = "Other"
        categories.setdefault(category, []).append(rec)
    return categories


