"""
Factory functions for creating realistic beam splitter cube components.

A beam splitter cube is a composite optical element consisting of:
- 4 external glass-air interfaces (with Fresnel reflections)
- 1 internal beam splitter coating interface
- Glass refractive index typically n=1.5 (BK7 glass)

The cube handles:
- Path length changes through glass (affecting beam position)
- Surface reflections at all interfaces (Fresnel equations)
- Beam splitting at the diagonal coating
- Refraction at all air-glass boundaries (Snell's law)
"""

from ...core.models import RefractiveObjectParams, RefractiveInterface
from typing import Optional


def create_beamsplitter_cube_50_50(
    size_mm: float = 25.4,  # 1 inch cube
    center_x: float = 0.0,
    center_y: float = 0.0,
    rotation_deg: float = 45.0,
    n_glass: float = 1.517,  # BK7 glass at 589nm
    split_ratio: float = 50.0,  # 50/50 split
    is_polarizing: bool = False,
    pbs_axis_deg: float = 0.0,
    image_path: Optional[str] = None,
    name: Optional[str] = None
) -> RefractiveObjectParams:
    """
    Create a realistic beam splitter cube with proper refraction.
    
    The cube is oriented at rotation_deg (typically 45°) with the beam splitter
    coating running diagonally from bottom-left to top-right in local coordinates.
    
    Coordinate system (local, before rotation):
    - The cube extends from -size_mm/2 to +size_mm/2 in both x and y
    - The diagonal coating goes from (-size/2, -size/2) to (+size/2, +size/2)
    - Four edges: left, bottom, right, top
    
    Args:
        size_mm: Side length of the cube in mm
        center_x: X position of cube center
        center_y: Y position of cube center
        rotation_deg: Rotation angle in degrees (45° typical for BS)
        n_glass: Refractive index of glass (1.517 for BK7)
        split_ratio: Transmission percentage (50.0 for 50/50)
        is_polarizing: True for PBS mode
        pbs_axis_deg: PBS transmission axis angle (absolute, in lab frame)
        image_path: Optional path to cube image
        name: Optional component name
    
    Returns:
        RefractiveObjectParams with 5 interfaces configured
    """
    half_size = size_mm / 2.0
    
    interfaces = []
    
    # Interface 1: Left edge (entrance surface for horizontal beam from left)
    # Air (n=1.0) -> Glass (n=n_glass)
    interfaces.append(RefractiveInterface(
        x1_mm=-half_size, y1_mm=-half_size,
        x2_mm=-half_size, y2_mm=+half_size,
        n1=1.0,  # Air
        n2=n_glass,  # Glass
        is_beam_splitter=False
    ))
    
    # Interface 2: Bottom edge (entrance surface for vertical beam from below)
    # Air (n=1.0) -> Glass (n=n_glass)
    interfaces.append(RefractiveInterface(
        x1_mm=-half_size, y1_mm=-half_size,
        x2_mm=+half_size, y2_mm=-half_size,
        n1=1.0,  # Air
        n2=n_glass,  # Glass
        is_beam_splitter=False
    ))
    
    # Interface 3: Diagonal beam splitter coating (runs from bottom-left to top-right)
    # Glass (n=n_glass) on both sides, but with beam splitting coating
    interfaces.append(RefractiveInterface(
        x1_mm=-half_size, y1_mm=-half_size,
        x2_mm=+half_size, y2_mm=+half_size,
        n1=n_glass,  # Glass on both sides
        n2=n_glass,
        is_beam_splitter=True,
        split_T=split_ratio,
        split_R=100.0 - split_ratio,
        is_polarizing=is_polarizing,
        pbs_transmission_axis_deg=pbs_axis_deg
    ))
    
    # Interface 4: Right edge (exit surface for transmitted beam)
    # Glass (n=n_glass) -> Air (n=1.0)
    interfaces.append(RefractiveInterface(
        x1_mm=+half_size, y1_mm=-half_size,
        x2_mm=+half_size, y2_mm=+half_size,
        n1=n_glass,  # Glass
        n2=1.0,  # Air
        is_beam_splitter=False
    ))
    
    # Interface 5: Top edge (exit surface for reflected beam)
    # Glass (n=n_glass) -> Air (n=1.0)
    interfaces.append(RefractiveInterface(
        x1_mm=-half_size, y1_mm=+half_size,
        x2_mm=+half_size, y2_mm=+half_size,
        n1=n_glass,  # Glass
        n2=1.0,  # Air
        is_beam_splitter=False
    ))
    
    return RefractiveObjectParams(
        x_mm=center_x,
        y_mm=center_y,
        angle_deg=rotation_deg,
        object_height_mm=size_mm * 1.414,  # Diagonal length for rendering bounds
        interfaces=interfaces,
        image_path=image_path,
        name=name or f"BS Cube {int(split_ratio)}/{int(100-split_ratio)}"
    )


def create_pbs_cube(
    size_mm: float = 50.8,  # 2 inch cube
    center_x: float = 0.0,
    center_y: float = 0.0,
    rotation_deg: float = 45.0,
    pbs_axis_deg: float = 0.0,  # Horizontal transmission axis
    n_glass: float = 1.517,
    image_path: Optional[str] = None,
    name: Optional[str] = None
) -> RefractiveObjectParams:
    """
    Create a Polarizing Beam Splitter (PBS) cube.
    
    A PBS cube transmits p-polarization and reflects s-polarization.
    Otherwise identical to regular beam splitter cube.
    
    Args:
        size_mm: Side length of the cube in mm
        center_x: X position of cube center
        center_y: Y position of cube center  
        rotation_deg: Rotation angle in degrees (45° typical)
        pbs_axis_deg: Transmission axis angle in lab frame (0° = horizontal)
        n_glass: Refractive index of glass
        image_path: Optional path to cube image
        name: Optional component name
    
    Returns:
        RefractiveObjectParams configured as PBS
    """
    return create_beamsplitter_cube_50_50(
        size_mm=size_mm,
        center_x=center_x,
        center_y=center_y,
        rotation_deg=rotation_deg,
        n_glass=n_glass,
        split_ratio=50.0,  # Not used for PBS (intensity determined by polarization)
        is_polarizing=True,
        pbs_axis_deg=pbs_axis_deg,
        image_path=image_path,
        name=name or "PBS Cube"
    )


def create_prism(
    base_mm: float = 25.4,
    height_mm: float = 25.4,
    center_x: float = 0.0,
    center_y: float = 0.0,
    rotation_deg: float = 0.0,
    n_glass: float = 1.517,
    image_path: Optional[str] = None,
    name: Optional[str] = None
) -> RefractiveObjectParams:
    """
    Create a simple triangular prism (45-45-90 triangle).
    
    Useful for demonstrating dispersion and refraction effects.
    
    Args:
        base_mm: Base width of triangle
        height_mm: Height of triangle
        center_x: X position
        center_y: Y position
        rotation_deg: Rotation angle
        n_glass: Refractive index
        image_path: Optional image
        name: Optional name
    
    Returns:
        RefractiveObjectParams for prism
    """
    interfaces = []
    
    # Triangle vertices (centered at origin)
    half_base = base_mm / 2.0
    half_height = height_mm / 2.0
    
    # Bottom edge
    interfaces.append(RefractiveInterface(
        x1_mm=-half_base, y1_mm=-half_height,
        x2_mm=+half_base, y2_mm=-half_height,
        n1=1.0, n2=n_glass,
        is_beam_splitter=False
    ))
    
    # Right edge (hypotenuse)
    interfaces.append(RefractiveInterface(
        x1_mm=+half_base, y1_mm=-half_height,
        x2_mm=0.0, y2_mm=+half_height,
        n1=1.0, n2=n_glass,
        is_beam_splitter=False
    ))
    
    # Left edge (hypotenuse)
    interfaces.append(RefractiveInterface(
        x1_mm=0.0, y1_mm=+half_height,
        x2_mm=-half_base, y2_mm=-half_height,
        n1=1.0, n2=n_glass,
        is_beam_splitter=False
    ))
    
    return RefractiveObjectParams(
        x_mm=center_x,
        y_mm=center_y,
        angle_deg=rotation_deg,
        object_height_mm=max(base_mm, height_mm),
        interfaces=interfaces,
        image_path=image_path,
        name=name or "Prism"
    )

