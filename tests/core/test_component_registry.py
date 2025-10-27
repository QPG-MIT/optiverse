"""
Tests for ComponentRegistry system.

Verifies that standard components are correctly defined with proper
images and parameters.
"""
import os
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
            pytest.fail("ComponentRegistry should be importable from optiverse.objects.component_registry")

    def test_get_standard_components_returns_list(self):
        """get_standard_components() should return a list."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        assert isinstance(components, list)
        assert len(components) > 0

    def test_standard_components_have_required_fields(self):
        """All standard components should have required fields."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        
        for comp in components:
            assert "name" in comp, "Component must have 'name' field"
            assert "kind" in comp, "Component must have 'kind' field"
            assert comp["kind"] in ["lens", "mirror", "beamsplitter", "source"], \
                f"Invalid kind: {comp['kind']}"

    def test_standard_lens_definition(self):
        """Standard lens should use lens_1_inch_mounted.png."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        lenses = [c for c in components if c["kind"] == "lens"]
        
        assert len(lenses) >= 1, "Should have at least one standard lens"
        
        std_lens = lenses[0]
        assert "Standard Lens" in std_lens["name"]
        assert "image_path" in std_lens
        assert "lens_1_inch_mounted.png" in std_lens["image_path"]
        assert std_lens["efl_mm"] == 100.0
        assert "length_mm" in std_lens
        assert "mm_per_pixel" in std_lens
        assert "line_px" in std_lens

    def test_standard_mirror_definition(self):
        """Standard mirror should use standard_mirror_1_inch.png."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        mirrors = [c for c in components if c["kind"] == "mirror"]
        
        assert len(mirrors) >= 1, "Should have at least one standard mirror"
        
        std_mirror = mirrors[0]
        assert "Standard Mirror" in std_mirror["name"]
        assert "image_path" in std_mirror
        assert "standard_mirror_1_inch.png" in std_mirror["image_path"]
        assert "length_mm" in std_mirror
        assert "mm_per_pixel" in std_mirror
        assert "line_px" in std_mirror

    def test_standard_beamsplitter_definition(self):
        """Standard beamsplitter should use beamsplitter_50_50_1_inch.png."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        beamsplitters = [c for c in components if c["kind"] == "beamsplitter"]
        
        assert len(beamsplitters) >= 1, "Should have at least one standard beamsplitter"
        
        std_bs = beamsplitters[0]
        assert "Standard Beamsplitter" in std_bs["name"] or "50/50" in std_bs["name"]
        assert "image_path" in std_bs
        assert "beamsplitter_50_50_1_inch.png" in std_bs["image_path"]
        assert std_bs.get("split_T") == 50.0 or std_bs.get("split_TR") == [50.0, 50.0]
        assert "length_mm" in std_bs
        assert "mm_per_pixel" in std_bs
        assert "line_px" in std_bs

    def test_standard_source_definition(self):
        """Standard source should be defined."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        sources = [c for c in components if c["kind"] == "source"]
        
        assert len(sources) >= 1, "Should have at least one standard source"
        
        std_source = sources[0]
        assert "Standard Source" in std_source["name"]
        assert "n_rays" in std_source
        assert "spread_deg" in std_source
        assert "size_mm" in std_source
        assert "ray_length_mm" in std_source

    def test_image_paths_exist(self):
        """All referenced image paths should exist."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        
        for comp in components:
            if "image_path" in comp and comp["image_path"]:
                path = Path(comp["image_path"])
                assert path.exists(), f"Image not found: {comp['image_path']}"

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
        
        # Should not raise an exception
        json_str = json.dumps(components)
        assert len(json_str) > 0

    def test_line_px_is_tuple_of_four(self):
        """line_px should be a 4-element tuple (x1, y1, x2, y2)."""
        from optiverse.objects.component_registry import ComponentRegistry
        
        components = ComponentRegistry.get_standard_components()
        
        for comp in components:
            if "line_px" in comp:
                line_px = comp["line_px"]
                assert isinstance(line_px, (list, tuple)), "line_px should be list or tuple"
                assert len(line_px) == 4, "line_px should have 4 elements"
                assert all(isinstance(x, (int, float)) for x in line_px), \
                    "All line_px elements should be numeric"

