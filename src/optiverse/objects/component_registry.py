"""
Component Registry - Standard component definitions.

This module provides centralized definitions for all standard optical components
that should be available in the component library by default.
"""
from pathlib import Path
from typing import Dict, List, Any, Tuple


def _get_image_path(filename: str) -> str:
    """Get full path to an image in the objects/images folder."""
    images_dir = Path(__file__).parent / "images"
    return str(images_dir / filename)


class ComponentRegistry:
    """
    Central registry for standard optical components.
    
    Provides default components that are auto-populated in the component library.
    All standard components include proper calibration and images.
    """
    
    @staticmethod
    def get_standard_lens() -> Dict[str, Any]:
        """
        Get standard 1-inch mounted lens definition.
        
        Returns:
            Dictionary with lens parameters including image and calibration
        """
        object_height_mm = 30.5  # Physical height of optical element
        x1_mm, y1_mm, x2_mm, y2_mm = 0.0, -15.25, 0.0, 15.25
        image_path = _get_image_path("lens_1_inch_mounted.png")
        
        return {
            "name": "Standard Lens (1\" mounted)",
            "kind": "lens",
            "type": "optical element",
            "object_height_mm": object_height_mm,
            "image_path": image_path,
            "interfaces": [
                {
                    "x1_mm": x1_mm,
                    "y1_mm": y1_mm,
                    "x2_mm": x2_mm,
                    "y2_mm": y2_mm,
                    "element_type": "lens",
                    "efl_mm": 100.0,
                }
            ],
            "angle_deg": 90,  # Vertical orientation by default
        }
    
    @staticmethod
    def get_standard_lens_2_inch() -> Dict[str, Any]:
        """
        Get standard 2-inch mounted lens definition.
        
        Returns:
            Dictionary with lens parameters including image and calibration
        """
        return {
            "name": "Standard Lens (2\" mounted)",
            "kind": "lens",
            "type": "optical element",
            "object_height_mm": 55.9,  # Physical height of optical element (2 inch mounted)
            "image_path": _get_image_path("lens_1_inch_mounted.png"),
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -27.95,
                    "x2_mm": 0.0,
                    "y2_mm": 27.95,
                    "element_type": "lens",
                    "efl_mm": 100.0,
                }
            ],
            "angle_deg": 90,  # Vertical orientation by default
        }
    
    @staticmethod
    def get_standard_mirror() -> Dict[str, Any]:
        """
        Get standard 1-inch mirror definition.
        
        Returns:
            Dictionary with mirror parameters including image and calibration
        """
        object_height_mm = 49.4  # Physical height of optical element
        x1_mm, y1_mm, x2_mm, y2_mm = 0.0, -24.7, 0.0, 24.7
        image_path = _get_image_path("standard_mirror_1_inch.png")
        
        return {
            "name": "Standard Mirror (1\")",
            "kind": "mirror",
            "type": "optical element",
            "object_height_mm": object_height_mm,
            "image_path": image_path,
            "interfaces": [
                {
                    "x1_mm": x1_mm,
                    "y1_mm": y1_mm,
                    "x2_mm": x2_mm,
                    "y2_mm": y2_mm,
                    "element_type": "mirror",
                }
            ],
            "angle_deg": 0.0,  # Horizontal orientation by default
        }
    
    @staticmethod
    def get_standard_mirror_2_inch() -> Dict[str, Any]:
        """
        Get standard 2-inch mirror definition.
        
        Returns:
            Dictionary with mirror parameters including image and calibration
        """
        return {
            "name": "Standard Mirror (2\")",
            "kind": "mirror",
            "type": "optical element",
            "object_height_mm": 68.6,  # Physical height of optical element (2 inch with mount)
            "image_path": _get_image_path("standard_mirror_1_inch.png"),
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -34.3,
                    "x2_mm": 0.0,
                    "y2_mm": 34.3,
                    "element_type": "mirror",
                }
            ],
            "angle_deg": 0.0,  # Horizontal orientation by default
        }
    
    @staticmethod
    def get_standard_beamsplitter() -> Dict[str, Any]:
        """
        Get standard 50/50 1-inch beamsplitter definition.
        
        Returns:
            Dictionary with beamsplitter parameters including image and calibration
        """
        object_height_mm = 25.4  # Physical height of optical element
        x1_mm, y1_mm, x2_mm, y2_mm = -12.7, -12.7, 12.7, 12.7
        image_path = _get_image_path("beamsplitter_50_50_1_inch.png")
        
        return {
            "name": "Standard Beamsplitter (50/50 1\")",
            "kind": "beamsplitter",
            "type": "optical element",
            "object_height_mm": object_height_mm,
            "image_path": image_path,
            "interfaces": [
                {
                    "x1_mm": x1_mm,
                    "y1_mm": y1_mm,
                    "x2_mm": x2_mm,
                    "y2_mm": y2_mm,
                    "element_type": "beam_splitter",
                    "split_T": 50.0,
                    "split_R": 50.0,
                }
            ],
            "angle_deg": 45,  # 45° orientation for proper beam splitting
        }
    
    @staticmethod
    def get_standard_pbs() -> Dict[str, Any]:
        """
        Get standard 2-inch PBS (Polarizing Beam Splitter) definition.
        
        Returns:
            Dictionary with PBS parameters including image and calibration
        """
        return {
            "name": "PBS (2\" Polarizing)",
            "kind": "beamsplitter",
            "type": "optical element",
            "object_height_mm": 50.8,  # Physical height of optical element (2 inch = 50.8 mm)
            "image_path": _get_image_path("pbs_2_inch.png"),
            "interfaces": [
                {
                    "x1_mm": -25.4,
                    "y1_mm": -25.4,
                    "x2_mm": 25.4,
                    "y2_mm": 25.4,
                    "element_type": "beam_splitter",
                    "split_T": 0.0,  # s-polarization reflects, p-polarization transmits
                    "split_R": 0.0,
                    "is_polarizing": True,  # This is a PBS
                    "pbs_transmission_axis_deg": 0.0,  # Horizontal transmission axis in lab frame (ABSOLUTE angle)
                }
            ],
            "angle_deg": 45,  # 45° orientation for proper beam splitting
        }
    
    @staticmethod
    def get_standard_objective() -> Dict[str, Any]:
        """
        Get standard microscope objective definition.
        
        Returns:
            Dictionary with objective parameters including image and calibration
        """
        return {
            "name": "Microscope Objective",
            "kind": "lens",
            "type": "optical element",
            "object_height_mm": 40.0,  # Physical height of optical element
            "image_path": _get_image_path("objective.png"),
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -20.0,
                    "x2_mm": 0.0,
                    "y2_mm": 20.0,
                    "element_type": "lens",
                    "efl_mm": 4.5,  # Typical short focal length for microscope objective
                }
            ],
            "angle_deg": 90,  # Vertical orientation by default
        }
    
    @staticmethod
    def get_standard_dichroic_550nm() -> Dict[str, Any]:
        """
        Get standard dichroic mirror (550nm cutoff) definition.
        
        Returns:
            Dictionary with dichroic parameters including image and calibration
        """
        return {
            "name": "Dichroic Mirror (550nm cutoff)",
            "kind": "dichroic",
            "type": "optical element",
            "object_height_mm": 25.4,  # Physical height of optical element (1 inch)
            "image_path": _get_image_path("beamsplitter_50_50_1_inch.png"),
            "interfaces": [
                {
                    "x1_mm": -12.7,
                    "y1_mm": -12.7,
                    "x2_mm": 12.7,
                    "y2_mm": 12.7,
                    "element_type": "dichroic",
                    "cutoff_wavelength_nm": 550.0,
                    "transition_width_nm": 50.0,
                }
            ],
            "angle_deg": 45,  # 45° orientation for proper beam combining/splitting
        }
    
    @staticmethod
    def get_standard_source() -> Dict[str, Any]:
        """
        Get standard optical source definition.
        
        Returns:
            Dictionary with source parameters
        """
        return {
            "name": "Standard Source",
            "kind": "source",
            "type": "optical element",
            "n_rays": 5,
            "spread_deg": 5.0,
            "size_mm": 10.0,
            "ray_length_mm": 500.0,
            "color_hex": "#FF0000",  # Red
            "wavelength_nm": 0.0,  # 0 = use color_hex
            "x_mm": 0.0,
            "y_mm": 0.0,
            "angle_deg": 0.0,
            "polarization_type": "horizontal",
            "polarization_angle_deg": 0.0,
        }
    
    @staticmethod
    def get_quarter_waveplate() -> Dict[str, Any]:
        """
        Get quarter waveplate (QWP) definition.
        
        Quarter waveplates introduce a 90° phase shift between orthogonal polarizations.
        Commonly used to convert linear → circular polarization (at 45° to fast axis).
        
        Returns:
            Dictionary with waveplate parameters including image and calibration
        """
        return {
            "name": "Quarter Waveplate (QWP)",
            "kind": "waveplate",
            "type": "optical element",
            "object_height_mm": 30.5,  # Same as 1" lens
            "image_path": _get_image_path("lens_1_inch_mounted.png"),
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -15.25,
                    "x2_mm": 0.0,
                    "y2_mm": 15.25,
                    "element_type": "waveplate",
                    "phase_shift_deg": 90.0,  # π/2 phase shift
                    "fast_axis_deg": 0.0,  # Horizontal fast axis by default
                }
            ],
            "angle_deg": 90,  # Vertical orientation by default
        }
    
    @staticmethod
    def get_half_waveplate() -> Dict[str, Any]:
        """
        Get half waveplate (HWP) definition.
        
        Half waveplates introduce a 180° phase shift between orthogonal polarizations.
        Commonly used to rotate linear polarization or switch circular handedness.
        
        Returns:
            Dictionary with waveplate parameters including image and calibration
        """
        return {
            "name": "Half Waveplate (HWP)",
            "kind": "waveplate",
            "type": "optical element",
            "object_height_mm": 30.5,  # Same as 1" lens
            "image_path": _get_image_path("lens_1_inch_mounted.png"),
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -15.25,
                    "x2_mm": 0.0,
                    "y2_mm": 15.25,
                    "element_type": "waveplate",
                    "phase_shift_deg": 180.0,  # π phase shift
                    "fast_axis_deg": 0.0,  # Horizontal fast axis by default
                }
            ],
            "angle_deg": 90,  # Vertical orientation by default
        }
    
    @staticmethod
    def get_slm() -> Dict[str, Any]:
        """
        Get Spatial Light Modulator (SLM) definition.
        
        SLMs act as programmable mirrors and can modulate light spatially.
        
        Returns:
            Dictionary with SLM parameters including image and calibration
        """
        return {
            "name": "Spatial Light Modulator",
            "kind": "slm",
            "type": "optical element",
            "object_height_mm": 100.0,  # Typical large SLM size
            "image_path": _get_image_path("slm.png"),
            "interfaces": [
                {
                    "x1_mm": -50.0,
                    "y1_mm": 0.0,
                    "x2_mm": 50.0,
                    "y2_mm": 0.0,
                    "element_type": "mirror",
                }
            ],
            "angle_deg": 0.0,  # Horizontal orientation by default
        }
    
    @staticmethod
    def get_laser_table() -> Dict[str, Any]:
        """
        Get laser table definition.
        
        Laser tables are background elements with no optical interface.
        Used for setting up optical experiments.
        
        Returns:
            Dictionary with laser table parameters
        """
        return {
            "name": "Laser Table",
            "kind": "background",
            "type": "background",
            "object_height_mm": 1500.0,  # 1.5m height
            "image_path": _get_image_path("lasertable_1.5m_3m.png"),
            "angle_deg": 0.0,  # Horizontal orientation by default
        }
    
    @staticmethod
    def get_standard_components() -> List[Dict[str, Any]]:
        """
        Get all standard components as a list.
        
        Returns:
            List of component dictionaries, one for each category
        """
        return [
            ComponentRegistry.get_standard_lens(),
            ComponentRegistry.get_standard_lens_2_inch(),
            ComponentRegistry.get_standard_mirror(),
            ComponentRegistry.get_standard_mirror_2_inch(),
            ComponentRegistry.get_standard_beamsplitter(),
            ComponentRegistry.get_standard_pbs(),
            ComponentRegistry.get_standard_dichroic_550nm(),
            ComponentRegistry.get_standard_objective(),
            ComponentRegistry.get_quarter_waveplate(),
            ComponentRegistry.get_half_waveplate(),
            ComponentRegistry.get_standard_source(),
            ComponentRegistry.get_slm(),
            ComponentRegistry.get_laser_table(),
        ]
    
    @staticmethod
    def get_components_by_category() -> Dict[str, List[Dict[str, Any]]]:
        """
        Get standard components organized by category.
        
        Returns:
            Dictionary mapping category names to lists of components
        """
        return {
            "Lenses": [
                ComponentRegistry.get_standard_lens(),
                ComponentRegistry.get_standard_lens_2_inch(),
            ],
            "Objectives": [ComponentRegistry.get_standard_objective()],
            "Mirrors": [
                ComponentRegistry.get_standard_mirror(),
                ComponentRegistry.get_standard_mirror_2_inch(),
            ],
            "Beamsplitters": [
                ComponentRegistry.get_standard_beamsplitter(),
                ComponentRegistry.get_standard_pbs(),
            ],
            "Dichroics": [
                ComponentRegistry.get_standard_dichroic_550nm(),
            ],
            "Waveplates": [
                ComponentRegistry.get_quarter_waveplate(),
                ComponentRegistry.get_half_waveplate(),
            ],
            "Sources": [ComponentRegistry.get_standard_source()],
            "Background": [ComponentRegistry.get_laser_table()],
            "Misc": [ComponentRegistry.get_slm()],
        }
    
    @staticmethod
    def get_component_by_kind(kind: str) -> Dict[str, Any]:
        """
        Get the standard component for a specific kind.
        
        Args:
            kind: Component kind ('lens', 'mirror', 'beamsplitter', 'source')
        
        Returns:
            Component dictionary
        
        Raises:
            ValueError: If kind is not recognized
        """
        kind_map = {
            "lens": ComponentRegistry.get_standard_lens,
            "mirror": ComponentRegistry.get_standard_mirror,
            "beamsplitter": ComponentRegistry.get_standard_beamsplitter,
            "source": ComponentRegistry.get_standard_source,
        }
        
        if kind not in kind_map:
            raise ValueError(f"Unknown component kind: {kind}")
        
        return kind_map[kind]()
    
    @staticmethod
    def get_category_for_element_type(element_type: str, name: str = "") -> str:
        """
        Get the category name for a component based on its interface element_type.
        
        Args:
            element_type: Element type from interface ('lens', 'mirror', 'beam_splitter', 'dichroic', 'waveplate', etc.)
            name: Optional component name to distinguish special cases (e.g., objectives)
        
        Returns:
            Category name (e.g., 'Lenses', 'Mirrors', 'Dichroics', 'Background', 'Misc')
        """
        # Special case: Objectives are lenses but in their own category
        if element_type == "lens" and "objective" in name.lower():
            return "Objectives"
        
        element_type_to_category = {
            "lens": "Lenses",
            "mirror": "Mirrors",
            "beam_splitter": "Beamsplitters",
            "beamsplitter": "Beamsplitters",  # Legacy support
            "dichroic": "Dichroics",
            "waveplate": "Waveplates",
            "source": "Sources",
            "background": "Background",
            "slm": "Misc",
            "refractive_interface": "Other",  # Generic refractive interfaces
        }
        return element_type_to_category.get(element_type, "Other")

