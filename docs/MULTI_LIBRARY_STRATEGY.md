# Multi-Library Strategy for Portable Assemblies

## Problem Statement

Current implementation has issues with library portability:

1. **Library name hardcoded in paths**: `@library/user_library/component/...`
2. **Renaming breaks references**: If user renames library folder, assemblies break
3. **Multi-PC workflow unclear**: How to merge libraries from different computers?
4. **No conflict resolution**: What if two PCs have different components with same name?

## Proposed Solutions

### Option 1: Component-Relative Paths (RECOMMENDED)

**Format**: `@component/{component_name}/images/file.png`

**Advantages**:
- ✅ Library name doesn't matter
- ✅ Works across any library
- ✅ Simple and intuitive
- ✅ Easy to merge libraries

**How it works**:
1. When saving: Search all configured libraries for the component folder
2. Store path as `@component/achromat_doublet/images/lens.png`
3. When loading: Search all libraries for a folder named `achromat_doublet`
4. If found in multiple libraries, use first match (or show dialog)

**Example**:
```json
{
  "image_path": "@component/achromat_doublet/images/lens.png"
}
```

This works if the library is named:
- `user_library/achromat_doublet/`
- `pc1_library/achromat_doublet/`
- `optics_components/achromat_doublet/`

### Option 2: Library Aliases

**Format**: `@library/{alias}/component/...`

**How it works**:
1. User assigns aliases to library paths in preferences
2. Assemblies use aliases instead of folder names
3. On other PC, user maps alias to their local path

**Example preferences**:
```json
{
  "library_aliases": {
    "main": "/Users/benny/Libraries/ComponentLibraries/user_library",
    "shared": "/Users/benny/Libraries/ComponentLibraries/team_library"
  }
}
```

**Assembly**:
```json
{
  "image_path": "@library/main/achromat_doublet/images/lens.png"
}
```

**Advantages**:
- ✅ Explicit library management
- ✅ Multiple libraries clearly separated
- ✅ Can have different versions in different libraries

**Disadvantages**:
- ❌ More complex setup
- ❌ User must configure aliases
- ❌ Still breaks if alias not configured

### Option 3: Embedded Component Metadata

**Format**: Store component folder name in assembly

**How it works**:
1. Assembly stores both path and component folder name
2. On load, search for component folder in all libraries
3. Use found path, ignore saved path if not found

**Example**:
```json
{
  "image_path": "@library/user_library/achromat_doublet/images/lens.png",
  "component_folder": "achromat_doublet"
}
```

**Advantages**:
- ✅ Backward compatible
- ✅ Fallback mechanism
- ✅ Still readable

### Option 4: UUID-Based Components

**Format**: Each component has a unique ID

**How it works**:
1. Components have a UUID in their `component.json`
2. Assemblies reference components by UUID
3. Library maintains index of UUID → path

**Example component.json**:
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Achromatic Doublet 50mm",
  "image_path": "images/lens.png"
}
```

**Assembly**:
```json
{
  "component_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Advantages**:
- ✅ Globally unique, never conflicts
- ✅ Can track component versions
- ✅ Professional approach

**Disadvantages**:
- ❌ Requires component.json updates
- ❌ More complex implementation
- ❌ UUIDs not human-readable

## Recommended Implementation

**Hybrid Approach: Component-Relative with Fallback**

1. **Primary**: Use `@component/{name}/` format
2. **Fallback**: If component not found, try exact library path
3. **Search**: Look in all configured libraries + subdirectories

### Path Format

```
@component/{component_folder_name}/{relative_path}
```

Examples:
```
@component/achromat_doublet/images/lens.png
@component/mirror_50mm/images/mirror_front.png
@component/beamsplitter_cube/images/bs.png
```

### Search Algorithm

```python
def resolve_component_path(component_path: str) -> str:
    """
    Resolve @component/... path by searching all libraries.
    
    Format: @component/{component_name}/{relative_path}
    Example: @component/achromat_doublet/images/lens.png
    """
    if not component_path.startswith("@component/"):
        return component_path
    
    # Extract component name and relative path
    parts = component_path[11:].split("/", 1)  # len("@component/") = 11
    component_name = parts[0]
    relative_path = parts[1] if len(parts) > 1 else ""
    
    # Search all configured libraries
    for library_root in get_all_library_roots():
        # Direct check
        component_dir = library_root / component_name
        if component_dir.exists():
            return str(component_dir / relative_path)
        
        # Search subdirectories (one level deep)
        for subdir in library_root.iterdir():
            if subdir.is_dir():
                component_dir = subdir / component_name
                if component_dir.exists():
                    return str(component_dir / relative_path)
    
    # Not found
    return None
```

### Backward Compatibility

Keep support for old `@library/` format:

```python
def to_absolute_path(path: str, library_roots=None):
    if path.startswith("@component/"):
        return resolve_component_path(path)
    elif path.startswith("@library/"):
        return resolve_library_relative_path(path, library_roots)
    else:
        return resolve_package_relative_path(path)
```

### Migration Path

1. **Phase 1**: Implement `@component/` format alongside `@library/`
2. **Phase 2**: Update serialization to prefer `@component/`
3. **Phase 3**: Keep `@library/` for backward compatibility
4. Old assemblies continue to work
5. New assemblies use better format

## Multi-PC Workflow

With component-relative paths:

**PC 1** (Benny):
```
~/Documents/Optiverse/ComponentLibraries/user_library/
  ├── achromat_doublet/
  ├── mirror_50mm/
  └── beamsplitter/
```

**PC 2** (Colleague):
```
~/Libraries/optics/
  ├── achromat_doublet/      # Same component
  ├── mirror_50mm/           # Same component
  └── custom_lens/           # Different component
```

**Assembly saved on PC 1**:
```json
{
  "image_path": "@component/achromat_doublet/images/lens.png"
}
```

**Opened on PC 2**: ✅ Works! Searches all libraries, finds `achromat_doublet`

### Merging Libraries

To merge libraries from two PCs:

```bash
# PC 2 receives PC 1's library
cp -r ~/Downloads/benny_library ~/Libraries/optics/benny_library

# Add to preferences
# Now has both libraries available
```

Assemblies work because they search all configured libraries.

## Implementation Checklist

- [ ] Add `resolve_component_path()` to `platform/paths.py`
- [ ] Add `make_component_relative()` to convert absolute → `@component/`
- [ ] Update `serialize_item()` to use `@component/` format
- [ ] Update `deserialize_item()` to support `@component/` format
- [ ] Keep `@library/` support for backward compatibility
- [ ] Add tests for component resolution
- [ ] Update documentation
- [ ] Add migration note in release notes

## Future Enhancements

1. **Component versioning**: `@component/achromat_doublet@v2/...`
2. **Conflict resolution dialog**: If component in multiple libraries, ask user
3. **Library sync**: Sync components across PCs
4. **Component marketplace**: Share components with community
