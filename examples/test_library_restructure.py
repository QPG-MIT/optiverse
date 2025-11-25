#!/usr/bin/env python3
"""
Test script for the component library restructure.

This script tests the new folder-based component library system including:
- Folder-based storage
- Export/import functionality
- Loading from multiple libraries
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path

# Add src to path so we can import optiverse
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_folder_based_storage():
    """Test that components are saved in folder structure."""
    print("\n=== Test 1: Folder-Based Storage ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        from optiverse.services.storage_service import StorageService
        from optiverse.core.models import ComponentRecord
        from optiverse.core.interface_definition import InterfaceDefinition

        # Create a temporary library
        library_path = Path(tmpdir) / "test_library"
        library_path.mkdir()

        storage = StorageService(str(library_path))

        # Create a test component
        test_component = ComponentRecord(
            name="Test Lens 1",
            image_path="",
            object_height_mm=25.4,
            angle_deg=0.0,
            category="lenses",
            interfaces=[
                InterfaceDefinition(
                    x1_mm=0.0, y1_mm=12.7,
                    x2_mm=0.0, y2_mm=-12.7,
                    element_type="lens",
                    n1=1.0, n2=1.0,
                    efl_mm=100.0
                )
            ],
            notes="Test component"
        )

        # Save component
        storage.save_component(test_component)

        # Check folder structure
        component_folder = library_path / "test_lens_1"
        assert component_folder.exists(), "Component folder not created"
        assert (component_folder / "component.json").exists(), "component.json not created"

        # Load and verify
        loaded = storage.load_library()
        assert len(loaded) == 1, f"Expected 1 component, got {len(loaded)}"
        assert loaded[0]["name"] == "Test Lens 1", "Component name mismatch"
        assert loaded[0]["category"] == "lenses", "Category mismatch"

        print("[OK] Folder-based storage works correctly")
        print(f"  - Component saved to: {component_folder}")
        print(f"  - Loaded {len(loaded)} component(s)")


def test_export_import():
    """Test export and import of components."""
    print("\n=== Test 2: Export/Import ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        from optiverse.services.storage_service import StorageService
        from optiverse.core.models import ComponentRecord
        from optiverse.core.interface_definition import InterfaceDefinition

        # Create source library
        source_lib = Path(tmpdir) / "source_library"
        source_lib.mkdir()

        storage1 = StorageService(str(source_lib))

        # Create and save a component
        test_component = ComponentRecord(
            name="Export Test Component",
            image_path="",
            object_height_mm=50.0,
            angle_deg=0.0,
            category="mirrors",
            interfaces=[
                InterfaceDefinition(
                    x1_mm=0.0, y1_mm=25.0,
                    x2_mm=0.0, y2_mm=-25.0,
                    element_type="mirror",
                    n1=1.0, n2=1.0
                )
            ],
            notes="Component for export test"
        )

        storage1.save_component(test_component)

        # Export component
        export_dest = Path(tmpdir) / "exports"
        export_dest.mkdir()

        success = storage1.export_component("Export Test Component", str(export_dest))
        assert success, "Export failed"

        exported_folder = export_dest / "export_test_component"
        assert exported_folder.exists(), "Exported folder not found"
        assert (exported_folder / "component.json").exists(), "Exported component.json not found"

        print("[OK] Export successful")
        print(f"  - Exported to: {exported_folder}")

        # Import into new library
        dest_lib = Path(tmpdir) / "dest_library"
        dest_lib.mkdir()

        storage2 = StorageService(str(dest_lib))

        success = storage2.import_component(str(exported_folder))
        assert success, "Import failed"

        # Verify import
        loaded = storage2.load_library()
        assert len(loaded) == 1, f"Expected 1 component after import, got {len(loaded)}"
        assert loaded[0]["name"] == "Export Test Component", "Imported component name mismatch"

        print("[OK] Import successful")
        print(f"  - Imported to: {dest_lib}")
        print(f"  - Component name: {loaded[0]['name']}")


def test_multiple_libraries():
    """Test loading from multiple library sources."""
    print("\n=== Test 3: Multiple Libraries ===")

    from optiverse.objects.definitions_loader import load_component_dicts
    from optiverse.platform.paths import get_builtin_library_root, get_user_library_root

    # Load built-in components
    builtin_root = get_builtin_library_root()
    print(f"  Built-in library: {builtin_root}")

    builtin_components = load_component_dicts()
    print(f"  [OK] Loaded {len(builtin_components)} built-in component(s)")

    # Show sample component names
    if builtin_components:
        sample_names = [c.get("name", "unnamed") for c in builtin_components[:3]]
        print(f"    Sample: {', '.join(sample_names)}")

    # Get user library location
    user_root = get_user_library_root()
    print(f"  User library: {user_root}")

    user_components = load_component_dicts(user_root)
    print(f"  [OK] Loaded {len(user_components)} user component(s)")

    print(f"  Total components: {len(builtin_components) + len(user_components)}")


def test_image_handling():
    """Test that images are copied into component folders."""
    print("\n=== Test 4: Image Handling ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        from optiverse.services.storage_service import StorageService
        from optiverse.core.models import ComponentRecord

        # Create a test image
        test_image = Path(tmpdir) / "test_image.png"
        test_image.write_text("fake image data")

        # Create library
        library_path = Path(tmpdir) / "test_library"
        library_path.mkdir()

        storage = StorageService(str(library_path))

        # Create component with image
        component = ComponentRecord(
            name="Component with Image",
            image_path=str(test_image),
            object_height_mm=30.0,
            angle_deg=0.0,
            category="lenses",
            interfaces=[],
            notes=""
        )

        # Save component
        storage.save_component(component)

        # Check image was copied
        component_folder = library_path / "component_with_image"
        images_folder = component_folder / "images"

        assert images_folder.exists(), "Images folder not created"

        copied_images = list(images_folder.glob("*.png"))
        assert len(copied_images) > 0, "Image not copied to component folder"

        print("[OK] Image handling works correctly")
        print(f"  - Image copied to: {images_folder}")
        print(f"  - Found {len(copied_images)} image(s) in component folder")

        # Verify component.json has relative image path
        json_path = component_folder / "component.json"
        with open(json_path) as f:
            data = json.load(f)

        image_path = data.get("image_path", "")
        assert image_path.startswith("images/"), f"Image path should be relative, got: {image_path}"
        print(f"  - Image path in JSON: {image_path}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Component Library Restructure Test Suite")
    print("=" * 60)

    try:
        test_folder_based_storage()
        test_export_import()
        test_multiple_libraries()
        test_image_handling()

        print("\n" + "=" * 60)
        print("[PASS] All tests passed successfully!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAIL] Test failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())



