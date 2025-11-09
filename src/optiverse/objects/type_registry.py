"""
Type registry for serializable optical components.

Provides decorator-based registration and helper functions for clean,
extensible save/load without hardcoded type checks.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Dict, Any, Optional, Type

from ..platform.paths import (
    to_relative_path, 
    to_absolute_path, 
    make_library_relative,
    get_all_library_roots
)
from ..core.interface_definition import InterfaceDefinition


class TypeRegistry:
    """
    Central registry mapping type names to item classes.
    
    Usage:
        @register_type("mirror", MirrorParams)
        class MirrorItem(BaseObj):
            pass
    """
    _registry: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, type_name: str, params_class: Optional[Type] = None):
        """
        Decorator to register an item class with the type registry.
        
        Args:
            type_name: Unique identifier for this type (e.g., "mirror", "lens")
            params_class: Dataclass used for this item's parameters (e.g., MirrorParams)
        
        Returns:
            Decorator function that registers the class
        """
        def decorator(item_class):
            cls._registry[type_name] = {
                'class': item_class,
                'params_class': params_class
            }
            # Set attributes on the class for easy access
            item_class.type_name = type_name
            item_class.params_class = params_class
            return item_class
        return decorator
    
    @classmethod
    def get_class(cls, type_name: str) -> Optional[Type]:
        """Get the item class for a given type name."""
        entry = cls._registry.get(type_name)
        return entry['class'] if entry else None
    
    @classmethod
    def get_params_class(cls, type_name: str) -> Optional[Type]:
        """Get the params class for a given type name."""
        entry = cls._registry.get(type_name)
        return entry['params_class'] if entry else None
    
    @classmethod
    def get_all_types(cls) -> list[str]:
        """Get list of all registered type names."""
        return list(cls._registry.keys())


# Decorator alias for convenience
register_type = TypeRegistry.register


def serialize_item(item) -> Dict[str, Any]:
    """
    Generic item serialization using vars() introspection.
    
    Captures ALL attributes automatically, including dynamic attributes
    added at runtime. Works for any item with a params attribute.
    
    Args:
        item: Item to serialize (must have params attribute)
    
    Returns:
        Dictionary ready for JSON serialization
    """
    # Start with all params attributes (dataclass fields + dynamic)
    d = vars(item.params).copy()
    
    # Add positional metadata from Qt transforms
    d["x_mm"] = float(item.pos().x())
    d["y_mm"] = float(item.pos().y())
    
    # Convert Qt rotation to user angle (if item uses angles)
    if hasattr(item, 'rotation'):
        # Import here to avoid circular dependency
        from ..core.geometry import qt_angle_to_user
        d["angle_deg"] = qt_angle_to_user(item.rotation())
    
    # Add item metadata from registry (extensible and automatic)
    if hasattr(item, '_metadata_registry'):
        for key, getter in item._metadata_registry.items():
            try:
                d[key] = getter(item)
            except Exception:
                # Skip metadata if getter fails (e.g., attribute doesn't exist)
                pass
    
    # Add type marker
    d["_type"] = item.type_name
    
    # Convert image path to library-relative (preferred) or package-relative
    if "image_path" in d and d["image_path"]:
        # Try to get library roots from the item's scene/view context
        library_roots = None
        try:
            # Get the scene from the item
            scene = item.scene()
            if scene:
                # Get all views for this scene
                views = scene.views()
                if views:
                    # Get the main window from the view
                    view = views[0]
                    main_window = view.window()
                    if hasattr(main_window, 'settings'):
                        library_roots = get_all_library_roots(main_window.settings)
        except Exception:
            # If we can't get library roots, that's okay - will fall back to package-relative
            pass
        
        # Try library-relative first (for user components)
        lib_relative = make_library_relative(d["image_path"], library_roots)
        if lib_relative:
            # Successfully converted to library-relative format
            d["image_path"] = lib_relative
        else:
            # Fall back to package-relative (for built-in components)
            d["image_path"] = to_relative_path(d["image_path"])
    
    # Explicitly serialize interfaces using their to_dict() method
    if "interfaces" in d and d["interfaces"]:
        d["interfaces"] = [iface.to_dict() for iface in d["interfaces"]]
    
    return d


def deserialize_item(data: Dict[str, Any]):
    """
    Generic item deserialization using registry lookup.
    
    Handles type lookup, params reconstruction, dynamic attribute restoration,
    and metadata restoration automatically.
    
    Args:
        data: Dictionary from JSON deserialization
    
    Returns:
        Reconstructed item instance, or None if type not found
    """
    # Extract type and look up in registry
    type_name = data.get("_type")
    if not type_name:
        return None
    
    item_class = TypeRegistry.get_class(type_name)
    params_class = TypeRegistry.get_params_class(type_name)
    
    if not item_class or not params_class:
        print(f"Warning: Unknown item type '{type_name}', skipping")
        return None
    
    # Make a copy to avoid mutating input
    d = data.copy()
    
    # Convert library-relative or package-relative path to absolute
    if "image_path" in d and d["image_path"]:
        # Try to get library roots from current context
        # Note: During deserialization, we don't have item context yet
        # So we'll just use default library paths
        library_roots = get_all_library_roots()
        d["image_path"] = to_absolute_path(d["image_path"], library_roots)
    
    # Deserialize interfaces from dicts to InterfaceDefinition objects
    if "interfaces" in d and d["interfaces"]:
        d["interfaces"] = [InterfaceDefinition.from_dict(iface) for iface in d["interfaces"]]
    
    # Extract metadata that's not part of Params
    item_uuid = d.pop("item_uuid", None)
    z_value = d.pop("z_value", None)
    locked = d.pop("locked", None)
    d.pop("_type", None)  # Remove type marker
    
    # FUTURE-PROOF: Separate dataclass fields from dynamic attributes
    field_names = {f.name for f in fields(params_class)}
    params_dict = {k: v for k, v in d.items() if k in field_names}
    dynamic_attrs = {k: v for k, v in d.items() if k not in field_names}
    
    # Create params with dataclass fields
    params = params_class(**params_dict)
    
    # Restore dynamic attributes (handles ANY attribute automatically!)
    for key, value in dynamic_attrs.items():
        # JSON converts tuples to lists, convert back if needed
        if isinstance(value, list) and key.endswith('_mm'):
            value = tuple(value)
        setattr(params, key, value)
    
    # Create item with fully restored params
    item = item_class(params, item_uuid)
    
    # Restore metadata
    if z_value is not None:
        item.setZValue(z_value)
    if locked is not None:
        item.set_locked(locked)
    
    return item

