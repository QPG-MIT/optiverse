"""Migration utilities for converting legacy components to v2 interface-based format."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import math

from .models import ComponentRecord
from .interface_definition import InterfaceDefinition


def migrate_component_to_v2(component: ComponentRecord) -> ComponentRecord:
    """
    Migrate a legacy (v1) component to v2 interface-based format.
    
    Args:
        component: ComponentRecord in legacy format
    
    Returns:
        ComponentRecord with interfaces_v2 populated
    
    Notes:
        - If component already has interfaces_v2, returns unchanged
        - Converts legacy type-specific properties to InterfaceDefinition objects
        - Coordinates converted from normalized 1000px space to mm
    """
    # Already v2 format
    if component.is_v2_format():
        return component
    
    # Dispatch to type-specific migration
    if component.kind == 'refractive_object':
        return _migrate_refractive_object(component)
    elif component.kind in ('lens', 'mirror', 'beamsplitter', 'dichroic'):
        return _migrate_simple_component(component)
    else:
        # Unknown type - return as-is
        return component


def _migrate_simple_component(component: ComponentRecord) -> ComponentRecord:
    """
    Migrate simple component (lens, mirror, beamsplitter, dichroic) to v2.
    
    Creates a single InterfaceDefinition from the component properties.
    """
    kind = component.kind
    
    # Convert line_px coordinates to mm
    # line_px is in normalized 1000px space
    # New coordinate system: Y goes from 0 (top) to object_height (bottom)
    # mm_per_px = object_height / 1000 (normalized image height)
    x1_norm, y1_norm, x2_norm, y2_norm = component.line_px
    
    object_height = component.object_height_mm
    if object_height > 0:
        # Simple conversion: normalized 1000px space to mm
        # Y: 0px → 0mm, 1000px → object_height mm
        mm_per_px = object_height / 1000.0
        
        x1_mm = x1_norm * mm_per_px
        y1_mm = y1_norm * mm_per_px
        x2_mm = x2_norm * mm_per_px
        y2_mm = y2_norm * mm_per_px
    else:
        # No valid object height - use defaults centered in image
        center_mm = 12.5  # Typical center for 25mm object height
        x1_mm, y1_mm = center_mm - 5.0, center_mm
        x2_mm, y2_mm = center_mm + 5.0, center_mm
    
    # Create InterfaceDefinition based on component type
    if kind == 'lens':
        interface = InterfaceDefinition(
            element_type='lens',
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm,
            efl_mm=component.efl_mm,
            name=f"{component.name} Interface" if component.name else ""
        )
    elif kind == 'mirror':
        interface = InterfaceDefinition(
            element_type='mirror',
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm,
            name=f"{component.name} Interface" if component.name else ""
        )
    elif kind == 'beamsplitter':
        t, r = component.split_TR
        interface = InterfaceDefinition(
            element_type='beam_splitter',
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm,
            split_T=t,
            split_R=r,
            name=f"{component.name} Interface" if component.name else ""
        )
    elif kind == 'dichroic':
        interface = InterfaceDefinition(
            element_type='dichroic',
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm,
            cutoff_wavelength_nm=component.cutoff_wavelength_nm,
            transition_width_nm=component.transition_width_nm,
            pass_type=component.pass_type,
            name=f"{component.name} Interface" if component.name else ""
        )
    else:
        # Fallback to refractive interface
        interface = InterfaceDefinition(
            element_type='refractive_interface',
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm
        )
    
    # Create new component with v2 interfaces
    component.interfaces_v2 = [interface]
    component.kind = component._compute_kind()
    
    return component


def _migrate_refractive_object(component: ComponentRecord) -> ComponentRecord:
    """
    Migrate refractive_object with legacy interfaces list to v2.
    
    Converts old dict-based interfaces to InterfaceDefinition objects.
    """
    legacy_interfaces = component.interfaces
    if not legacy_interfaces:
        # No interfaces - create empty v2
        component.interfaces_v2 = []
        component.kind = "empty"
        return component
    
    # Compute mm_per_px from first interface if possible
    # Legacy interfaces may have x1_px, y1_px, etc. in actual pixel coordinates
    # or x1_mm, y1_mm, etc. already in mm
    first_iface = legacy_interfaces[0]
    
    # Check if legacy interface has mm coordinates
    has_mm_coords = all(k in first_iface for k in ('x1_mm', 'y1_mm', 'x2_mm', 'y2_mm'))
    has_px_coords = all(k in first_iface for k in ('x1_px', 'y1_px', 'x2_px', 'y2_px'))
    
    mm_per_px = 1.0  # Default scale
    if has_px_coords and not has_mm_coords:
        # Need to convert from pixels to mm
        # New coordinate system: image height → object_height
        # For legacy pixel coordinates, we need to know the image height
        # Since we don't have it, we'll assume normalized 1000px height
        if component.object_height_mm > 0:
            mm_per_px = component.object_height_mm / 1000.0
        else:
            mm_per_px = 0.025  # Fallback: 25mm / 1000px
    
    # Convert each legacy interface
    interfaces_v2 = []
    for old_iface in legacy_interfaces:
        # Get coordinates
        if has_mm_coords:
            x1_mm = old_iface.get('x1_mm', 0.0)
            y1_mm = old_iface.get('y1_mm', 0.0)
            x2_mm = old_iface.get('x2_mm', 10.0)
            y2_mm = old_iface.get('y2_mm', 10.0)
        elif has_px_coords:
            # Convert from pixels
            x1_px = old_iface.get('x1_px', 0)
            y1_px = old_iface.get('y1_px', 0)
            x2_px = old_iface.get('x2_px', 100)
            y2_px = old_iface.get('y2_px', 100)
            
            x1_mm = x1_px * mm_per_px
            y1_mm = y1_px * mm_per_px
            x2_mm = x2_px * mm_per_px
            y2_mm = y2_px * mm_per_px
        else:
            # No coordinates - use defaults
            x1_mm, y1_mm, x2_mm, y2_mm = 0.0, 0.0, 10.0, 10.0
        
        # Determine interface type
        is_bs = old_iface.get('is_beam_splitter', False)
        element_type = 'beam_splitter' if is_bs else 'refractive_interface'
        
        # Create InterfaceDefinition
        interface = InterfaceDefinition(
            element_type=element_type,
            x1_mm=x1_mm,
            y1_mm=y1_mm,
            x2_mm=x2_mm,
            y2_mm=y2_mm,
            n1=old_iface.get('n1', 1.0),
            n2=old_iface.get('n2', 1.5),
            split_T=old_iface.get('split_T', 50.0),
            split_R=old_iface.get('split_R', 50.0),
            is_polarizing=old_iface.get('is_polarizing', False),
            pbs_transmission_axis_deg=old_iface.get('pbs_transmission_axis_deg', 0.0),
        )
        
        interfaces_v2.append(interface)
    
    # Update component
    component.interfaces_v2 = interfaces_v2
    component.kind = component._compute_kind()
    
    return component


def convert_v2_to_legacy(component: ComponentRecord) -> ComponentRecord:
    """
    Convert v2 interface-based component back to legacy format.
    
    This is mainly for backward compatibility and testing.
    May lose information for multi-element components.
    
    Args:
        component: ComponentRecord in v2 format
    
    Returns:
        ComponentRecord in legacy format
    
    Notes:
        - Multi-element components converted to refractive_object
        - Single-interface components converted to their specific type
    """
    if not component.is_v2_format():
        return component
    
    num_interfaces = len(component.interfaces_v2)
    
    if num_interfaces == 0:
        # Empty - convert to default lens
        component.kind = 'lens'
        component.line_px = (0.0, 0.0, 100.0, 100.0)
        return component
    
    elif num_interfaces == 1:
        # Single interface - convert to simple component
        interface = component.interfaces_v2[0]
        
        # Convert mm coordinates back to normalized 1000px space
        # New coordinate system: Y from 0 to object_height
        # mm_per_px = object_height / 1000
        if component.object_height_mm > 0:
            mm_per_px = component.object_height_mm / 1000.0
            
            x1_norm = interface.x1_mm / mm_per_px
            y1_norm = interface.y1_mm / mm_per_px
            x2_norm = interface.x2_mm / mm_per_px
            y2_norm = interface.y2_mm / mm_per_px
        else:
            x1_norm, y1_norm, x2_norm, y2_norm = 450.0, 500.0, 550.0, 500.0
        
        component.line_px = (x1_norm, y1_norm, x2_norm, y2_norm)
        component.kind = interface.element_type
        
        # Copy type-specific properties
        if interface.element_type == 'lens':
            component.efl_mm = interface.efl_mm
        elif interface.element_type == 'beam_splitter':
            component.split_TR = (interface.split_T, interface.split_R)
        elif interface.element_type == 'dichroic':
            component.cutoff_wavelength_nm = interface.cutoff_wavelength_nm
            component.transition_width_nm = interface.transition_width_nm
            component.pass_type = interface.pass_type
        
        return component
    
    else:
        # Multiple interfaces - convert to refractive_object
        component.kind = 'refractive_object'
        
        # Convert interfaces to legacy dict format
        legacy_interfaces = []
        for interface in component.interfaces_v2:
            legacy_iface = {
                'x1_mm': interface.x1_mm,
                'y1_mm': interface.y1_mm,
                'x2_mm': interface.x2_mm,
                'y2_mm': interface.y2_mm,
                'n1': interface.n1,
                'n2': interface.n2,
                'is_beam_splitter': (interface.element_type == 'beam_splitter'),
                'split_T': interface.split_T,
                'split_R': interface.split_R,
                'is_polarizing': interface.is_polarizing,
                'pbs_transmission_axis_deg': interface.pbs_transmission_axis_deg,
            }
            legacy_interfaces.append(legacy_iface)
        
        component.interfaces = legacy_interfaces
        
        # Set a representative line_px from first interface
        if component.interfaces_v2:
            first = component.interfaces_v2[0]
            mm_per_px = component.object_height_mm / 1000.0 if component.object_height_mm > 0 else 1.0
            
            x1_norm = first.x1_mm / mm_per_px
            y1_norm = first.y1_mm / mm_per_px
            x2_norm = first.x2_mm / mm_per_px
            y2_norm = first.y2_mm / mm_per_px
            
            component.line_px = (x1_norm, y1_norm, x2_norm, y2_norm)
        
        return component

