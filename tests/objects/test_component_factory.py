"""
Tests for ComponentFactory - unified component creation.

The ComponentFactory is the single source of truth for creating optical
components from library data. It's used by both ghost preview and actual
component creation to ensure consistency.
"""
import pytest
from optiverse.objects.component_factory import ComponentFactory
from optiverse.objects import (
    LensItem,
    MirrorItem,
    BeamsplitterItem,
    WaveplateItem,
    DichroicItem,
    SLMItem,
    RefractiveObjectItem,
)


class TestComponentFactoryLens:
    """Tests for creating LensItem from factory."""
    
    def test_create_lens_basic(self):
        """Factory creates LensItem from lens interface data."""
        data = {
            "name": "Test Lens",
            "image_path": "",
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "interfaces": [{
                "element_type": "lens",
                "name": "Front Surface",
                "x1_mm": -25.0,
                "y1_mm": 0.0,
                "x2_mm": 25.0,
                "y2_mm": 0.0,
                "n1": 1.0,
                "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 100.0, 50.0)
        
        assert isinstance(item, LensItem)
        assert item.params.x_mm == 100.0
        assert item.params.y_mm == 50.0
        assert item.params.angle_deg == 90.0
        assert item.params.name == "Test Lens"
        assert item.params.object_height_mm == 50.0
        assert len(item.params.interfaces) == 1
    
    def test_create_lens_preserves_all_interfaces(self):
        """Factory preserves all interfaces from data."""
        data = {
            "name": "Doublet",
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "interfaces": [
                {
                    "element_type": "lens",
                    "name": "Surface 1",
                    "x1_mm": -25.0, "y1_mm": 0.0,
                    "x2_mm": 25.0, "y2_mm": 0.0,
                    "n1": 1.0, "n2": 1.5,
                    "efl_mm": 100.0,
                    "is_curved": True,
                    "radius_of_curvature_mm": 50.0,
                },
                {
                    "element_type": "lens",
                    "name": "Surface 2",
                    "x1_mm": -25.0, "y1_mm": 5.0,
                    "x2_mm": 25.0, "y2_mm": 5.0,
                    "n1": 1.5, "n2": 1.0,
                    "efl_mm": 100.0,
                    "is_curved": True,
                    "radius_of_curvature_mm": -50.0,
                },
            ]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, LensItem)
        assert len(item.params.interfaces) == 2
        assert item.params.interfaces[0].name == "Surface 1"
        assert item.params.interfaces[1].name == "Surface 2"
    
    def test_create_lens_default_angle(self):
        """Factory uses default angle for lens when not specified."""
        data = {
            "name": "Test Lens",
            "object_height_mm": 50.0,
            # No angle_deg specified
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, LensItem)
        # Default angle for lens should be 90° (vertical)
        assert item.params.angle_deg == 90.0


class TestComponentFactoryMirror:
    """Tests for creating MirrorItem from factory."""
    
    def test_create_mirror_basic(self):
        """Factory creates MirrorItem from mirror interface data."""
        data = {
            "name": "Test Mirror",
            "object_height_mm": 80.0,
            "angle_deg": 45.0,
            "interfaces": [{
                "element_type": "mirror",
                "name": "Reflective Surface",
                "x1_mm": -40.0, "y1_mm": 0.0,
                "x2_mm": 40.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 200.0, 100.0)
        
        assert isinstance(item, MirrorItem)
        assert item.params.x_mm == 200.0
        assert item.params.y_mm == 100.0
        assert item.params.angle_deg == 45.0
        assert len(item.params.interfaces) == 1


class TestComponentFactoryBeamsplitter:
    """Tests for creating BeamsplitterItem from factory."""
    
    def test_create_beamsplitter_basic(self):
        """Factory creates BeamsplitterItem from beamsplitter interface."""
        data = {
            "name": "50:50 BS",
            "object_height_mm": 60.0,
            "angle_deg": 45.0,
            "interfaces": [{
                "element_type": "beam_splitter",
                "name": "BS Surface",
                "x1_mm": -30.0, "y1_mm": 0.0,
                "x2_mm": 30.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "split_T": 50.0,
                "split_R": 50.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
                "is_polarizing": False,
                "pbs_transmission_axis_deg": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, BeamsplitterItem)
        assert item.params.split_T == 50.0
        assert item.params.split_R == 50.0
        assert item.params.is_polarizing is False
    
    def test_create_polarizing_beamsplitter(self):
        """Factory creates polarizing beamsplitter."""
        data = {
            "name": "PBS",
            "object_height_mm": 60.0,
            "angle_deg": 45.0,
            "interfaces": [{
                "element_type": "beam_splitter",
                "name": "PBS Surface",
                "x1_mm": -30.0, "y1_mm": 0.0,
                "x2_mm": 30.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "split_T": 100.0,
                "split_R": 0.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
                "is_polarizing": True,
                "pbs_transmission_axis_deg": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, BeamsplitterItem)
        assert item.params.is_polarizing is True
        assert item.params.pbs_transmission_axis_deg == 0.0


class TestComponentFactoryWaveplate:
    """Tests for creating WaveplateItem from factory."""
    
    def test_create_waveplate_basic(self):
        """Factory creates WaveplateItem from waveplate interface."""
        data = {
            "name": "QWP",
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "interfaces": [{
                "element_type": "waveplate",
                "name": "QWP Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "phase_shift_deg": 90.0,
                "fast_axis_deg": 0.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, WaveplateItem)
        assert item.params.phase_shift_deg == 90.0
        assert item.params.fast_axis_deg == 0.0


class TestComponentFactoryDichroic:
    """Tests for creating DichroicItem from factory."""
    
    def test_create_dichroic_basic(self):
        """Factory creates DichroicItem from dichroic interface."""
        data = {
            "name": "Dichroic 550nm",
            "object_height_mm": 60.0,
            "angle_deg": 45.0,
            "interfaces": [{
                "element_type": "dichroic",
                "name": "Dichroic Surface",
                "x1_mm": -30.0, "y1_mm": 0.0,
                "x2_mm": 30.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "cutoff_wavelength_nm": 550.0,
                "transition_width_nm": 50.0,
                "pass_type": "longpass",
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, DichroicItem)
        assert item.params.cutoff_wavelength_nm == 550.0
        assert item.params.transition_width_nm == 50.0
        assert item.params.pass_type == "longpass"


class TestComponentFactorySLM:
    """Tests for creating SLMItem from factory."""
    
    def test_create_slm_basic(self):
        """Factory creates SLMItem from SLM interface."""
        data = {
            "name": "SLM",
            "object_height_mm": 100.0,
            "angle_deg": 90.0,
            "interfaces": [{
                "element_type": "slm",
                "name": "SLM Surface",
                "x1_mm": -50.0, "y1_mm": 0.0,
                "x2_mm": 50.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        assert isinstance(item, SLMItem)


class TestComponentFactoryRefractiveObject:
    """Tests for creating RefractiveObjectItem from factory."""
    
    def test_create_refractive_object_mixed_interfaces(self):
        """Factory creates RefractiveObjectItem for mixed interface types."""
        data = {
            "name": "Beam Splitter Cube",
            "object_height_mm": 60.0,
            "angle_deg": 45.0,
            "interfaces": [
                {
                    "element_type": "refractive_interface",
                    "name": "Entrance",
                    "x1_mm": -30.0, "y1_mm": -30.0,
                    "x2_mm": -30.0, "y2_mm": 30.0,
                    "n1": 1.0, "n2": 1.5,
                    "is_curved": False,
                    "radius_of_curvature_mm": 0.0,
                },
                {
                    "element_type": "beam_splitter",
                    "name": "BS Surface",
                    "x1_mm": -30.0, "y1_mm": -30.0,
                    "x2_mm": 30.0, "y2_mm": 30.0,
                    "n1": 1.5, "n2": 1.5,
                    "split_T": 50.0,
                    "split_R": 50.0,
                    "is_curved": False,
                    "radius_of_curvature_mm": 0.0,
                    "is_polarizing": False,
                    "pbs_transmission_axis_deg": 0.0,
                },
                {
                    "element_type": "refractive_interface",
                    "name": "Exit",
                    "x1_mm": 30.0, "y1_mm": -30.0,
                    "x2_mm": 30.0, "y2_mm": 30.0,
                    "n1": 1.5, "n2": 1.0,
                    "is_curved": False,
                    "radius_of_curvature_mm": 0.0,
                },
            ]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        # Mixed interface types → RefractiveObjectItem
        assert isinstance(item, RefractiveObjectItem)
        assert len(item.params.interfaces) == 3
    
    def test_create_refractive_object_all_refractive(self):
        """Factory creates RefractiveObjectItem when all interfaces are refractive."""
        data = {
            "name": "Prism",
            "object_height_mm": 80.0,
            "angle_deg": 0.0,
            "interfaces": [
                {
                    "element_type": "refractive_interface",
                    "name": "Surface 1",
                    "x1_mm": -40.0, "y1_mm": 0.0,
                    "x2_mm": 0.0, "y2_mm": 40.0,
                    "n1": 1.0, "n2": 1.5,
                    "is_curved": False,
                    "radius_of_curvature_mm": 0.0,
                },
                {
                    "element_type": "refractive_interface",
                    "name": "Surface 2",
                    "x1_mm": 0.0, "y1_mm": 40.0,
                    "x2_mm": 40.0, "y2_mm": 0.0,
                    "n1": 1.5, "n2": 1.0,
                    "is_curved": False,
                    "radius_of_curvature_mm": 0.0,
                },
            ]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        
        # All refractive → RefractiveObjectItem
        assert isinstance(item, RefractiveObjectItem)
        assert len(item.params.interfaces) == 2


class TestComponentFactoryAngleDefaults:
    """Tests for default angle assignment."""
    
    def test_lens_default_angle(self):
        """Lens gets default angle of 0° (native orientation)."""
        data = {
            "name": "Lens",
            "object_height_mm": 50.0,
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.angle_deg == 0.0
    
    def test_beamsplitter_default_angle(self):
        """Beamsplitter gets default angle of 0° (native orientation)."""
        data = {
            "name": "BS",
            "object_height_mm": 60.0,
            "interfaces": [{
                "element_type": "beam_splitter",
                "name": "Surface",
                "x1_mm": -30.0, "y1_mm": 0.0,
                "x2_mm": 30.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "split_T": 50.0,
                "split_R": 50.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
                "is_polarizing": False,
                "pbs_transmission_axis_deg": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.angle_deg == 0.0
    
    def test_dichroic_default_angle(self):
        """Dichroic gets default angle of 0° (native orientation)."""
        data = {
            "name": "Dichroic",
            "object_height_mm": 60.0,
            "interfaces": [{
                "element_type": "dichroic",
                "name": "Surface",
                "x1_mm": -30.0, "y1_mm": 0.0,
                "x2_mm": 30.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "cutoff_wavelength_nm": 550.0,
                "transition_width_nm": 50.0,
                "pass_type": "longpass",
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.angle_deg == 0.0
    
    def test_mirror_default_angle(self):
        """Mirror gets default angle of 0° (native orientation)."""
        data = {
            "name": "Mirror",
            "object_height_mm": 80.0,
            "interfaces": [{
                "element_type": "mirror",
                "name": "Surface",
                "x1_mm": -40.0, "y1_mm": 0.0,
                "x2_mm": 40.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.angle_deg == 0.0
    
    def test_explicit_angle_overrides_default(self):
        """Explicit angle in data overrides default."""
        data = {
            "name": "Lens",
            "object_height_mm": 50.0,
            "angle_deg": 45.0,  # Override default (0°)
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.angle_deg == 45.0


class TestComponentFactoryEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_missing_interfaces(self):
        """Factory returns None for component without interfaces."""
        data = {
            "name": "Invalid Component",
            "object_height_mm": 50.0,
            # No interfaces!
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item is None
    
    def test_empty_interfaces_list(self):
        """Factory returns None for empty interfaces list."""
        data = {
            "name": "Invalid Component",
            "object_height_mm": 50.0,
            "interfaces": []
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item is None
    
    def test_missing_object_height(self):
        """Factory uses default object height when missing."""
        data = {
            "name": "Test Lens",
            # No object_height_mm
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item is not None
        # Should use some reasonable default
        assert item.params.object_height_mm > 0


class TestComponentFactoryImagePath:
    """Tests for image path handling."""
    
    def test_image_path_preserved(self):
        """Factory preserves image_path from data."""
        data = {
            "name": "Lens with Image",
            "image_path": "/path/to/lens.png",
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.image_path == "/path/to/lens.png"
    
    def test_no_image_path(self):
        """Factory handles missing image_path."""
        data = {
            "name": "Lens No Image",
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "interfaces": [{
                "element_type": "lens",
                "name": "Surface",
                "x1_mm": -25.0, "y1_mm": 0.0,
                "x2_mm": 25.0, "y2_mm": 0.0,
                "n1": 1.0, "n2": 1.5,
                "efl_mm": 100.0,
                "is_curved": False,
                "radius_of_curvature_mm": 0.0,
            }]
        }
        
        item = ComponentFactory.create_item_from_dict(data, 0, 0)
        assert item.params.image_path == ""

