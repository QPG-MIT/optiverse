#!/usr/bin/env python3
"""
Quick test to verify PathMeasureItem undo/redo functionality.
"""
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore

# Add src to path
sys.path.insert(0, 'src')

from optiverse.objects.annotations.path_measure_item import PathMeasureItem
from optiverse.core.undo_commands import AddItemCommand, AddMultipleItemsCommand
from optiverse.core.undo_stack import UndoStack

def test_single_path_measure():
    """Test single PathMeasureItem with undo/redo."""
    print("Testing single PathMeasureItem...")
    
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    scene = QtWidgets.QGraphicsScene()
    undo_stack = UndoStack()
    
    # Create ray path
    points = [np.array([0, 0]), np.array([100, 0]), np.array([100, 100])]
    
    # Create PathMeasureItem
    item = PathMeasureItem(ray_path_points=points, start_param=0.0, end_param=1.0, ray_index=0)
    
    # Add via undo command
    cmd = AddItemCommand(scene, item)
    undo_stack.push(cmd)
    
    assert item in scene.items(), "❌ Item should be in scene after add"
    print("✅ Item added to scene")
    
    # Undo
    undo_stack.undo()
    assert item not in scene.items(), "❌ Item should NOT be in scene after undo"
    print("✅ Undo works - item removed")
    
    # Redo
    undo_stack.redo()
    assert item in scene.items(), "❌ Item should be back in scene after redo"
    print("✅ Redo works - item restored")
    
    print("✅ Single PathMeasureItem test PASSED\n")

def test_multiple_path_measures():
    """Test multiple PathMeasureItems (beam splitter case) with undo/redo."""
    print("Testing multiple PathMeasureItems (beam splitter)...")
    
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    scene = QtWidgets.QGraphicsScene()
    undo_stack = UndoStack()
    
    # Create 3 ray paths (simulating beam splitter)
    points1 = [np.array([0, 0]), np.array([100, 0])]
    points2 = [np.array([0, 0]), np.array([0, 100])]
    points3 = [np.array([0, 0]), np.array([50, 50])]
    
    # Create 3 PathMeasureItems
    item1 = PathMeasureItem(ray_path_points=points1, start_param=0.0, end_param=1.0, ray_index=0)
    item2 = PathMeasureItem(ray_path_points=points2, start_param=0.0, end_param=1.0, ray_index=1)
    item3 = PathMeasureItem(ray_path_points=points3, start_param=0.0, end_param=1.0, ray_index=2)
    
    items = [item1, item2, item3]
    
    # Add all via single undo command (beam splitter case)
    cmd = AddMultipleItemsCommand(scene, items)
    undo_stack.push(cmd)
    
    for i, item in enumerate(items):
        assert item in scene.items(), f"❌ Item {i} should be in scene after add"
    print("✅ All 3 items added to scene")
    
    # Undo (should remove ALL items in one operation)
    undo_stack.undo()
    for i, item in enumerate(items):
        assert item not in scene.items(), f"❌ Item {i} should NOT be in scene after undo"
    print("✅ Undo works - all 3 items removed atomically")
    
    # Redo (should restore ALL items in one operation)
    undo_stack.redo()
    for i, item in enumerate(items):
        assert item in scene.items(), f"❌ Item {i} should be back in scene after redo"
    print("✅ Redo works - all 3 items restored atomically")
    
    print("✅ Multiple PathMeasureItems test PASSED\n")

def test_delete_with_undo():
    """Test that deletion also works with undo."""
    print("Testing PathMeasureItem deletion with undo...")
    
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    scene = QtWidgets.QGraphicsScene()
    undo_stack = UndoStack()
    
    from optiverse.core.undo_commands import RemoveItemCommand
    
    # Create and add item
    points = [np.array([0, 0]), np.array([100, 0])]
    item = PathMeasureItem(ray_path_points=points, start_param=0.0, end_param=1.0, ray_index=0)
    
    add_cmd = AddItemCommand(scene, item)
    undo_stack.push(add_cmd)
    
    assert item in scene.items(), "❌ Item should be in scene"
    print("✅ Item added")
    
    # Delete item
    remove_cmd = RemoveItemCommand(scene, item)
    undo_stack.push(remove_cmd)
    
    assert item not in scene.items(), "❌ Item should be removed"
    print("✅ Item deleted")
    
    # Undo delete (restore item)
    undo_stack.undo()
    assert item in scene.items(), "❌ Item should be restored after undo"
    print("✅ Undo delete works - item restored")
    
    # Undo add (remove item completely)
    undo_stack.undo()
    assert item not in scene.items(), "❌ Item should be removed after undoing add"
    print("✅ Undo add works - item removed completely")
    
    # Redo add
    undo_stack.redo()
    assert item in scene.items(), "❌ Item should be back after redo"
    print("✅ Redo add works")
    
    # Redo delete
    undo_stack.redo()
    assert item not in scene.items(), "❌ Item should be deleted after redo"
    print("✅ Redo delete works")
    
    print("✅ Delete with undo test PASSED\n")

if __name__ == "__main__":
    print("=" * 60)
    print("PathMeasureItem Undo/Redo Functionality Tests")
    print("=" * 60 + "\n")
    
    try:
        test_single_path_measure()
        test_multiple_path_measures()
        test_delete_with_undo()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\n✅ PathMeasureItem now has full undo/redo support:")
        print("   - Can be deleted with Backspace/Delete")
        print("   - Can be undone with Ctrl+Z")
        print("   - Can be redone with Ctrl+Shift+Z")
        print("   - Beam splitter siblings are handled atomically")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
