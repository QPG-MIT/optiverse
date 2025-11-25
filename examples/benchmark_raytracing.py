#!/usr/bin/env python
"""
Performance Benchmark: Legacy vs Polymorphic Raytracing

This script benchmarks the performance difference between the legacy
and new polymorphic raytracing engines.

Usage:
    python benchmark_raytracing.py

    Or with specific parameters:
    python benchmark_raytracing.py --elements 100 --rays 50 --iterations 10
"""
import argparse
import time
import numpy as np
from typing import List, Tuple
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from optiverse.core.models import SourceParams, OpticalElement
from optiverse.core.use_cases import trace_rays as trace_rays_legacy
from optiverse.raytracing import trace_rays_polymorphic
from optiverse.data import OpticalInterface, LineSegment, LensProperties, MirrorProperties, BeamsplitterProperties
from optiverse.integration import create_polymorphic_element


def create_test_scene(num_elements: int) -> Tuple[List[OpticalElement], List]:
    """
    Create a test scene with specified number of elements.

    Args:
        num_elements: Number of optical elements to create

    Returns:
        Tuple of (legacy_elements, polymorphic_elements)
    """
    legacy_elements = []
    poly_elements = []

    # Mix of different element types
    element_types = ['mirror', 'lens', 'beamsplitter']

    for i in range(num_elements):
        x = 50.0 + i * 10.0
        element_type = element_types[i % len(element_types)]

        if element_type == 'mirror':
            # Legacy
            legacy_elem = OpticalElement(
                kind="mirror",
                p1=np.array([x, -20.0]),
                p2=np.array([x, 20.0])
            )
            legacy_elements.append(legacy_elem)

            # Polymorphic
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = MirrorProperties(reflectivity=99.0)
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

        elif element_type == 'lens':
            # Legacy
            legacy_elem = OpticalElement(
                kind="lens",
                p1=np.array([x, -20.0]),
                p2=np.array([x, 20.0]),
                efl_mm=100.0
            )
            legacy_elements.append(legacy_elem)

            # Polymorphic
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = LensProperties(efl_mm=100.0)
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

        elif element_type == 'beamsplitter':
            # Legacy
            legacy_elem = OpticalElement(
                kind="bs",
                p1=np.array([x, -20.0]),
                p2=np.array([x, 20.0]),
                split_T=70.0,
                split_R=30.0,
                is_polarizing=False,
                pbs_transmission_axis_deg=0.0
            )
            legacy_elements.append(legacy_elem)

            # Polymorphic
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = BeamsplitterProperties(split_T=70.0, split_R=30.0, is_polarizing=False)
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

    return legacy_elements, poly_elements


def create_test_source(num_rays: int) -> SourceParams:
    """
    Create a test source with specified number of rays.

    Args:
        num_rays: Number of rays to generate

    Returns:
        SourceParams object
    """
    return SourceParams(
        x_mm=0.0,
        y_mm=0.0,
        angle_deg=0.0,
        spread_deg=0.0,
        n_rays=num_rays,
        size_mm=20.0 if num_rays > 1 else 0.0,
        ray_length_mm=2000.0,  # Long enough to reach all elements
        wavelength_nm=633.0,
        color_hex="#FF0000",
        polarization_type="horizontal"
    )


def benchmark_legacy(elements: List[OpticalElement], source: SourceParams, iterations: int = 10) -> Tuple[float, int]:
    """
    Benchmark the legacy raytracing engine.

    Args:
        elements: List of OpticalElement objects
        source: Source parameters
        iterations: Number of iterations to run

    Returns:
        Tuple of (average_time_ms, total_paths)
    """
    times = []
    total_paths = 0

    for _ in range(iterations):
        start = time.perf_counter()
        paths = trace_rays_legacy(elements, [source], max_events=80)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms
        total_paths = len(paths)

    avg_time = np.mean(times)
    return avg_time, total_paths


def benchmark_polymorphic(elements: List, source: SourceParams, iterations: int = 10) -> Tuple[float, int]:
    """
    Benchmark the polymorphic raytracing engine.

    Args:
        elements: List of IOpticalElement objects
        source: Source parameters
        iterations: Number of iterations to run

    Returns:
        Tuple of (average_time_ms, total_paths)
    """
    times = []
    total_paths = 0

    for _ in range(iterations):
        start = time.perf_counter()
        paths = trace_rays_polymorphic(elements, [source], max_events=80)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms
        total_paths = len(paths)

    avg_time = np.mean(times)
    return avg_time, total_paths


def run_benchmark(num_elements: int, num_rays: int, iterations: int = 10):
    """
    Run a complete benchmark comparing legacy and polymorphic engines.

    Args:
        num_elements: Number of optical elements in the scene
        num_rays: Number of rays from the source
        iterations: Number of iterations to average over
    """
    print(f"\n{'='*80}")
    print(f"BENCHMARK: {num_elements} elements, {num_rays} rays, {iterations} iterations")
    print(f"{'='*80}\n")

    # Create test scene
    print("Creating test scene...")
    legacy_elements, poly_elements = create_test_scene(num_elements)
    source = create_test_source(num_rays)

    # Benchmark legacy
    print(f"\nBenchmarking LEGACY engine...")
    legacy_time, legacy_paths = benchmark_legacy(legacy_elements, source, iterations)
    print(f"  Average time: {legacy_time:.2f} ms")
    print(f"  Total paths: {legacy_paths}")

    # Benchmark polymorphic
    print(f"\nBenchmarking POLYMORPHIC engine...")
    poly_time, poly_paths = benchmark_polymorphic(poly_elements, source, iterations)
    print(f"  Average time: {poly_time:.2f} ms")
    print(f"  Total paths: {poly_paths}")

    # Calculate speedup
    speedup = legacy_time / poly_time if poly_time > 0 else 0
    improvement_pct = ((legacy_time - poly_time) / legacy_time * 100) if legacy_time > 0 else 0

    # Results
    print(f"\n{'='*80}")
    print(f"RESULTS:")
    print(f"{'='*80}")
    print(f"  Legacy time:       {legacy_time:.2f} ms")
    print(f"  Polymorphic time:  {poly_time:.2f} ms")
    print(f"  Speedup:           {speedup:.2f}x")
    print(f"  Improvement:       {improvement_pct:.1f}%")
    print(f"  Path count match:  {'✓' if legacy_paths == poly_paths else '✗'}")
    print(f"{'='*80}\n")

    return {
        'num_elements': num_elements,
        'num_rays': num_rays,
        'legacy_time_ms': legacy_time,
        'poly_time_ms': poly_time,
        'speedup': speedup,
        'improvement_pct': improvement_pct,
        'legacy_paths': legacy_paths,
        'poly_paths': poly_paths
    }


def run_scaling_benchmark():
    """
    Run benchmarks with increasing scene complexity to test scaling.
    """
    print(f"\n{'#'*80}")
    print(f"SCALING BENCHMARK: Testing with increasing scene complexity")
    print(f"{'#'*80}\n")

    results = []

    # Test with different numbers of elements
    element_counts = [10, 25, 50, 100]
    ray_count = 50
    iterations = 5

    for num_elements in element_counts:
        result = run_benchmark(num_elements, ray_count, iterations)
        results.append(result)

    # Summary table
    print(f"\n{'='*80}")
    print(f"SCALING SUMMARY:")
    print(f"{'='*80}")
    print(f"{'Elements':<12} {'Rays':<8} {'Legacy (ms)':<15} {'Poly (ms)':<15} {'Speedup':<10}")
    print(f"{'-'*80}")

    for r in results:
        print(f"{r['num_elements']:<12} {r['num_rays']:<8} "
              f"{r['legacy_time_ms']:<15.2f} {r['poly_time_ms']:<15.2f} "
              f"{r['speedup']:<10.2f}x")

    print(f"{'='*80}\n")

    # Average speedup
    avg_speedup = np.mean([r['speedup'] for r in results])
    print(f"Average speedup across all tests: {avg_speedup:.2f}x\n")


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark legacy vs polymorphic raytracing engines"
    )
    parser.add_argument(
        '--elements', type=int, default=50,
        help='Number of optical elements (default: 50)'
    )
    parser.add_argument(
        '--rays', type=int, default=50,
        help='Number of rays from source (default: 50)'
    )
    parser.add_argument(
        '--iterations', type=int, default=10,
        help='Number of iterations to average (default: 10)'
    )
    parser.add_argument(
        '--scaling', action='store_true',
        help='Run scaling benchmark with multiple scene sizes'
    )

    args = parser.parse_args()

    print(f"\n{'#'*80}")
    print(f"RAYTRACING PERFORMANCE BENCHMARK")
    print(f"Comparing Legacy vs Polymorphic Engines")
    print(f"{'#'*80}\n")

    if args.scaling:
        run_scaling_benchmark()
    else:
        run_benchmark(args.elements, args.rays, args.iterations)

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()



