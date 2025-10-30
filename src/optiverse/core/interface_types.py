"""Interface type registry and metadata."""

from typing import Dict, List, Any, Tuple, Optional


# Interface type registry with metadata for UI generation
INTERFACE_TYPES: Dict[str, Dict[str, Any]] = {
    'lens': {
        'name': 'Lens',
        'description': 'Thin lens with specified focal length',
        'color': (0, 180, 180),
        'emoji': '🔵',
        'properties': ['efl_mm'],
        'property_labels': {
            'efl_mm': 'Effective Focal Length',
        },
        'property_units': {
            'efl_mm': 'mm',
        },
        'property_ranges': {
            'efl_mm': (-10000.0, 10000.0),
        },
        'property_defaults': {
            'efl_mm': 100.0,
        },
    },
    'mirror': {
        'name': 'Mirror',
        'description': 'Reflective surface',
        'color': (255, 140, 0),
        'emoji': '🟠',
        'properties': ['reflectivity'],
        'property_labels': {
            'reflectivity': 'Reflectivity',
        },
        'property_units': {
            'reflectivity': '%',
        },
        'property_ranges': {
            'reflectivity': (0.0, 100.0),
        },
        'property_defaults': {
            'reflectivity': 99.0,
        },
    },
    'beam_splitter': {
        'name': 'Beam Splitter',
        'description': 'Partially transmitting/reflecting coating',
        'color': (0, 150, 120),  # Green (purple if polarizing)
        'emoji': '🟢',
        'properties': ['split_T', 'split_R', 'is_polarizing', 'pbs_transmission_axis_deg'],
        'property_labels': {
            'split_T': 'Transmission',
            'split_R': 'Reflection',
            'is_polarizing': 'Polarizing (PBS)',
            'pbs_transmission_axis_deg': 'PBS Transmission Axis',
        },
        'property_units': {
            'split_T': '%',
            'split_R': '%',
            'pbs_transmission_axis_deg': '°',
        },
        'property_ranges': {
            'split_T': (0.0, 100.0),
            'split_R': (0.0, 100.0),
            'pbs_transmission_axis_deg': (-180.0, 180.0),
        },
        'property_defaults': {
            'split_T': 50.0,
            'split_R': 50.0,
            'is_polarizing': False,
            'pbs_transmission_axis_deg': 0.0,
        },
    },
    'dichroic': {
        'name': 'Dichroic',
        'description': 'Wavelength-selective filter',
        'color': (255, 0, 255),
        'emoji': '🟣',
        'properties': ['cutoff_wavelength_nm', 'transition_width_nm', 'pass_type'],
        'property_labels': {
            'cutoff_wavelength_nm': 'Cutoff Wavelength',
            'transition_width_nm': 'Transition Width',
            'pass_type': 'Pass Type',
        },
        'property_units': {
            'cutoff_wavelength_nm': 'nm',
            'transition_width_nm': 'nm',
        },
        'property_ranges': {
            'cutoff_wavelength_nm': (200.0, 2000.0),
            'transition_width_nm': (1.0, 200.0),
        },
        'property_defaults': {
            'cutoff_wavelength_nm': 550.0,
            'transition_width_nm': 50.0,
            'pass_type': 'longpass',
        },
    },
    'refractive_interface': {
        'name': 'Refractive Interface',
        'description': 'Boundary between two media',
        'color': (100, 100, 255),
        'emoji': '🔵',
        'properties': ['n1', 'n2', 'is_curved', 'radius_of_curvature_mm'],
        'property_labels': {
            'n1': 'Incident Index (n₁)',
            'n2': 'Transmitted Index (n₂)',
            'is_curved': 'Curved Surface',
            'radius_of_curvature_mm': 'Radius of Curvature',
        },
        'property_units': {
            'n1': '',
            'n2': '',
            'is_curved': '',
            'radius_of_curvature_mm': 'mm',
        },
        'property_ranges': {
            'n1': (1.0, 3.0),
            'n2': (1.0, 3.0),
            'radius_of_curvature_mm': (-10000.0, 10000.0),
        },
        'property_defaults': {
            'n1': 1.0,
            'n2': 1.5,
            'is_curved': False,
            'radius_of_curvature_mm': 0.0,
        },
    },
}


# Common refractive index presets
REFRACTIVE_INDEX_PRESETS = {
    'Vacuum': 1.0,
    'Air': 1.000293,
    'Water': 1.333,
    'Fused Silica': 1.458,
    'BK7 Glass': 1.517,
    'SF11 Glass': 1.785,
    'Sapphire': 1.77,
}


def get_type_info(element_type: str) -> Dict[str, Any]:
    """
    Get metadata for an interface type.
    
    Args:
        element_type: Type identifier (e.g., 'lens', 'mirror')
    
    Returns:
        Dictionary with type metadata, or empty dict if not found
    """
    return INTERFACE_TYPES.get(element_type, {})


def get_all_type_names() -> List[str]:
    """Get list of all available interface type names."""
    return list(INTERFACE_TYPES.keys())


def get_type_display_name(element_type: str) -> str:
    """Get human-readable name for an interface type."""
    return get_type_info(element_type).get('name', element_type)


def get_property_label(element_type: str, prop_name: str) -> str:
    """
    Get human-readable label for a property.
    
    Args:
        element_type: Type identifier
        prop_name: Property name
    
    Returns:
        Human-readable label, or property name if not found
    """
    type_info = get_type_info(element_type)
    return type_info.get('property_labels', {}).get(prop_name, prop_name)


def get_property_unit(element_type: str, prop_name: str) -> str:
    """
    Get unit for a property.
    
    Args:
        element_type: Type identifier
        prop_name: Property name
    
    Returns:
        Unit string (e.g., 'mm', '%', '°'), or empty string if none
    """
    type_info = get_type_info(element_type)
    return type_info.get('property_units', {}).get(prop_name, '')


def get_property_range(element_type: str, prop_name: str) -> Tuple[float, float]:
    """
    Get valid range for a property.
    
    Args:
        element_type: Type identifier
        prop_name: Property name
    
    Returns:
        Tuple of (min, max) values
    """
    type_info = get_type_info(element_type)
    return type_info.get('property_ranges', {}).get(prop_name, (-1e10, 1e10))


def get_property_default(element_type: str, prop_name: str) -> Any:
    """
    Get default value for a property.
    
    Args:
        element_type: Type identifier
        prop_name: Property name
    
    Returns:
        Default value, or None if not found
    """
    type_info = get_type_info(element_type)
    return type_info.get('property_defaults', {}).get(prop_name)


def get_type_color(element_type: str, is_polarizing: bool = False) -> Tuple[int, int, int]:
    """
    Get RGB color for an interface type.
    
    Args:
        element_type: Type identifier
        is_polarizing: If True and type is beam_splitter, return purple instead of green
    
    Returns:
        RGB tuple (0-255 range)
    """
    color = get_type_info(element_type).get('color', (150, 150, 150))
    
    # Special case: PBS is purple instead of green
    if element_type == 'beam_splitter' and is_polarizing:
        return (150, 0, 150)
    
    return color


def get_type_emoji(element_type: str) -> str:
    """Get emoji icon for an interface type."""
    return get_type_info(element_type).get('emoji', '⚪')


def get_type_properties(element_type: str) -> List[str]:
    """Get list of property names for an interface type."""
    return get_type_info(element_type).get('properties', [])


def validate_property_value(element_type: str, prop_name: str, value: Any) -> bool:
    """
    Validate if a property value is within valid range.
    
    Args:
        element_type: Type identifier
        prop_name: Property name
        value: Value to validate
    
    Returns:
        True if valid, False otherwise
    """
    if isinstance(value, (int, float)):
        min_val, max_val = get_property_range(element_type, prop_name)
        return min_val <= value <= max_val
    
    # For non-numeric values, accept anything
    return True

