"""
Test suite for polymorphic optical elements.

Tests the IOpticalElement interface and all concrete implementations.
This defines expected behavior before implementation (TDD).
"""
import pytest
import numpy as np
import math


class TestRayState:
    """Test RayState data structure"""
    
    def test_create_ray_state(self):
        """Test creating a ray state"""
        from optiverse.raytracing.ray import RayState, Polarization
        
        ray = RayState(
            position=np.array([0.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[np.array([0.0, 0.0])],
            events=0
        )
        
        assert np.array_equal(ray.position, np.array([0.0, 0.0]))
        assert np.array_equal(ray.direction, np.array([1.0, 0.0]))
        assert ray.intensity == 1.0
        assert ray.events == 0
    
    def test_ray_state_advance(self):
        """Test advancing ray along direction"""
        from optiverse.raytracing.ray import RayState, Polarization
        
        ray = RayState(
            position=np.array([0.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        new_ray = ray.advance(distance=10.0)
        
        assert np.allclose(new_ray.position, np.array([10.0, 0.0]))
        assert new_ray.events == ray.events  # Events not incremented by advance


class TestIOpticalElement:
    """Test IOpticalElement interface"""
    
    def test_interface_exists(self):
        """Test that IOpticalElement interface can be imported"""
        from optiverse.raytracing.elements.base import IOpticalElement
        
        # Check it's an abstract base class
        assert hasattr(IOpticalElement, 'interact')
        assert hasattr(IOpticalElement, 'get_geometry')
        assert hasattr(IOpticalElement, 'get_bounding_box')
    
    def test_cannot_instantiate_interface(self):
        """Test that IOpticalElement cannot be instantiated directly"""
        from optiverse.raytracing.elements.base import IOpticalElement
        
        with pytest.raises(TypeError):
            IOpticalElement()


class TestMirrorElement:
    """Test MirrorElement implementation"""
    
    def test_create_mirror(self):
        """Test creating a mirror element"""
        from optiverse.raytracing.elements import MirrorElement
        
        mirror = MirrorElement(
            p1=np.array([0.0, -10.0]),
            p2=np.array([0.0, 10.0]),
            reflectivity=0.99
        )
        
        p1, p2 = mirror.get_geometry()
        assert np.array_equal(p1, np.array([0.0, -10.0]))
        assert np.array_equal(p2, np.array([0.0, 10.0]))
    
    def test_mirror_reflection(self):
        """Test mirror reflects ray according to law of reflection"""
        from optiverse.raytracing.elements import MirrorElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Vertical mirror at x=0
        mirror = MirrorElement(
            p1=np.array([0.0, -10.0]),
            p2=np.array([0.0, 10.0]),
            reflectivity=0.99
        )
        
        # Ray traveling right, hits mirror
        ray = RayState(
            position=np.array([-5.0, 0.0]),
            direction=np.array([1.0, 0.0]),  # Right
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0, 0.0])  # Normal points right
        tangent = np.array([0.0, 1.0])  # Tangent points up
        
        # Interact
        output_rays = mirror.interact(ray, hit_point, normal, tangent)
        
        # Should have one reflected ray
        assert len(output_rays) == 1
        
        reflected = output_rays[0]
        # Should reflect back left
        assert np.allclose(reflected.direction, np.array([-1.0, 0.0]))
        # Intensity reduced by reflectivity
        assert np.isclose(reflected.intensity, 0.99)
        # Events incremented
        assert reflected.events == 1
    
    def test_mirror_at_45_degrees(self):
        """Test mirror at 45° reflects ray 90°"""
        from optiverse.raytracing.elements import MirrorElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # 45° mirror
        mirror = MirrorElement(
            p1=np.array([-10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            reflectivity=1.0
        )
        
        # Ray traveling right
        ray = RayState(
            position=np.array([-5.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        # 45° mirror: normal at 135° (pointing upper-left)
        normal = np.array([-1.0/np.sqrt(2), 1.0/np.sqrt(2)])
        tangent = np.array([1.0/np.sqrt(2), 1.0/np.sqrt(2)])
        
        output_rays = mirror.interact(ray, hit_point, normal, tangent)
        reflected = output_rays[0]
        
        # Should reflect upward
        assert np.allclose(reflected.direction, np.array([0.0, 1.0]), atol=1e-6)


class TestLensElement:
    """Test LensElement implementation"""
    
    def test_create_lens(self):
        """Test creating a lens element"""
        from optiverse.raytracing.elements import LensElement
        
        lens = LensElement(
            p1=np.array([0.0, -15.0]),
            p2=np.array([0.0, 15.0]),
            efl_mm=100.0
        )
        
        p1, p2 = lens.get_geometry()
        assert np.array_equal(p1, np.array([0.0, -15.0]))
    
    def test_lens_on_axis_ray_unchanged(self):
        """Test lens doesn't deflect on-axis ray"""
        from optiverse.raytracing.elements import LensElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Vertical lens at x=0
        lens = LensElement(
            p1=np.array([0.0, -15.0]),
            p2=np.array([0.0, 15.0]),
            efl_mm=100.0
        )
        
        # On-axis ray (y=0)
        ray = RayState(
            position=np.array([-10.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0, 0.0])
        tangent = np.array([0.0, 1.0])
        
        output_rays = lens.interact(ray, hit_point, normal, tangent)
        
        assert len(output_rays) == 1
        refracted = output_rays[0]
        
        # On-axis ray should continue straight
        assert np.allclose(refracted.direction, np.array([1.0, 0.0]), atol=1e-6)
    
    def test_lens_off_axis_ray_deflected(self):
        """Test lens deflects off-axis ray toward focus"""
        from optiverse.raytracing.elements import LensElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Vertical lens at x=0, f=100mm
        lens = LensElement(
            p1=np.array([0.0, -15.0]),
            p2=np.array([0.0, 15.0]),
            efl_mm=100.0
        )
        
        # Off-axis ray at y=10mm
        ray = RayState(
            position=np.array([-10.0, 10.0]),
            direction=np.array([1.0, 0.0]),  # Parallel to axis
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 10.0])
        normal = np.array([1.0, 0.0])
        tangent = np.array([0.0, 1.0])
        
        output_rays = lens.interact(ray, hit_point, normal, tangent)
        refracted = output_rays[0]
        
        # Should be deflected downward (toward focus)
        # tan(deflection) ≈ y/f = 10/100 = 0.1 rad ≈ 5.7°
        assert refracted.direction[0] > 0  # Still going forward
        assert refracted.direction[1] < 0  # Deflected downward


class TestRefractiveElement:
    """Test RefractiveElement implementation"""
    
    def test_create_refractive_interface(self):
        """Test creating a refractive interface"""
        from optiverse.raytracing.elements import RefractiveElement
        
        interface = RefractiveElement(
            p1=np.array([0.0, -5.0]),
            p2=np.array([0.0, 5.0]),
            n1=1.0,
            n2=1.5
        )
        
        p1, p2 = interface.get_geometry()
        assert np.array_equal(p1, np.array([0.0, -5.0]))
    
    def test_refractive_normal_incidence(self):
        """Test refraction at normal incidence (no bending)"""
        from optiverse.raytracing.elements import RefractiveElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Air-glass interface
        interface = RefractiveElement(
            p1=np.array([0.0, -5.0]),
            p2=np.array([0.0, 5.0]),
            n1=1.0,  # Air
            n2=1.5   # Glass
        )
        
        # Ray perpendicular to interface
        ray = RayState(
            position=np.array([-1.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0, 0.0])
        tangent = np.array([0.0, 1.0])
        
        output_rays = interface.interact(ray, hit_point, normal, tangent)
        
        # Should have transmitted and reflected rays
        assert len(output_rays) >= 1
        
        # Find transmitted ray (should be strongest)
        transmitted = max(output_rays, key=lambda r: r.intensity)
        
        # Normal incidence: no bending
        assert np.allclose(transmitted.direction, np.array([1.0, 0.0]), atol=1e-6)
    
    def test_total_internal_reflection(self):
        """Test total internal reflection when angle exceeds critical angle"""
        from optiverse.raytracing.elements import RefractiveElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Glass-air interface (going from dense to less dense)
        interface = RefractiveElement(
            p1=np.array([0.0, -5.0]),
            p2=np.array([0.0, 5.0]),
            n1=1.5,  # Glass
            n2=1.0   # Air
        )
        
        # Ray at steep angle (beyond critical angle)
        # Critical angle for 1.5→1.0 is arcsin(1.0/1.5) ≈ 41.8°
        # Use 60° (beyond critical)
        angle = math.radians(60)
        ray = RayState(
            position=np.array([-1.0, 0.0]),
            direction=np.array([math.cos(angle), math.sin(angle)]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0, 0.0])
        tangent = np.array([0.0, 1.0])
        
        output_rays = interface.interact(ray, hit_point, normal, tangent)
        
        # Should have only reflected ray (total internal reflection)
        # No transmitted ray
        assert len(output_rays) == 1  # Only reflection
        reflected = output_rays[0]
        assert reflected.intensity > 0.99  # Almost all light reflected


class TestBeamsplitterElement:
    """Test BeamsplitterElement implementation"""
    
    def test_create_beamsplitter(self):
        """Test creating a beamsplitter"""
        from optiverse.raytracing.elements import BeamsplitterElement
        
        bs = BeamsplitterElement(
            p1=np.array([-10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            transmission=0.5,
            reflection=0.5
        )
        
        p1, p2 = bs.get_geometry()
        assert np.array_equal(p1, np.array([-10.0, -10.0]))
    
    def test_beamsplitter_splits_ray(self):
        """Test beamsplitter creates two rays"""
        from optiverse.raytracing.elements import BeamsplitterElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # 50/50 beamsplitter
        bs = BeamsplitterElement(
            p1=np.array([-10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            transmission=0.5,
            reflection=0.5
        )
        
        ray = RayState(
            position=np.array([-5.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0/np.sqrt(2), 1.0/np.sqrt(2)])  # 45°
        tangent = np.array([-1.0/np.sqrt(2), 1.0/np.sqrt(2)])
        
        output_rays = bs.interact(ray, hit_point, normal, tangent)
        
        # Should have 2 rays: transmitted and reflected
        assert len(output_rays) == 2
        
        # Check intensities sum to ≤ original (accounting for loss)
        total_intensity = sum(r.intensity for r in output_rays)
        assert total_intensity <= 1.0
        assert total_intensity >= 0.9  # Minimal loss


class TestWaveplateElement:
    """Test WaveplateElement implementation"""
    
    def test_create_waveplate(self):
        """Test creating a waveplate"""
        from optiverse.raytracing.elements import WaveplateElement
        
        qwp = WaveplateElement(
            p1=np.array([0.0, -15.0]),
            p2=np.array([0.0, 15.0]),
            phase_shift_deg=90.0,
            fast_axis_deg=45.0
        )
        
        p1, p2 = qwp.get_geometry()
        assert np.array_equal(p1, np.array([0.0, -15.0]))
    
    def test_qwp_converts_linear_to_circular(self):
        """Test QWP at 45° converts horizontal linear to circular"""
        from optiverse.raytracing.elements import WaveplateElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # Quarter waveplate at 45°
        qwp = WaveplateElement(
            p1=np.array([0.0, -15.0]),
            p2=np.array([0.0, 15.0]),
            phase_shift_deg=90.0,
            fast_axis_deg=45.0
        )
        
        # Horizontal linear polarization
        ray = RayState(
            position=np.array([-5.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=633.0,
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0, 0.0])
        tangent = np.array([0.0, 1.0])
        
        output_rays = qwp.interact(ray, hit_point, normal, tangent)
        
        # Should have one output ray
        assert len(output_rays) == 1
        
        out_ray = output_rays[0]
        # Check polarization changed (should be circular)
        # Right circular: [1, i]/√2
        jones = out_ray.polarization.jones_vector
        # Check for circular character: |Ex| ≈ |Ey| and 90° phase difference
        assert np.isclose(abs(jones[0]), abs(jones[1]), atol=0.1)


class TestDichroicElement:
    """Test DichroicElement implementation"""
    
    def test_create_dichroic(self):
        """Test creating a dichroic mirror"""
        from optiverse.raytracing.elements import DichroicElement
        
        dichroic = DichroicElement(
            p1=np.array([-10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            cutoff_wavelength_nm=550.0,
            transition_width_nm=50.0,
            pass_type="longpass"
        )
        
        p1, p2 = dichroic.get_geometry()
        assert np.array_equal(p1, np.array([-10.0, -10.0]))
    
    def test_dichroic_reflects_short_wavelength(self):
        """Test longpass dichroic reflects short wavelengths"""
        from optiverse.raytracing.elements import DichroicElement
        from optiverse.raytracing.ray import RayState, Polarization
        
        # 550nm longpass dichroic
        dichroic = DichroicElement(
            p1=np.array([-10.0, -10.0]),
            p2=np.array([10.0, 10.0]),
            cutoff_wavelength_nm=550.0,
            transition_width_nm=50.0,
            pass_type="longpass"
        )
        
        # 488nm ray (blue, < 550nm)
        ray = RayState(
            position=np.array([-5.0, 0.0]),
            direction=np.array([1.0, 0.0]),
            intensity=1.0,
            polarization=Polarization.horizontal(),
            wavelength_nm=488.0,  # Blue
            path=[],
            events=0
        )
        
        hit_point = np.array([0.0, 0.0])
        normal = np.array([1.0/np.sqrt(2), 1.0/np.sqrt(2)])
        tangent = np.array([-1.0/np.sqrt(2), 1.0/np.sqrt(2)])
        
        output_rays = dichroic.interact(ray, hit_point, normal, tangent)
        
        # Should have transmitted and reflected
        assert len(output_rays) == 2
        
        # Reflected should be stronger for short wavelength
        reflected = [r for r in output_rays if np.dot(r.direction, normal) < 0][0]
        transmitted = [r for r in output_rays if np.dot(r.direction, normal) > 0][0]
        
        assert reflected.intensity > transmitted.intensity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

