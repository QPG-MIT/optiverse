"""
ComponentFactory - Unified component creation system.

This module provides a single source of truth for creating optical components
from library data. Used by both ghost preview and actual component creation
to ensure perfect consistency.

Key principle: "What You See Is What You Drop"
"""
from __future__ import annotations

from typing import Optional, Dict, Any

from ..core.models import (
    LensParams,
    MirrorParams,
    BeamsplitterParams,
    WaveplateParams,
    DichroicParams,
    SLMParams,
    RefractiveObjectParams,
    RefractiveInterface,
    BlockParams,
)
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
            Appropriate Item subclass (LensItem, MirrorItem, etc.) or None if invalid
        """
        # Import here to avoid circular imports
        from .lenses import LensItem
        from .mirrors import MirrorItem
        from .beamsplitters import BeamsplitterItem
        from .waveplates import WaveplateItem
        from .dichroics import DichroicItem
        from .misc import SLMItem
        from .refractive import RefractiveObjectItem
        from .blocks.block_item import BlockItem
        
        # Extract interfaces (source of truth)
        interfaces_data = data.get("interfaces", [])
        if not interfaces_data or len(interfaces_data) == 0:
            # No interfaces defined - invalid component
            return None
        
        # Convert interface data to InterfaceDefinition objects
        interfaces = []
        for iface_data in interfaces_data:
            if isinstance(iface_data, dict):
                iface_def = InterfaceDefinition.from_dict(iface_data)
            else:
                # Already an InterfaceDefinition
                iface_def = iface_data
            interfaces.append(iface_def)
        
        # Get first interface type (determines component category)
        first_interface = interfaces[0]
        element_type = first_interface.element_type
        
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
        
        # Determine if we should use RefractiveObjectItem
        # (for mixed interface types or all refractive_interface)
        all_same_type = all(iface.element_type == element_type for iface in interfaces)
        all_refractive = all(iface.element_type == "refractive_interface" for iface in interfaces)
        use_refractive_item = all_refractive or (len(interfaces) > 1 and not all_same_type)
        
        # Create the appropriate item type using a dispatch table
        if use_refractive_item:
            ref_interfaces = []
            for iface_def in interfaces:
                ref_iface = RefractiveInterface(
                    x1_mm=iface_def.x1_mm,
                    y1_mm=iface_def.y1_mm,
                    x2_mm=iface_def.x2_mm,
                    y2_mm=iface_def.y2_mm,
                    n1=iface_def.n1,
                    n2=iface_def.n2,
                    is_curved=iface_def.is_curved,
                    radius_of_curvature_mm=iface_def.radius_of_curvature_mm,
                    is_beam_splitter=(iface_def.element_type == "beam_splitter"),
                    split_T=iface_def.split_T,
                    split_R=iface_def.split_R,
                    is_polarizing=iface_def.is_polarizing,
                    pbs_transmission_axis_deg=iface_def.pbs_transmission_axis_deg,
                )
                ref_interfaces.append(ref_iface)

            mm_per_pixel = float(data.get("mm_per_pixel", object_height_mm / 1000.0))

            params = RefractiveObjectParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                interfaces=ref_interfaces,
                image_path=image_path,
                mm_per_pixel=mm_per_pixel,
                name=name,
            )
            return RefractiveObjectItem(params)

        def build_lens():
            efl_mm = float(getattr(first_interface, 'efl_mm', 100.0))
            params = LensParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                efl_mm=efl_mm,
                object_height_mm=object_height_mm,
                image_path=image_path,
                name=name,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return LensItem(params)

        def build_bs():
            split_T = float(getattr(first_interface, 'split_T', 50.0))
            split_R = float(getattr(first_interface, 'split_R', 50.0))
            is_polarizing = bool(getattr(first_interface, 'is_polarizing', False))
            pbs_axis = float(getattr(first_interface, 'pbs_transmission_axis_deg', 0.0))
            params = BeamsplitterParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                split_T=split_T,
                split_R=split_R,
                image_path=image_path,
                name=name,
                is_polarizing=is_polarizing,
                pbs_transmission_axis_deg=pbs_axis,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return BeamsplitterItem(params)

        def build_waveplate():
            phase_shift_deg = float(getattr(first_interface, 'phase_shift_deg', 90.0))
            fast_axis_deg = float(getattr(first_interface, 'fast_axis_deg', 0.0))
            params = WaveplateParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                phase_shift_deg=phase_shift_deg,
                fast_axis_deg=fast_axis_deg,
                image_path=image_path,
                name=name,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return WaveplateItem(params)

        def build_dichroic():
            cutoff_wavelength_nm = float(getattr(first_interface, 'cutoff_wavelength_nm', 550.0))
            transition_width_nm = float(getattr(first_interface, 'transition_width_nm', 50.0))
            pass_type = str(getattr(first_interface, 'pass_type', "longpass"))
            params = DichroicParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                cutoff_wavelength_nm=cutoff_wavelength_nm,
                transition_width_nm=transition_width_nm,
                pass_type=pass_type,
                image_path=image_path,
                name=name,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return DichroicItem(params)

        def build_slm():
            params = SLMParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                image_path=image_path,
                name=name,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return SLMItem(params)

        def build_mirror():
            params = MirrorParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                image_path=image_path,
                name=name,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return MirrorItem(params)

        def build_block():
            params = BlockParams(
                x_mm=x_mm,
                y_mm=y_mm,
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                image_path=image_path,
                name=name,
                interfaces=interfaces,
            )
            if reference_line_mm:
                params._reference_line_mm = reference_line_mm  # type: ignore
            return BlockItem(params)

        dispatch = {
            "lens": build_lens,
            "beam_splitter": build_bs,
            "beamsplitter": build_bs,
            "waveplate": build_waveplate,
            "dichroic": build_dichroic,
            "slm": build_slm,
            "mirror": build_mirror,
            "beam_block": build_block,
        }

        builder = dispatch.get(element_type, build_mirror)
        return builder()

