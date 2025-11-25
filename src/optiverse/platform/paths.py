from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6 import QtCore

_logger = logging.getLogger(__name__)


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def _app_data_root() -> Path:
    # Prefer Qt standard writable location
    base = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.AppDataLocation
    )
    if not base:
        # Fallback to HOME
        home = (
            os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
        )
        base = os.path.join(home, ".optiverse")
    root = Path(base) / "Optiverse"
    root.mkdir(parents=True, exist_ok=True)
    return root


def library_root_dir() -> str:
    root = _app_data_root() / "library"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def assets_dir() -> str:
    d = Path(library_root_dir()) / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def svg_cache_dir() -> str:
    """Get the SVG rendering cache directory."""
    d = _app_data_root() / "svg_cache"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def get_user_library_root() -> Path:
    """
    Get the default user component library root directory.

    This is where user-created components are stored in folder-based structure,
    similar to the built-in library format.

    Default location: Documents/Optiverse/ComponentLibraries/user_library/

    Returns:
        Path to the user library root directory
    """
    # Use Qt's DocumentsLocation for cross-platform compatibility
    docs_location = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.DocumentsLocation
    )

    if not docs_location:
        # Fallback to home directory
        home = (
            os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
        )
        docs_location = home

    # Create the library directory structure
    library_root = Path(docs_location) / "Optiverse" / "ComponentLibraries" / "user_library"
    library_root.mkdir(parents=True, exist_ok=True)

    return library_root


def get_all_custom_library_roots() -> list[Path]:
    """
    Get all custom component library directories by scanning ComponentLibraries/.

    Auto-discovers all subdirectories under Documents/Optiverse/ComponentLibraries/
    allowing users to organize components into multiple libraries (e.g., lab_equipment/,
    vendor_catalog/, experiments/) without merging everything into user_library/.

    Returns:
        List of Path objects for all library directories found under ComponentLibraries/
    """
    # Use Qt's DocumentsLocation for cross-platform compatibility
    docs_location = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.StandardLocation.DocumentsLocation
    )

    if not docs_location:
        # Fallback to home directory
        home = (
            os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
        )
        docs_location = home

    # Get the ComponentLibraries parent directory
    component_libraries_root = Path(docs_location) / "Optiverse" / "ComponentLibraries"

    # Ensure it exists
    component_libraries_root.mkdir(parents=True, exist_ok=True)

    # Scan for all subdirectories
    library_paths = []
    try:
        for item in component_libraries_root.iterdir():
            if item.is_dir():
                library_paths.append(item)
    except OSError as e:
        _logger.debug("Failed to scan component libraries: %s", e)

    return library_paths


def get_custom_library_path(library_path: str) -> Path | None:
    """
    Validate and return a custom library path.

    Args:
        library_path: Path to a custom component library directory

    Returns:
        Path object if valid, None if invalid
    """
    if not library_path:
        return None

    try:
        path = Path(library_path).resolve()

        # Check if path exists and is a directory
        if not path.exists():
            return None

        if not path.is_dir():
            return None

        return path
    except (OSError, ValueError) as e:
        _logger.debug("Invalid library path %r: %s", library_path, e)
        return None


def get_builtin_library_root() -> Path:
    """
    Get the built-in component library root directory.

    This is where standard components are stored within the package.

    Returns:
        Path to src/optiverse/objects/library/
    """
    return get_package_root() / "objects" / "library"


def get_package_root() -> Path:
    """
    Get the package root directory (src/optiverse).

    Returns:
        Path to the optiverse package root
    """
    # This file is at src/optiverse/platform/paths.py
    # Go up two levels to get to src/optiverse
    return Path(__file__).parent.parent


def get_package_images_dir() -> Path:
    """
    Get the package images directory.

    Returns:
        Path to src/optiverse/objects/images
    """
    return get_package_root() / "objects" / "images"


def is_package_image(image_path: str | None) -> bool:
    """
    Check if an image path is within the package.

    Args:
        image_path: Path to check (can be absolute or relative)

    Returns:
        True if the image is inside the package, False otherwise
    """
    if not image_path:
        return False

    try:
        path = Path(image_path).resolve()
        package_root = get_package_root().resolve()

        # Check if the path is relative to the package root
        try:
            path.relative_to(package_root)
            return True
        except ValueError:
            return False
    except OSError as e:
        _logger.debug("Failed to check if path is in package %r: %s", image_path, e)
        return False


def to_relative_path(image_path: str | None) -> str | None:
    """
    Convert an absolute image path to a relative path if it's within the package.
    Otherwise, keep it as absolute.

    Args:
        image_path: Absolute or relative path to an image

    Returns:
        Relative path (from package root) if within package, otherwise absolute path
    """
    if not image_path:
        return image_path

    try:
        path = Path(image_path)

        # If already relative, return as-is
        if not path.is_absolute():
            return image_path

        # Try to make it relative to package root
        package_root = get_package_root().resolve()
        abs_path = path.resolve()

        try:
            rel_path = abs_path.relative_to(package_root)
            # Return with forward slashes for cross-platform compatibility
            return rel_path.as_posix()
        except ValueError:
            # Path is outside package, return absolute with forward slashes
            return abs_path.as_posix()
    except OSError as e:
        _logger.debug("Failed to convert path to relative %r: %s", image_path, e)
        return image_path


def to_absolute_path(
    image_path: str | None, library_roots: list[Path] | None = None
) -> str | None:
    """
    Convert a relative image path to absolute, assuming it's relative to package root.
    If already absolute, verify it exists or leave as-is.

    Supports multiple path formats:
    - @component/{component_name}/... - Component-relative (library-agnostic, PREFERRED)
    - @library/{library_name}/... - Library-relative (backward compatibility)
    - Relative paths - Assumed relative to package root

    Args:
        image_path: Relative or absolute path to an image
        library_roots: Optional list of library root paths for resolving special formats

    Returns:
        Absolute path to the image
    """
    if not image_path:
        return image_path

    try:
        # Handle component-relative paths: @component/{component_name}/... (PREFERRED)
        if image_path.startswith("@component/"):
            return resolve_component_path(image_path, library_roots)

        # Handle library-relative paths: @library/{library_name}/... (BACKWARD COMPATIBILITY)
        if image_path.startswith("@library/"):
            return resolve_library_relative_path(image_path, library_roots)

        path = Path(image_path)

        # If already absolute, return as-is
        if path.is_absolute():
            return str(path)

        # Assume relative to package root
        package_root = get_package_root()
        abs_path = (package_root / path).resolve()

        return str(abs_path)
    except OSError as e:
        _logger.debug("Failed to convert path to absolute %r: %s", image_path, e)
        return image_path


def get_all_library_roots(settings_service=None) -> list[Path]:
    """
    Get all configured library roots (user default + custom libraries).

    Args:
        settings_service: Optional SettingsService instance for loading custom paths

    Returns:
        List of Path objects for all library directories
    """
    libraries = []

    # Always include default user library
    libraries.append(get_user_library_root())

    # Load custom library paths from settings if available
    if settings_service is not None:
        try:
            custom_paths = settings_service.get_value("library_paths", [], list)
            for path_str in custom_paths:
                if path_str:
                    path = Path(path_str)
                    if path.exists() and path.is_dir() and path not in libraries:
                        libraries.append(path)
        except (OSError, TypeError, ValueError) as e:
            _logger.debug("Failed to load custom library paths from settings: %s", e)
    else:
        # Fallback: scan ComponentLibraries directory
        libraries.extend(get_all_custom_library_roots())

    # Remove duplicates while preserving order
    seen = set()
    unique_libraries = []
    for lib in libraries:
        lib_resolved = lib.resolve()
        if lib_resolved not in seen:
            seen.add(lib_resolved)
            unique_libraries.append(lib)

    return unique_libraries


def resolve_library_relative_path(
    rel_path: str, library_roots: list[Path] | None = None
) -> str | None:
    """
    Resolve a library-relative path to absolute path.

    Format: @library/{library_name}/{component_folder}/images/{filename}
    Example: @library/user_library/achromat_doublet/images/lens.png

    Args:
        rel_path: Library-relative path starting with @library/
        library_roots: Optional list of library roots to search. If None, uses all configured libraries.

    Returns:
        Absolute path if library is found, None if library not found
        Note: Does not check if the final file exists - just resolves the path
    """
    if not rel_path or not rel_path.startswith("@library/"):
        return None

    # Remove @library/ prefix
    path_after_prefix = rel_path[9:]  # len("@library/") == 9

    # Extract library name (first path component)
    parts = path_after_prefix.split("/")
    if len(parts) < 2:
        return None

    library_name = parts[0]
    relative_path = "/".join(parts[1:])

    # Get library roots to search
    if library_roots is None:
        library_roots = get_all_library_roots()

    # Search for matching library
    for lib_root in library_roots:
        # Check if this library's name matches
        if lib_root.name == library_name or lib_root.stem == library_name:
            # Construct full path (even if file doesn't exist yet)
            full_path = lib_root / relative_path
            return str(full_path.resolve())

    # Library not found
    return None


def make_library_relative(
    abs_path: str, library_roots: list[Path] | None = None
) -> str | None:
    """
    Convert an absolute path to library-relative format if it's within a library.

    Args:
        abs_path: Absolute path to convert
        library_roots: Optional list of library roots. If None, uses all configured libraries.

    Returns:
        Library-relative path (@library/...) if within a library, None otherwise
    """
    if not abs_path:
        return None

    try:
        path = Path(abs_path).resolve()

        # Get library roots to check
        if library_roots is None:
            library_roots = get_all_library_roots()

        # Check if path is within any library
        for lib_root in library_roots:
            lib_root_resolved = lib_root.resolve()
            try:
                # Get relative path from library root
                rel_to_lib = path.relative_to(lib_root_resolved)
                # Construct library-relative path
                library_name = lib_root_resolved.name
                return f"@library/{library_name}/{rel_to_lib.as_posix()}"
            except ValueError:
                # Path is not relative to this library
                continue

        # Not in any library
        return None
    except OSError as e:
        _logger.debug("Failed to convert to library path %r: %s", abs_path, e)
        return None


def resolve_component_path(
    component_path: str, library_roots: list[Path] | None = None
) -> str | None:
    """
    Resolve a component-relative path to absolute path.

    Component-relative paths are library-agnostic and search all configured libraries.
    This makes assemblies portable across different library structures and renames.

    Format: @component/{component_name}/{relative_path}
    Example: @component/achromat_doublet/images/lens.png

    Args:
        component_path: Component-relative path starting with @component/
        library_roots: Optional list of library roots to search. If None, uses all configured libraries.

    Returns:
        Absolute path if component found, None if not found in any library
    """
    if not component_path or not component_path.startswith("@component/"):
        return None

    # Remove @component/ prefix
    path_after_prefix = component_path[11:]  # len("@component/") == 11

    # Extract component name (first path component)
    parts = path_after_prefix.split("/")
    if len(parts) < 1:
        return None

    component_name = parts[0]
    relative_path = "/".join(parts[1:]) if len(parts) > 1 else ""

    # Get library roots to search
    if library_roots is None:
        library_roots = get_all_library_roots()

    # Search for component in all libraries
    for lib_root in library_roots:
        # Try direct match (component at library root)
        component_dir = lib_root / component_name
        if component_dir.exists() and component_dir.is_dir():
            full_path = component_dir / relative_path if relative_path else component_dir
            return str(full_path.resolve())

        # Try one level deep (common structure: library/category/component)
        for subdir in lib_root.iterdir():
            if subdir.is_dir():
                component_dir = subdir / component_name
                if component_dir.exists() and component_dir.is_dir():
                    full_path = component_dir / relative_path if relative_path else component_dir
                    return str(full_path.resolve())

    # Component not found in any library
    return None


def make_component_relative(
    abs_path: str, library_roots: list[Path] | None = None
) -> str | None:
    """
    Convert an absolute path to component-relative format if it's within a library.

    Component-relative paths are preferred over library-relative paths because they
    are independent of library folder names, making them more portable.

    Args:
        abs_path: Absolute path to convert
        library_roots: Optional list of library roots. If None, uses all configured libraries.

    Returns:
        Component-relative path (@component/...) if within a library, None otherwise
    """
    if not abs_path:
        return None

    try:
        path = Path(abs_path).resolve()

        # Get library roots to check
        if library_roots is None:
            library_roots = get_all_library_roots()

        # Check if path is within any library
        for lib_root in library_roots:
            lib_root_resolved = lib_root.resolve()
            try:
                # Get relative path from library root
                rel_to_lib = path.relative_to(lib_root_resolved)

                # Extract component name (first directory in the relative path)
                parts = rel_to_lib.parts
                if len(parts) >= 1:
                    component_name = parts[0]
                    relative_path = "/".join(parts[1:]) if len(parts) > 1 else ""

                    # Return component-relative format
                    if relative_path:
                        return f"@component/{component_name}/{relative_path}"
                    else:
                        return f"@component/{component_name}"
            except ValueError:
                # Path is not relative to this library
                continue

        # Not in any library
        return None
    except OSError as e:
        _logger.debug("Failed to convert to component path %r: %s", abs_path, e)
        return None
