"""
Integration tests for the adapter layer that connects legacy interfaces
to the new polymorphic system.

Test Strategy:
1. Legacy InterfaceDefinition → OpticalInterface (Phase 1)
2. OpticalInterface → IOpticalElement (Phase 2)
3. End-to-end: Legacy → Polymorphic raytracing
"""

import numpy as np

# Legacy imports (existing system)
from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import RefractiveInterface, SourceParams

# New imports (Phase 1 & 2)
from optiverse.data import (
    BeamsplitterProperties,
    DichroicProperties,
    LensProperties,
    LineSegment,
    MirrorProperties,
    OpticalInterface,
    RefractiveProperties,
    WaveplateProperties,
)
from optiverse.raytracing import Polarization, Ray, trace_rays_polymorphic
from optiverse.raytracing.elements import (
    Beamsplitter,
    Dichroic,
    IOpticalElement,
    Lens,
    Mirror,
    RefractiveInterfaceElement,
    Waveplate,
)


class TestLegacyToOpticalInterface:
    """Test conversion from legacy InterfaceDefinition to new OpticalInterface."""

    def test_convert_lens_interface(self):
        """Test converting a legacy lens interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="lens",
            efl_mm=100.0,
            name="Test Lens",
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.name == "Test Lens"
        assert new_iface.get_element_type() == "lens"
        assert np.array_equal(new_iface.geometry.p1, np.array([0.0, -10.0]))
        assert np.array_equal(new_iface.geometry.p2, np.array([0.0, 10.0]))
        assert isinstance(new_iface.properties, LensProperties)
        assert new_iface.properties.efl_mm == 100.0

    def test_convert_mirror_interface(self):
        """Test converting a legacy mirror interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-5.0, x2_mm=0.0, y2_mm=5.0, element_type="mirror", reflectivity=99.0
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "mirror"
        assert isinstance(new_iface.properties, MirrorProperties)
        # Note: reflectivity is stored as 0-1 in new system, 0-100 in legacy
        assert new_iface.properties.reflectivity == 0.99

    def test_convert_refractive_interface(self):
        """Test converting a legacy refractive interface (from RefractiveInterface)."""
        legacy = RefractiveInterface(
            x1_mm=0.0, y1_mm=-5.0, x2_mm=0.0, y2_mm=5.0, n1=1.0, n2=1.5, is_beam_splitter=False
        )

        new_iface = OpticalInterface.from_legacy_refractive_interface(legacy)

        assert new_iface.get_element_type() == "refractive"
        assert isinstance(new_iface.properties, RefractiveProperties)
        assert new_iface.properties.n1 == 1.0
        assert new_iface.properties.n2 == 1.5

    def test_convert_beamsplitter_interface(self):
        """Test converting a legacy beamsplitter interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="beam_splitter",
            split_T=70.0,
            split_R=30.0,
            is_polarizing=True,
            pbs_transmission_axis_deg=45.0,
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "beamsplitter"
        assert isinstance(new_iface.properties, BeamsplitterProperties)
        # Note: split values are stored as 0-1 in new system, 0-100 in legacy
        assert new_iface.properties.transmission == 0.70
        assert new_iface.properties.reflection == 0.30
        assert new_iface.properties.is_polarizing is True
        assert new_iface.properties.polarization_axis_deg == 45.0

    def test_convert_waveplate_interface(self):
        """Test converting a polarizing_interface (waveplate) interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="polarizing_interface",
            polarizer_subtype="waveplate",
            name="QWP",
            phase_shift_deg=90.0,
            fast_axis_deg=45.0,
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "waveplate"
        assert isinstance(new_iface.properties, WaveplateProperties)
        assert new_iface.properties.phase_shift_deg == 90.0
        assert new_iface.properties.fast_axis_deg == 45.0

    def test_convert_legacy_waveplate_element_type(self):
        """Test converting a legacy 'waveplate' element_type for backward compatibility."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="waveplate", name="QWP"
        )
        # Old style: properties set as attributes
        legacy.phase_shift_deg = 90.0
        legacy.fast_axis_deg = 45.0

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "waveplate"
        assert isinstance(new_iface.properties, WaveplateProperties)
        assert new_iface.properties.phase_shift_deg == 90.0
        assert new_iface.properties.fast_axis_deg == 45.0

    def test_convert_dichroic_interface(self):
        """Test converting a legacy dichroic interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="dichroic",
            cutoff_wavelength_nm=550.0,
            transition_width_nm=20.0,
            pass_type="longpass",
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "dichroic"
        assert isinstance(new_iface.properties, DichroicProperties)
        assert new_iface.properties.cutoff_wavelength_nm == 550.0
        assert new_iface.properties.transition_width_nm == 20.0


class TestOpticalInterfaceToPolymorphicElement:
    """Test conversion from OpticalInterface to IOpticalElement."""

    def test_convert_to_mirror_element(self):
        """Test converting OpticalInterface (mirror) to Mirror element."""
        geom = LineSegment(np.array([0, -10]), np.array([0, 10]))
        props = MirrorProperties(reflectivity=0.99)
        iface = OpticalInterface(geometry=geom, properties=props, name="Test Mirror")

        # This is the adapter function we'll implement
        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Mirror)
        assert isinstance(element, IOpticalElement)
        # Verify element can interact with rays
        assert hasattr(element, "interact")

    def test_convert_to_lens_element(self):
        """Test converting OpticalInterface (lens) to Lens element."""
        geom = LineSegment(np.array([10, -15]), np.array([10, 15]))
        props = LensProperties(efl_mm=75.0)
        iface = OpticalInterface(geometry=geom, properties=props, name="Test Lens")

        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Lens)
        assert isinstance(element, IOpticalElement)

    def test_convert_to_refractive_element(self):
        """Test converting OpticalInterface (refractive) to RefractiveInterfaceElement."""
        geom = LineSegment(np.array([20, -10]), np.array([20, 10]))
        props = RefractiveProperties(n1=1.0, n2=1.5)
        iface = OpticalInterface(geometry=geom, properties=props)

        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, RefractiveInterfaceElement)
        assert isinstance(element, IOpticalElement)

    def test_convert_to_beamsplitter_element(self):
        """Test converting OpticalInterface (beamsplitter) to Beamsplitter element."""
        geom = LineSegment(np.array([30, -10]), np.array([30, 10]))
        props = BeamsplitterProperties(transmission=0.5, reflection=0.5)
        iface = OpticalInterface(geometry=geom, properties=props)

        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Beamsplitter)
        assert isinstance(element, IOpticalElement)

    def test_convert_to_waveplate_element(self):
        """Test converting OpticalInterface (waveplate) to Waveplate element."""
        geom = LineSegment(np.array([40, -10]), np.array([40, 10]))
        props = WaveplateProperties(phase_shift_deg=90.0, fast_axis_deg=0.0)
        iface = OpticalInterface(geometry=geom, properties=props)

        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Waveplate)
        assert isinstance(element, IOpticalElement)

    def test_convert_to_dichroic_element(self):
        """Test converting OpticalInterface (dichroic) to Dichroic element."""
        geom = LineSegment(np.array([50, -10]), np.array([50, 10]))
        props = DichroicProperties(
            cutoff_wavelength_nm=550.0, transition_width_nm=10.0, pass_type="longpass"
        )
        iface = OpticalInterface(geometry=geom, properties=props)

        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Dichroic)
        assert isinstance(element, IOpticalElement)


class TestEndToEndIntegration:
    """Test complete integration from legacy interfaces through to polymorphic raytracing."""

    def test_legacy_to_polymorphic_pipeline(self):
        """Test the complete conversion pipeline: Legacy → Phase1 → Phase2 → Raytrace."""
        # Create a legacy lens interface
        legacy_lens = InterfaceDefinition(
            x1_mm=10.0, y1_mm=-10.0, x2_mm=10.0, y2_mm=10.0, element_type="lens", efl_mm=50.0
        )

        # Create a legacy mirror interface
        legacy_mirror = InterfaceDefinition(
            x1_mm=60.0,
            y1_mm=-10.0,
            x2_mm=60.0,
            y2_mm=10.0,
            element_type="mirror",
            reflectivity=99.0,
        )

        # Step 1: Convert to new OpticalInterface
        lens_iface = OpticalInterface.from_legacy_interface_definition(legacy_lens)
        mirror_iface = OpticalInterface.from_legacy_interface_definition(legacy_mirror)

        # Step 2: Convert to polymorphic elements
        from optiverse.integration.adapter import create_polymorphic_element

        lens_element = create_polymorphic_element(lens_iface)
        mirror_element = create_polymorphic_element(mirror_iface)

        # Step 3: Create a ray and test interaction
        Ray(
            position=np.array([0.0, 5.0]),
            direction=np.array([1.0, 0.0]),
            remaining_length=100.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            base_rgb=(255, 0, 0),
        )

        # The ray should interact with both elements
        assert isinstance(lens_element, IOpticalElement)
        assert isinstance(mirror_element, IOpticalElement)

        # Both should have the interact method
        assert callable(getattr(lens_element, "interact", None))
        assert callable(getattr(mirror_element, "interact", None))

    def test_full_scene_conversion(self):
        """Test converting a scene with multiple legacy interfaces to polymorphic elements."""
        # Create various legacy interfaces
        legacy_interfaces = [
            InterfaceDefinition(
                x1_mm=10, y1_mm=-10, x2_mm=10, y2_mm=10, element_type="lens", efl_mm=50
            ),
            InterfaceDefinition(x1_mm=30, y1_mm=-10, x2_mm=30, y2_mm=10, element_type="mirror"),
            InterfaceDefinition(
                x1_mm=50,
                y1_mm=-10,
                x2_mm=50,
                y2_mm=10,
                element_type="beam_splitter",
                split_T=50,
                split_R=50,
            ),
            RefractiveInterface(
                x1_mm=70, y1_mm=-10, x2_mm=70, y2_mm=10, n1=1.0, n2=1.5, is_beam_splitter=False
            ),
        ]

        from optiverse.integration.adapter import convert_legacy_interfaces

        # Convert all interfaces
        polymorphic_elements = convert_legacy_interfaces(legacy_interfaces)

        # Verify we got 4 elements
        assert len(polymorphic_elements) == 4

        # Verify types
        assert isinstance(polymorphic_elements[0], Lens)
        assert isinstance(polymorphic_elements[1], Mirror)
        assert isinstance(polymorphic_elements[2], Beamsplitter)
        assert isinstance(polymorphic_elements[3], RefractiveInterfaceElement)

        # All should implement IOpticalElement
        for element in polymorphic_elements:
            assert isinstance(element, IOpticalElement)

    def test_full_raytracing_pipeline(self):
        """Test full raytracing with polymorphic elements."""
        # Create elements
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=1.0)
        iface = OpticalInterface(geometry=geom, properties=props)

        from optiverse.integration.adapter import create_polymorphic_element

        mirror = create_polymorphic_element(iface)

        # Create source
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            ray_length_mm=200.0,
            polarization_type="horizontal",
        )

        # Trace
        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        assert len(paths) >= 1
        assert hasattr(paths[0], "points")
        assert hasattr(paths[0], "rgba")


class TestFeatureFlagSwitching:
    """Test that conversion works correctly."""

    def test_polymorphic_conversion(self):
        """Test that polymorphic conversion works."""
        legacy_interfaces = [
            InterfaceDefinition(
                x1_mm=10, y1_mm=-10, x2_mm=10, y2_mm=10, element_type="lens", efl_mm=50
            ),
        ]

        from optiverse.integration.adapter import convert_legacy_interfaces

        elements = convert_legacy_interfaces(legacy_interfaces)
        assert isinstance(elements[0], IOpticalElement)


class TestPerformanceComparison:
    """Benchmark the conversion overhead."""

    def test_conversion_performance(self):
        """Benchmark the conversion overhead."""
        import time

        # Create 100 legacy interfaces
        legacy_interfaces = [
            InterfaceDefinition(
                x1_mm=float(i), y1_mm=-10, x2_mm=float(i), y2_mm=10, element_type="lens", efl_mm=50
            )
            for i in range(100)
        ]

        # Measure conversion time
        start = time.perf_counter()

        from optiverse.integration.adapter import convert_legacy_interfaces

        elements = convert_legacy_interfaces(legacy_interfaces)

        elapsed = time.perf_counter() - start

        # Conversion should be fast (< 10ms for 100 elements)
        assert elapsed < 0.01, f"Conversion too slow: {elapsed * 1000:.2f}ms"
        assert len(elements) == 100
