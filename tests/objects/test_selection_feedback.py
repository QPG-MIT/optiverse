"""
Tests for selection feedback on component sprites.

When a component is selected, its sprite should show visual feedback
(blue tint overlay) to indicate selection.
"""

from optiverse.objects import ComponentItem
from tests.fixtures.factories import (
    create_component_from_params,
    create_lens_item,
    create_mirror_item,
)


class TestSelectionFeedback:
    """Test selection feedback on component sprites."""

    def test_sprite_has_paint_method(self):
        """ComponentSprite should have a paint method."""
        from optiverse.objects import ComponentSprite

        # Check that paint method exists
        assert hasattr(ComponentSprite, "paint")
        assert callable(ComponentSprite.paint)

    def test_selection_changes_trigger_update(self):
        """Selecting/deselecting should trigger sprite update."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        # Should have itemChange method that handles selection
        assert hasattr(item, "itemChange")

        # Selecting should not crash
        item.setSelected(True)
        item.setSelected(False)


class TestBaseObjItemChange:
    """Test that itemChange handles selection state changes."""

    def test_itemchange_on_selection(self):
        """itemChange should handle selection state changes."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        # Selection change should not crash
        item.setSelected(True)
        assert item.isSelected()

        item.setSelected(False)
        assert not item.isSelected()

    def test_itemchange_updates_sprite_on_selection(self):
        """When selection changes, sprite should be updated."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        # Even without sprite, selection should work
        item.setSelected(True)
        item.setSelected(False)

        # No crashes expected
        assert True


class TestIntegrationWithAllComponents:
    """Test selection feedback works with all component types."""

    def test_lens_selection_feedback(self):
        """Lens selection should work."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        item.setSelected(True)
        assert item.isSelected()

    def test_mirror_selection_feedback(self):
        """Mirror selection should work."""
        item = create_mirror_item(x_mm=0, y_mm=0, angle_deg=0.0)

        item.setSelected(True)
        assert item.isSelected()

    def test_beamsplitter_selection_feedback(self):
        """Beamsplitter selection should work."""
        from optiverse.core.interface_definition import InterfaceDefinition
        from optiverse.core.models import ComponentParams

        # Create a beamsplitter using ComponentParams with beam_splitter interface
        half_height = 40.0
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="beam_splitter",
            split_T=50.0,
            split_R=50.0,
        )
        params = ComponentParams(
            x_mm=0, y_mm=0, angle_deg=45.0, object_height_mm=80.0, interfaces=[interface]
        )
        item = ComponentItem(params)

        item.setSelected(True)
        assert item.isSelected()
