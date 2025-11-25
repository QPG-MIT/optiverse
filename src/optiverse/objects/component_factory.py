"""
ComponentFactory - Unified component creation system.

This module provides a single source of truth for creating optical components
from library data. Used by both ghost preview and actual component creation
to ensure perfect consistency.

Key principle: "What You See Is What You Drop"
"""
from __future__ import annotations

from typing import Optional, Dict, Any

from ..core.models import ComponentParams
from ..core.interface_definition import InterfaceDefinition
from ..platform.paths import to_absolute_path
from .base_obj import BaseObj


class ComponentFactory:
    """
    Single source of truth for creating optical components from ComponentRecord data.

    This factory eliminates code duplication between ghost preview and actual
    component creation, ensuring they produce identical results.

    Usage:
        # Ghost preview:
        ghost_item = ComponentFactory.create_item_from_dict(data, x, y)
        ghost_item.setOpacity(0.7)

        # Actual component:
        real_item = ComponentFactory.create_item_from_dict(data, x, y)
    """

    @staticmethod
    def create_item_from_dict(data: dict, x_mm: float, y_mm: float) -> Optional[BaseObj]:
        """
        Create an optical component item from library data.

        This is the ONLY place where component type routing happens.

        Args:
            data: Component data dict (from library/ComponentRecord)
            x_mm: X position in scene coordinates (mm)
            y_mm: Y position in scene coordinates (mm)

        Returns:
            ComponentItem (generic, with or without interfaces), or None if invalid
        """
        # Import here to avoid circular imports
        from .generic import ComponentItem

        # Check for background category first (preferred method)
        category = data.get("category", "").lower()
        if category == "background":
            # Create background/decorative item (ComponentItem with no interfaces)
            name = data.get("name", "Background")
            image_path_raw = data.get("image_path", "")
            image_path = to_absolute_path(image_path_raw) if image_path_raw else ""
            object_height_mm = float(data.get("object_height_mm", data.get("object_height", data.get("length_mm", 100.0))))
            angle_deg = float(data.get("angle_deg", 0.0))
            mm_per_pixel = float(data.get("mm_per_pixel", object_height_mm / 1000.0))

            params = ComponentParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                name=name,
                image_path=image_path,
                mm_per_pixel=mm_per_pixel,
                interfaces=[],  # Background has no optical interfaces
                category=category,
                notes=data.get("notes"),
            )
            return ComponentItem(params)

        # Extract interfaces (source of truth for optical elements)
        interfaces_data = data.get("interfaces", [])
        if not interfaces_data or len(interfaces_data) == 0:
            # No interfaces defined - treat as decorative/background item
            name = data.get("name", "Decorative")
            image_path_raw = data.get("image_path", "")
            image_path = to_absolute_path(image_path_raw) if image_path_raw else ""
            object_height_mm = float(data.get("object_height_mm", data.get("object_height", data.get("length_mm", 100.0))))
            angle_deg = float(data.get("angle_deg", 0.0))
            mm_per_pixel = float(data.get("mm_per_pixel", object_height_mm / 1000.0))

            params = ComponentParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                name=name,
                image_path=image_path,
                mm_per_pixel=mm_per_pixel,
                interfaces=[],  # No interfaces
                category=data.get("category"),
                notes=data.get("notes"),
            )
            return ComponentItem(params)

        # Convert interface data to InterfaceDefinition objects
        interfaces = []
        for iface_data in interfaces_data:
            if isinstance(iface_data, dict):
                iface_def = InterfaceDefinition.from_dict(iface_data)
            else:
                # Already an InterfaceDefinition
                iface_def = iface_data
            interfaces.append(iface_def)

        # Extract common parameters
        name = data.get("name", "Component")
        image_path_raw = data.get("image_path", "")
        # Convert package-relative paths to absolute filesystem paths
        image_path = to_absolute_path(image_path_raw) if image_path_raw else ""
        object_height_mm = float(data.get("object_height_mm", data.get("object_height", data.get("length_mm", 60.0))))

        # Determine angle (default to 0.0 = native orientation from Component Editor)
        if "angle_deg" in data:
            angle_deg = float(data["angle_deg"])
        else:
            angle_deg = 0.0

        # Extract reference line from first interface for sprite positioning
        reference_line_mm = None
        if interfaces and len(interfaces) > 0:
            first_iface = interfaces[0]
            reference_line_mm = (
                float(first_iface.x1_mm),
                float(first_iface.y1_mm),
                float(first_iface.x2_mm),
                float(first_iface.y2_mm),
            )

        # Use generic ComponentItem for all multi-interface components
        # Each interface behaves independently based on its element_type
        mm_per_pixel = float(data.get("mm_per_pixel", object_height_mm / 1000.0))

        params = ComponentParams(
            x_mm=x_mm,
            y_mm=y_mm,
            angle_deg=angle_deg,
            object_height_mm=object_height_mm,
            interfaces=interfaces,  # Keep as InterfaceDefinition objects
            image_path=image_path,
            mm_per_pixel=mm_per_pixel,
            name=name,
            category=data.get("category"),
            notes=data.get("notes"),
        )

        # Store reference line if present (proper field, not dynamic attribute)
        if reference_line_mm:
            params.reference_line_mm = reference_line_mm

        return ComponentItem(params)



