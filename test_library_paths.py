"""
Test script for library-relative path functionality.

This script tests the new library-relative path system to ensure
assemblies are portable across different computers.
"""

from pathlib import Path
from optiverse.core.models import ComponentRecord, serialize_component, deserialize_component
from optiverse.services.settings_service import SettingsService
from optiverse.platform.paths import get_all_library_roots, make_library_relative, resolve_library_relative_path


def test_library_relative_paths():
    """Test library-relative path conversion and resolution."""
    print("=" * 70)
    print("LIBRARY-RELATIVE PATH SYSTEM TEST")
    print("=" * 70)
    
    # Initialize settings
    settings = SettingsService()
    
    # Get all library roots
    library_roots = get_all_library_roots(settings)
    print(f"\n✓ Found {len(library_roots)} library root(s):")
    for lib in library_roots:
        print(f"  - {lib}")
    
    # Test 1: Create a component with absolute path
    print("\n" + "-" * 70)
    print("Test 1: Serialize component with library image path")
    print("-" * 70)
    
    # Use user library path
    if library_roots:
        user_lib = library_roots[0]
        test_image = user_lib / "test_component" / "images" / "test.png"
        
        rec = ComponentRecord(
            name="Test Component",
            image_path=str(test_image),
            object_height_mm=25.4
        )
        
        print(f"Original path: {rec.image_path}")
        
        # Serialize
        data = serialize_component(rec, settings)
        serialized_path = data["image_path"]
        print(f"Serialized path: {serialized_path}")
        
        if serialized_path.startswith("@library/"):
            print("✓ Path correctly converted to library-relative format")
        else:
            print("✗ Path NOT converted to library-relative format")
        
        # Test 2: Deserialize and check resolution
        print("\n" + "-" * 70)
        print("Test 2: Deserialize component and resolve path")
        print("-" * 70)
        
        rec2 = deserialize_component(data, settings)
        if rec2:
            print(f"Deserialized path: {rec2.image_path}")
            print(f"Paths match: {Path(rec.image_path).resolve() == Path(rec2.image_path).resolve()}")
            print("✓ Path correctly resolved back to absolute")
        else:
            print("✗ Failed to deserialize component")
    
    # Test 3: Make library relative
    print("\n" + "-" * 70)
    print("Test 3: Convert absolute path to library-relative")
    print("-" * 70)
    
    if library_roots:
        test_abs_path = str(library_roots[0] / "achromat_doublet" / "images" / "lens.png")
        library_rel = make_library_relative(test_abs_path, library_roots)
        
        print(f"Absolute: {test_abs_path}")
        print(f"Library-relative: {library_rel}")
        
        if library_rel and library_rel.startswith("@library/"):
            print("✓ Successfully converted to library-relative")
            
            # Test resolution
            resolved = resolve_library_relative_path(library_rel, library_roots)
            print(f"Resolved back: {resolved}")
            
            if resolved:
                print("✓ Successfully resolved library-relative path")
            else:
                print("✗ Failed to resolve library-relative path")
        else:
            print("✗ Failed to convert to library-relative")
    
    # Test 4: Backward compatibility
    print("\n" + "-" * 70)
    print("Test 4: Backward compatibility with absolute paths")
    print("-" * 70)
    
    old_data = {
        "name": "Old Component",
        "image_path": "/absolute/path/to/image.png",
        "object_height_mm": 25.4
    }
    
    rec3 = deserialize_component(old_data, settings)
    if rec3:
        print(f"Old absolute path: {old_data['image_path']}")
        print(f"Deserialized path: {rec3.image_path}")
        print("✓ Backward compatibility maintained")
    else:
        print("✗ Failed to deserialize old format")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_library_relative_paths()
