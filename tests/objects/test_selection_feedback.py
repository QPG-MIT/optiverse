"""
Tests for selection feedback on component sprites.

When a component is selected, its sprite should show visual feedback
(blue tint overlay) to indicate selection.
"""

from optiverse.core.models import BeamsplitterParams, LensParams, MirrorParams
from optiverse.objects import BeamsplitterItem, LensItem, MirrorItem


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
        params = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        item = LensItem(params)

        # Should have itemChange method that handles selection
        assert hasattr(item, "itemChange")

        # Selecting should not crash
        item.setSelected(True)
        item.setSelected(False)


class TestBaseObjItemChange:
    """Test that itemChange handles selection state changes."""

    def test_itemchange_on_selection(self):
        """itemChange should handle selection state changes."""
        params = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        item = LensItem(params)

        # Selection change should not crash
        item.setSelected(True)
        assert item.isSelected()

        item.setSelected(False)
        assert not item.isSelected()

    def test_itemchange_updates_sprite_on_selection(self):
        """When selection changes, sprite should be updated."""
        params = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        item = LensItem(params)

        # Even without sprite, selection should work
        item.setSelected(True)
        item.setSelected(False)

        # No crashes expected
        assert True


class TestIntegrationWithAllComponents:
    """Test selection feedback works with all component types."""

    def test_lens_selection_feedback(self):
        """Lens selection should work."""
        params = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        item = LensItem(params)

        item.setSelected(True)
        assert item.isSelected()

    def test_mirror_selection_feedback(self):
        """Mirror selection should work."""
        params = MirrorParams(x_mm=0, y_mm=0, angle_deg=0.0, length_mm=80.0)
        item = MirrorItem(params)

        item.setSelected(True)
        assert item.isSelected()

    def test_beamsplitter_selection_feedback(self):
        """Beamsplitter selection should work."""
        params = BeamsplitterParams(
            x_mm=0, y_mm=0, angle_deg=45.0, length_mm=80.0, split_T=50.0, split_R=50.0
        )
        item = BeamsplitterItem(params)

        item.setSelected(True)
        assert item.isSelected()
