"""
Integration tests for the adapter layer that connects legacy interfaces to the new polymorphic system.

Test Strategy:
1. Legacy InterfaceDefinition → OpticalInterface (Phase 1)
2. OpticalInterface → IOpticalElement (Phase 2)
3. End-to-end: Legacy → Polymorphic raytracing
"""
import pytest
import numpy as np

# Legacy imports (existing system)
from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import RefractiveInterface, SourceParams

# New imports (Phase 1 & 2)
from optiverse.data import OpticalInterface, LineSegment, LensProperties, MirrorProperties, RefractiveProperties, BeamsplitterProperties, WaveplateProperties, DichroicProperties
from optiverse.raytracing import Ray, Polarization
from optiverse.raytracing.elements import IOpticalElement, Mirror, Lens, RefractiveInterfaceElement, Beamsplitter, Waveplate, Dichroic


class TestLegacyToOpticalInterface:
    """Test conversion from legacy InterfaceDefinition to new OpticalInterface."""

    def test_convert_lens_interface(self):
        """Test converting a legacy lens interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0,
            x2_mm=0.0, y2_mm=10.0,
            element_type="lens",
            efl_mm=100.0,
            name="Test Lens"
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
            x1_mm=0.0, y1_mm=-5.0,
            x2_mm=0.0, y2_mm=5.0,
            element_type="mirror",
            reflectivity=99.0
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "mirror"
        assert isinstance(new_iface.properties, MirrorProperties)
        assert new_iface.properties.reflectivity == 99.0

    def test_convert_refractive_interface(self):
        """Test converting a legacy refractive interface (from RefractiveInterface)."""
        legacy = RefractiveInterface(
            x1_mm=0.0, y1_mm=-5.0,
            x2_mm=0.0, y2_mm=5.0,
            n1=1.0, n2=1.5,
            is_beam_splitter=False
        )

        new_iface = OpticalInterface.from_legacy_refractive_interface(legacy)

        assert new_iface.get_element_type() == "refractive_interface"
        assert isinstance(new_iface.properties, RefractiveProperties)
        assert new_iface.properties.n1 == 1.0
        assert new_iface.properties.n2 == 1.5

    def test_convert_beamsplitter_interface(self):
        """Test converting a legacy beamsplitter interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0,
            x2_mm=0.0, y2_mm=10.0,
            element_type="beam_splitter",
            split_T=70.0,
            split_R=30.0,
            is_polarizing=True,
            pbs_transmission_axis_deg=45.0
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "beam_splitter"
        assert isinstance(new_iface.properties, BeamsplitterProperties)
        assert new_iface.properties.split_T == 70.0
        assert new_iface.properties.split_R == 30.0
        assert new_iface.properties.is_polarizing is True
        assert new_iface.properties.pbs_transmission_axis_deg == 45.0

    def test_convert_waveplate_interface(self):
        """Test converting a polarizing_interface (waveplate) interface."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0,
            x2_mm=0.0, y2_mm=10.0,
            element_type="polarizing_interface",
            polarizer_subtype="waveplate",
            name="QWP",
            phase_shift_deg=90.0,
            fast_axis_deg=45.0
        )

        new_iface = OpticalInterface.from_legacy_interface_definition(legacy)

        assert new_iface.get_element_type() == "waveplate"
        assert isinstance(new_iface.properties, WaveplateProperties)
        assert new_iface.properties.phase_shift_deg == 90.0
        assert new_iface.properties.fast_axis_deg == 45.0

    def test_convert_legacy_waveplate_element_type(self):
        """Test converting a legacy 'waveplate' element_type for backward compatibility."""
        legacy = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0,
            x2_mm=0.0, y2_mm=10.0,
            element_type="waveplate",
            name="QWP"
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
            x1_mm=0.0, y1_mm=-10.0,
            x2_mm=0.0, y2_mm=10.0,
            element_type="dichroic",
            cutoff_wavelength_nm=550.0,
            transition_width_nm=20.0,
            pass_type="longpass"
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
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props, name="Test Mirror")

        # This is the adapter function we'll implement
        from optiverse.integration.adapter import create_polymorphic_element

        element = create_polymorphic_element(iface)

        assert isinstance(element, Mirror)
        assert isinstance(element, IOpticalElement)
        # Verify element can interact with rays
        assert hasattr(element, 'interact_with_ray')

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
        props = BeamsplitterProperties(split_T=50.0, split_R=50.0)
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
        from optiverse.data.optical_properties import PassType

        geom = LineSegment(np.array([50, -10]), np.array([50, 10]))
        props = DichroicProperties(cutoff_wavelength_nm=550.0, transition_width_nm=10.0, pass_type=PassType.LONGPASS)
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
            x1_mm=10.0, y1_mm=-10.0,
            x2_mm=10.0, y2_mm=10.0,
            element_type="lens",
            efl_mm=50.0
        )

        # Create a legacy mirror interface
        legacy_mirror = InterfaceDefinition(
            x1_mm=60.0, y1_mm=-10.0,
            x2_mm=60.0, y2_mm=10.0,
            element_type="mirror",
            reflectivity=99.0
        )

        # Step 1: Convert to new OpticalInterface
        lens_iface = OpticalInterface.from_legacy_interface_definition(legacy_lens)
        mirror_iface = OpticalInterface.from_legacy_interface_definition(legacy_mirror)

        # Step 2: Convert to polymorphic elements
        from optiverse.integration.adapter import create_polymorphic_element

        lens_element = create_polymorphic_element(lens_iface)
        mirror_element = create_polymorphic_element(mirror_iface)

        # Step 3: Create a ray and test interaction
        ray = Ray(
            position=np.array([0.0, 5.0]),
            direction=np.array([1.0, 0.0]),
            remaining_length=100.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            base_rgb=(255, 0, 0)
        )

        # The ray should interact with both elements
        assert isinstance(lens_element, IOpticalElement)
        assert isinstance(mirror_element, IOpticalElement)

        # Both should have the interact_with_ray method
        assert callable(getattr(lens_element, 'interact_with_ray', None))
        assert callable(getattr(mirror_element, 'interact_with_ray', None))

    def test_full_scene_conversion(self):
        """Test converting a scene with multiple legacy interfaces to polymorphic elements."""
        # Create various legacy interfaces
        legacy_interfaces = [
            InterfaceDefinition(x1_mm=10, y1_mm=-10, x2_mm=10, y2_mm=10, element_type="lens", efl_mm=50),
            InterfaceDefinition(x1_mm=30, y1_mm=-10, x2_mm=30, y2_mm=10, element_type="mirror"),
            InterfaceDefinition(x1_mm=50, y1_mm=-10, x2_mm=50, y2_mm=10, element_type="beam_splitter", split_T=50, split_R=50),
            RefractiveInterface(x1_mm=70, y1_mm=-10, x2_mm=70, y2_mm=10, n1=1.0, n2=1.5, is_beam_splitter=False),
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


class TestBackwardCompatibility:
    """Test that the adapter maintains backward compatibility with existing scenes."""

    def test_old_system_still_works(self):
        """Verify the old raytracing system still works (no breaking changes)."""
        # This test ensures we haven't broken existing functionality
        from optiverse.core.models import OpticalElement
        from optiverse.core.use_cases import trace_rays as old_trace_rays

        # Create old-style elements
        old_lens = OpticalElement(
            kind="lens",
            p1=np.array([10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            efl_mm=50.0
        )

        old_mirror = OpticalElement(
            kind="mirror",
            p1=np.array([60.0, -10.0]),
            p2=np.array([60.0, 10.0])
        )

        # Create old-style source
        old_source = SourceParams(
            pos_mm=np.array([0.0, 0.0]),
            angle_deg=0.0,
            num_rays=5,
            wavelength_nm=633.0
        )

        # Old system should still work
        paths = old_trace_rays([old_lens, old_mirror], [old_source], max_events=10)

        # Should return RayPath objects
        assert isinstance(paths, list)
        # Each path should have points
        for path in paths:
            assert hasattr(path, 'points')
            assert hasattr(path, 'rgba')

    def test_feature_flag_switching(self):
        """Test that we can switch between old and new systems via feature flag."""
        # This test ensures graceful migration path
        # In the real implementation, this would be controlled by a config setting

        legacy_interfaces = [
            InterfaceDefinition(x1_mm=10, y1_mm=-10, x2_mm=10, y2_mm=10, element_type="lens", efl_mm=50),
        ]

        # Flag OFF → Use old system (this should still work)
        USE_NEW_RAYTRACING = False

        if USE_NEW_RAYTRACING:
            from optiverse.integration.adapter import convert_legacy_interfaces
            elements = convert_legacy_interfaces(legacy_interfaces)
            assert isinstance(elements[0], IOpticalElement)
        else:
            # Old conversion path (what currently exists in MainWindow)
            from optiverse.core.models import OpticalElement
            iface = legacy_interfaces[0]
            elem = OpticalElement(kind="lens", p1=np.array([10, -10]), p2=np.array([10, 10]), efl_mm=50)
            assert elem.kind == "lens"

        # Flag ON → Use new system
        USE_NEW_RAYTRACING = True

        if USE_NEW_RAYTRACING:
            from optiverse.integration.adapter import convert_legacy_interfaces
            elements = convert_legacy_interfaces(legacy_interfaces)
            assert isinstance(elements[0], IOpticalElement)


class TestPerformanceComparison:
    """Compare performance of old vs new systems (benchmark tests)."""

    def test_conversion_performance(self):
        """Benchmark the conversion overhead."""
        import time

        # Create 100 legacy interfaces
        legacy_interfaces = [
            InterfaceDefinition(
                x1_mm=float(i), y1_mm=-10, x2_mm=float(i), y2_mm=10,
                element_type="lens", efl_mm=50
            )
            for i in range(100)
        ]

        # Measure conversion time
        start = time.perf_counter()

        from optiverse.integration.adapter import convert_legacy_interfaces
        elements = convert_legacy_interfaces(legacy_interfaces)

        elapsed = time.perf_counter() - start

        # Conversion should be fast (< 10ms for 100 elements)
        assert elapsed < 0.01, f"Conversion too slow: {elapsed*1000:.2f}ms"
        assert len(elements) == 100



