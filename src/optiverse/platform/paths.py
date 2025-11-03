from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore


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
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppDataLocation)
    if not base:
        # Fallback to HOME
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
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


def get_library_path() -> str:
    """Get the legacy flat JSON library path (for backwards compatibility)."""
    return str(Path(library_root_dir()) / "components_library.json")


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
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
        docs_location = home
    
    # Create the library directory structure
    library_root = Path(docs_location) / "Optiverse" / "ComponentLibraries" / "user_library"
    library_root.mkdir(parents=True, exist_ok=True)
    
    return library_root


def get_custom_library_path(library_path: str) -> Optional[Path]:
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
    except Exception:
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


def is_package_image(image_path: Optional[str]) -> bool:
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
    except Exception:
        return False


def to_relative_path(image_path: Optional[str]) -> Optional[str]:
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
    except Exception:
        return image_path


def to_absolute_path(image_path: Optional[str]) -> Optional[str]:
    """
    Convert a relative image path to absolute, assuming it's relative to package root.
    If already absolute, verify it exists or leave as-is.
    
    Args:
        image_path: Relative or absolute path to an image
    
    Returns:
        Absolute path to the image
    """
    if not image_path:
        return image_path
    
    try:
        path = Path(image_path)
        
        # If already absolute, return as-is
        if path.is_absolute():
            return str(path)
        
        # Assume relative to package root
        package_root = get_package_root()
        abs_path = (package_root / path).resolve()
        
        return str(abs_path)
    except Exception:
        return image_path


