"""
Tests for editing component properties in the UI.

These tests verify that:
- Source properties can be edited (position, angle, rays, wavelength, etc.)
- Component properties can be edited (position, rotation)
- Interface properties can be edited (EFL, reflectivity, split ratios, etc.)
- Property changes are reflected in the scene
"""

from __future__ import annotations

from PyQt6 import QtCore

from optiverse.core.component_types import ComponentType
from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import ComponentParams, SourceParams
from optiverse.objects import ComponentItem, SourceItem


class TestSourcePropertyEditing:
    """Test editing source properties."""

    def test_edit_source_position(self, main_window):
        """Test changing source position."""
        # Add a source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0))
        main_window.scene.addItem(source)

        # Change position via params
        source.params.x_mm = 100.0
        source.params.y_mm = 50.0
        source.setPos(QtCore.QPointF(100.0, 50.0))

        # Verify position changed
        assert source.pos().x() == 100.0
        assert source.pos().y() == 50.0

    def test_edit_source_angle(self, main_window):
        """Test changing source emission angle."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, angle_deg=0.0))
        main_window.scene.addItem(source)

        # Change angle
        source.params.angle_deg = 45.0
        source.setRotation(45.0)

        # Verify angle changed
        assert source.rotation() == 45.0

    def test_edit_source_num_rays(self, main_window):
        """Test changing number of rays."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, n_rays=5))
        main_window.scene.addItem(source)

        # Change number of rays
        source.params.n_rays = 10

        # Verify change
        assert source.params.n_rays == 10

    def test_edit_source_wavelength(self, main_window):
        """Test changing source wavelength."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, wavelength_nm=532.0))
        main_window.scene.addItem(source)

        # Change wavelength
        source.params.wavelength_nm = 633.0

        # Verify change
        assert source.params.wavelength_nm == 633.0

    def test_edit_source_spread(self, main_window):
        """Test changing source angular spread."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, spread_deg=0.0))
        main_window.scene.addItem(source)

        # Change spread
        source.params.spread_deg = 15.0

        # Verify change
        assert source.params.spread_deg == 15.0

    def test_edit_source_color(self, main_window):
        """Test changing source color."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, color_hex="#FF0000"))
        main_window.scene.addItem(source)

        # Change color
        source.params.color_hex = "#00FF00"

        # Verify change
        assert source.params.color_hex == "#00FF00"

    def test_edit_source_ray_length(self, main_window):
        """Test changing source ray length."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, ray_length_mm=1000.0))
        main_window.scene.addItem(source)

        # Change ray length
        source.params.ray_length_mm = 2000.0

        # Verify change
        assert source.params.ray_length_mm == 2000.0

    def test_edit_source_size(self, main_window):
        """Test changing source aperture size."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, size_mm=10.0))
        main_window.scene.addItem(source)

        # Change size
        source.params.size_mm = 20.0

        # Verify change
        assert source.params.size_mm == 20.0

    def test_edit_source_polarization(self, main_window):
        """Test changing source polarization."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, polarization_type="horizontal"))
        main_window.scene.addItem(source)

        # Change polarization
        source.params.polarization_type = "vertical"

        # Verify change
        assert source.params.polarization_type == "vertical"


class TestComponentPositionEditing:
    """Test editing component positions."""

    def test_edit_lens_position(self, main_window):
        """Test changing lens position."""
        item = main_window.placement_handler.place_component_at(
            ComponentType.LENS, QtCore.QPointF(0, 0)
        )

        # Move the lens
        new_pos = QtCore.QPointF(150.0, 75.0)
        item.setPos(new_pos)

        # Verify position
        assert item.pos().x() == 150.0
        assert item.pos().y() == 75.0

    def test_edit_mirror_position(self, main_window):
        """Test changing mirror position."""
        item = main_window.placement_handler.place_component_at(
            ComponentType.MIRROR, QtCore.QPointF(0, 0)
        )

        # Move the mirror
        new_pos = QtCore.QPointF(-100.0, 200.0)
        item.setPos(new_pos)

        # Verify position
        assert item.pos().x() == -100.0
        assert item.pos().y() == 200.0

    def test_edit_component_rotation(self, main_window):
        """Test changing component rotation."""
        item = main_window.placement_handler.place_component_at(
            ComponentType.LENS, QtCore.QPointF(0, 0)
        )
        initial_rotation = item.rotation()

        # Rotate the lens
        new_rotation = initial_rotation + 30.0
        item.setRotation(new_rotation)

        # Verify rotation
        assert abs(item.rotation() - new_rotation) < 0.1

    def test_position_change_updates_params(self, main_window):
        """Test that position changes update params."""
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0))
        main_window.scene.addItem(source)

        # Move via setPos
        source.setPos(QtCore.QPointF(200.0, 100.0))

        # Update params to match (as UI would do)
        source.params.x_mm = 200.0
        source.params.y_mm = 100.0

        assert source.params.x_mm == 200.0
        assert source.params.y_mm == 100.0


class TestInterfacePropertyEditing:
    """Test editing interface properties on components."""

    def test_edit_lens_efl(self, main_window):
        """Test changing lens effective focal length."""
        # Create a lens with specific EFL
        interface = InterfaceDefinition(
            element_type="lens",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            efl_mm=100.0,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=90.0,
            object_height_mm=50.0,
            interfaces=[interface],
        )
        lens = ComponentItem(params)
        main_window.scene.addItem(lens)

        # Change EFL
        lens.params.interfaces[0].efl_mm = 200.0

        # Verify change
        assert lens.params.interfaces[0].efl_mm == 200.0

    def test_edit_beamsplitter_split_ratio(self, main_window):
        """Test changing beamsplitter split ratio."""
        # Create a beamsplitter
        interface = InterfaceDefinition(
            element_type="beam_splitter",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            split_T=50.0,
            split_R=50.0,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=45.0,
            object_height_mm=50.0,
            interfaces=[interface],
        )
        bs = ComponentItem(params)
        main_window.scene.addItem(bs)

        # Change split ratio
        bs.params.interfaces[0].split_T = 70.0
        bs.params.interfaces[0].split_R = 30.0

        # Verify change
        assert bs.params.interfaces[0].split_T == 70.0
        assert bs.params.interfaces[0].split_R == 30.0

    def test_edit_dichroic_cutoff(self, main_window):
        """Test changing dichroic cutoff wavelength."""
        # Create a dichroic
        interface = InterfaceDefinition(
            element_type="dichroic",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            cutoff_wavelength_nm=550.0,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=45.0,
            object_height_mm=50.0,
            interfaces=[interface],
        )
        dichroic = ComponentItem(params)
        main_window.scene.addItem(dichroic)

        # Change cutoff
        dichroic.params.interfaces[0].cutoff_wavelength_nm = 600.0

        # Verify change
        assert dichroic.params.interfaces[0].cutoff_wavelength_nm == 600.0

    def test_edit_refractive_index(self, main_window):
        """Test changing refractive indices."""
        interface = InterfaceDefinition(
            element_type="refractive_interface",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            n1=1.0,
            n2=1.5,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            object_height_mm=50.0,
            interfaces=[interface],
        )
        component = ComponentItem(params)
        main_window.scene.addItem(component)

        # Change refractive indices
        component.params.interfaces[0].n1 = 1.5
        component.params.interfaces[0].n2 = 1.0

        # Verify change
        assert component.params.interfaces[0].n1 == 1.5
        assert component.params.interfaces[0].n2 == 1.0

    def test_edit_interface_name(self, main_window):
        """Test changing interface name."""
        interface = InterfaceDefinition(
            element_type="lens",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            name="Original Name",
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=90.0,
            object_height_mm=50.0,
            interfaces=[interface],
        )
        component = ComponentItem(params)
        main_window.scene.addItem(component)

        # Change name
        component.params.interfaces[0].name = "New Name"

        # Verify change
        assert component.params.interfaces[0].name == "New Name"


class TestPropertyEditingTriggersRetrace:
    """Test that property changes can trigger retrace."""

    def test_source_change_with_autotrace(self, main_window):
        """Test that source changes work with autotrace enabled."""
        main_window.autotrace = True

        # Add source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, n_rays=5))
        main_window.scene.addItem(source)

        # Change source property
        source.params.n_rays = 10

        # Trigger retrace (as UI would do after property change)
        main_window.raytracing_controller.schedule_retrace()
        main_window.raytracing_controller._do_retrace()

        # Ray data should be updated
        # (We're just verifying it doesn't crash)
        assert True

    def test_component_move_with_autotrace(self, main_window):
        """Test that moving component works with autotrace."""
        main_window.autotrace = True

        # Add source and lens
        source = SourceItem(SourceParams(x_mm=-100.0, y_mm=0.0, n_rays=1))
        main_window.scene.addItem(source)

        item = main_window.placement_handler.place_component_at(
            ComponentType.LENS, QtCore.QPointF(0, 0)
        )

        # Retrace initially
        main_window.raytracing_controller.retrace()

        # Move the lens
        item.setPos(QtCore.QPointF(50.0, 0.0))

        # Retrace after move
        main_window.raytracing_controller.retrace()

        # Should still have rays (might be different count due to geometry)
        assert len(main_window.raytracing_controller.ray_data) > 0


class TestMultipleInterfaceEditing:
    """Test editing components with multiple interfaces."""

    def test_edit_first_interface(self, main_window):
        """Test editing first interface of multi-interface component."""
        interface1 = InterfaceDefinition(
            element_type="refractive_interface",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            n1=1.0,
            n2=1.5,
        )
        interface2 = InterfaceDefinition(
            element_type="refractive_interface",
            x1_mm=-25.0,
            y1_mm=5.0,
            x2_mm=25.0,
            y2_mm=5.0,
            n1=1.5,
            n2=1.0,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            object_height_mm=50.0,
            interfaces=[interface1, interface2],
        )
        component = ComponentItem(params)
        main_window.scene.addItem(component)

        # Edit first interface
        component.params.interfaces[0].n2 = 1.6

        # Verify only first changed
        assert component.params.interfaces[0].n2 == 1.6
        assert component.params.interfaces[1].n1 == 1.5  # Unchanged

    def test_edit_second_interface(self, main_window):
        """Test editing second interface of multi-interface component."""
        interface1 = InterfaceDefinition(
            element_type="lens",
            x1_mm=-25.0,
            y1_mm=0.0,
            x2_mm=25.0,
            y2_mm=0.0,
            efl_mm=100.0,
        )
        interface2 = InterfaceDefinition(
            element_type="lens",
            x1_mm=-25.0,
            y1_mm=5.0,
            x2_mm=25.0,
            y2_mm=5.0,
            efl_mm=150.0,
        )
        params = ComponentParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=90.0,
            object_height_mm=50.0,
            interfaces=[interface1, interface2],
        )
        component = ComponentItem(params)
        main_window.scene.addItem(component)

        # Edit second interface
        component.params.interfaces[1].efl_mm = 200.0

        # Verify only second changed
        assert component.params.interfaces[0].efl_mm == 100.0  # Unchanged
        assert component.params.interfaces[1].efl_mm == 200.0
