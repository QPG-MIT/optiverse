"""
Component Registry - Delegates to definitions loader and provides categorization.

This module provides a thin wrapper over the definitions loader and categorization logic.
Standard components are defined in objects/library/*/component.json files.
"""

from typing import Any

from .definitions_loader import load_component_dicts


class ComponentRegistry:
    """
    Registry for standard optical components loaded from JSON definitions.

    Delegates to definitions_loader for component data and provides categorization helpers.
    """

    @staticmethod
    def get_standard_components() -> list[dict[str, Any]]:
        """
        Load all standard components from per-object folders.
        Returns a list of JSON-serializable component dicts.
        """
        return load_component_dicts()

    @staticmethod
    def get_components_by_category() -> dict[str, list[dict[str, Any]]]:
        """
        Get standard components organized by category using the same
        categorization logic as the UI.
        """
        categories: dict[str, list[dict[str, Any]]] = {
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

        for rec in ComponentRegistry.get_standard_components():
            name = rec.get("name", "")

            # Check for top-level category field first (preferred method)
            if "category" in rec:
                category_key = rec["category"].lower()
                # Map to UI category names
                category_map = {
                    "lenses": "Lenses",
                    "objectives": "Objectives",
                    "mirrors": "Mirrors",
                    "beamsplitters": "Beamsplitters",
                    "dichroics": "Dichroics",
                    "waveplates": "Waveplates",
                    "sources": "Sources",
                    "background": "Background",
                    "misc": "Misc",
                }
                category = category_map.get(category_key, "Other")
            else:
                # Fallback to element_type for legacy support
                interfaces = rec.get("interfaces", [])
                if interfaces and len(interfaces) > 0:
                    element_type = interfaces[0].get("element_type", "lens")
                    category = ComponentRegistry.get_category_for_element_type(element_type, name)
                else:
                    category = "Other"

            categories.setdefault(category, []).append(rec)

        return categories

    @staticmethod
    def get_category_for_element_type(element_type: str, name: str = "") -> str:
        """
        Get the category name for a component based on its interface element_type.

        Args:
            element_type: Element type from interface ('lens', 'mirror', 'beam_splitter', 'dichroic', 'waveplate', etc.)
            name: Optional component name to distinguish special cases (e.g., objectives)

        Returns:
            Category name (e.g., 'Lenses', 'Mirrors', 'Dichroics', 'Background', 'Misc')
        """
        # Special case: Objectives are lenses but in their own category
        if element_type == "lens" and "objective" in name.lower():
            return "Objectives"

        element_type_to_category = {
            "lens": "Lenses",
            "mirror": "Mirrors",
            "beam_splitter": "Beamsplitters",
            "beamsplitter": "Beamsplitters",  # Legacy support
            "dichroic": "Dichroics",
            "waveplate": "Waveplates",
            "source": "Sources",
            "background": "Background",
            "slm": "Misc",
            "refractive_interface": "Other",  # Generic refractive interfaces
            "beam_block": "Misc",
        }
        return element_type_to_category.get(element_type, "Other")
