"""
Tests for ComponentRegistry/catalog system (v2 schema).

Verifies that standard components load from per-object folders with
interfaces and valid image paths.
"""

from pathlib import Path

import pytest


class TestComponentRegistry:
    """Test the component registry returns correct standard components."""

    def test_registry_exists(self):
        """Component registry module should exist."""
        try:
            from optiverse.objects.component_registry import ComponentRegistry

            assert ComponentRegistry is not None
        except ImportError:
            pytest.fail(
                "ComponentRegistry should be importable from optiverse.objects.component_registry"
            )

    def test_get_standard_components_returns_list(self):
        """get_standard_components() should return a non-empty list."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        assert isinstance(components, list) and len(components) > 0

    def test_standard_components_have_required_fields(self):
        """All standard components should have required v2 fields."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()

        for comp in components:
            assert "name" in comp, "Component must have 'name'"
            assert "image_path" in comp, "Component must have 'image_path'"
            assert "object_height_mm" in comp, "Component must have 'object_height_mm'"
            # Either interfaces are present or it's a non-interface element (e.g., source/background)
            assert "interfaces" in comp, "Component should export 'interfaces' list"
            # No legacy keys
            assert "schema_version" not in comp
            assert "coord_system" not in comp

    def test_standard_lens_definition(self):
        """Standard lens should appear with correct image and interfaces."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        # A lens is any component whose first interface is type 'lens'
        lenses = [
            c
            for c in components
            if c.get("interfaces") and c["interfaces"][0].get("element_type") == "lens"
        ]

        assert len(lenses) >= 1, "Should have at least one standard lens"

        std_lens = lenses[0]
        assert "Standard Lens" in std_lens["name"]
        assert "lens_1_inch_mounted.png" in std_lens["image_path"]
        iface0 = std_lens["interfaces"][0]
        assert iface0.get("efl_mm") == 100.0

    def test_standard_mirror_definition(self):
        """Standard mirror should use standard_mirror_1_inch.png."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        mirrors = [
            c
            for c in components
            if c.get("interfaces") and c["interfaces"][0].get("element_type") == "mirror"
        ]

        assert len(mirrors) >= 1, "Should have at least one standard mirror"

        std_mirror = mirrors[0]
        assert "Standard Mirror" in std_mirror["name"]
        assert "standard_mirror_1_inch.png" in std_mirror["image_path"]

    def test_standard_beamsplitter_definition(self):
        """Standard beamsplitter should use beamsplitter_50_50_1_inch.png."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        beamsplitters = [
            c
            for c in components
            if c.get("interfaces")
            and c["interfaces"][0].get("element_type") in ("beam_splitter", "beamsplitter")
        ]

        assert len(beamsplitters) >= 1, "Should have at least one standard beamsplitter"

        std_bs = beamsplitters[0]
        assert "Standard Beamsplitter" in std_bs["name"] or "50/50" in std_bs["name"]
        assert "beamsplitter_50_50_1_inch.png" in std_bs["image_path"]
        iface0 = std_bs["interfaces"][0]
        assert iface0.get("split_T") == 50.0
        assert iface0.get("split_R") == 50.0

    def test_standard_source_definition(self):
        """Standard source should be defined."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        sources = [c for c in components if c.get("name", "").lower().startswith("standard source")]

        assert len(sources) >= 1, "Should have at least one standard source"

        std_source = sources[0]
        for k in ("n_rays", "spread_deg", "size_mm", "ray_length_mm"):
            assert k in std_source

    def test_image_paths_exist(self):
        """All referenced image paths should exist on disk."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()

        for comp in components:
            image = comp.get("image_path", "")
            if image:
                path = Path(image)
                assert path.exists(), f"Image not found: {image}"

    def test_get_components_by_category(self):
        """get_components_by_category() should organize components."""
        from optiverse.objects.component_registry import ComponentRegistry

        by_category = ComponentRegistry.get_components_by_category()

        assert isinstance(by_category, dict)
        assert "Lenses" in by_category
        assert "Mirrors" in by_category
        assert "Beamsplitters" in by_category
        assert "Sources" in by_category

        # Each category should have at least one component
        assert len(by_category["Lenses"]) >= 1
        assert len(by_category["Mirrors"]) >= 1
        assert len(by_category["Beamsplitters"]) >= 1
        assert len(by_category["Sources"]) >= 1

    def test_component_params_are_serializable(self):
        """All component parameters should be JSON-serializable."""
        import json

        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()

        json_str = json.dumps(components)
        assert len(json_str) > 0

    def test_interfaces_have_valid_minimal_fields(self):
        """If interfaces exist, they contain numeric coordinates and element_type."""
        from optiverse.objects.component_registry import ComponentRegistry

        components = ComponentRegistry.get_standard_components()
        for comp in components:
            if comp.get("interfaces"):
                iface = comp["interfaces"][0]
                assert isinstance(iface.get("x1_mm"), (int, float))
                assert isinstance(iface.get("y1_mm"), (int, float))
                assert isinstance(iface.get("x2_mm"), (int, float))
                assert isinstance(iface.get("y2_mm"), (int, float))
                assert isinstance(iface.get("element_type"), str)
