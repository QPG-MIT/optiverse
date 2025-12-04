#!/usr/bin/env python
"""
Performance Benchmark: Polymorphic Raytracing Engine

This script benchmarks the polymorphic raytracing engine with and without
parallel processing to measure the performance benefits.

Usage:
    python benchmark_raytracing.py

    Or with specific parameters:
    python benchmark_raytracing.py --elements 100 --rays 50 --iterations 10
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optiverse.core.models import SourceParams
from optiverse.data import (
    BeamsplitterProperties,
    LensProperties,
    LineSegment,
    MirrorProperties,
    OpticalInterface,
)
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing import trace_rays_polymorphic


def create_test_scene(num_elements: int) -> list:
    """
    Create a test scene with specified number of elements.

    Args:
        num_elements: Number of optical elements to create

    Returns:
        List of polymorphic elements
    """
    poly_elements = []

    # Mix of different element types
    element_types = ["mirror", "lens", "beamsplitter"]

    for i in range(num_elements):
        x = 50.0 + i * 10.0
        element_type = element_types[i % len(element_types)]

        if element_type == "mirror":
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = MirrorProperties(reflectivity=1.0)
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

        elif element_type == "lens":
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = LensProperties(efl_mm=100.0)
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

        elif element_type == "beamsplitter":
            geom = LineSegment(np.array([x, -20.0]), np.array([x, 20.0]))
            props = BeamsplitterProperties(
                transmission=0.7, reflection=0.3, is_polarizing=False, polarization_axis_deg=0.0
            )
            iface = OpticalInterface(geometry=geom, properties=props)
            poly_elem = create_polymorphic_element(iface)
            poly_elements.append(poly_elem)

    return poly_elements


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
        polarization_type="horizontal",
    )


def benchmark_sequential(elements: list, source: SourceParams, iterations: int = 10) -> tuple[float, int]:
    """
    Benchmark the polymorphic raytracing engine in sequential mode.

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
        paths = trace_rays_polymorphic(elements, [source], max_events=80, parallel=False)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms
        total_paths = len(paths)

    avg_time = np.mean(times)
    return avg_time, total_paths


def benchmark_parallel(elements: list, source: SourceParams, iterations: int = 10) -> tuple[float, int]:
    """
    Benchmark the polymorphic raytracing engine in parallel mode.

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
        paths = trace_rays_polymorphic(
            elements, [source], max_events=80, parallel=True, parallel_threshold=1
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms
        total_paths = len(paths)

    avg_time = np.mean(times)
    return avg_time, total_paths


def run_benchmark(num_elements: int, num_rays: int, iterations: int = 10):
    """
    Run a complete benchmark comparing sequential and parallel modes.

    Args:
        num_elements: Number of optical elements in the scene
        num_rays: Number of rays from the source
        iterations: Number of iterations to average over
    """
    print(f"\n{'=' * 80}")
    print(f"BENCHMARK: {num_elements} elements, {num_rays} rays, {iterations} iterations")
    print(f"{'=' * 80}\n")

    # Create test scene
    print("Creating test scene...")
    poly_elements = create_test_scene(num_elements)
    source = create_test_source(num_rays)

    # Benchmark sequential
    print("\nBenchmarking SEQUENTIAL mode...")
    seq_time, seq_paths = benchmark_sequential(poly_elements, source, iterations)
    print(f"  Average time: {seq_time:.2f} ms")
    print(f"  Total paths: {seq_paths}")

    # Benchmark parallel
    print("\nBenchmarking PARALLEL mode...")
    par_time, par_paths = benchmark_parallel(poly_elements, source, iterations)
    print(f"  Average time: {par_time:.2f} ms")
    print(f"  Total paths: {par_paths}")

    # Calculate speedup
    speedup = seq_time / par_time if par_time > 0 else 0
    improvement_pct = ((seq_time - par_time) / seq_time * 100) if seq_time > 0 else 0

    # Results
    print(f"\n{'=' * 80}")
    print("RESULTS:")
    print(f"{'=' * 80}")
    print(f"  Sequential time:   {seq_time:.2f} ms")
    print(f"  Parallel time:     {par_time:.2f} ms")
    print(f"  Speedup:           {speedup:.2f}x")
    print(f"  Improvement:       {improvement_pct:.1f}%")
    print(f"  Path count match:  {'✓' if seq_paths == par_paths else '✗'}")
    print(f"{'=' * 80}\n")

    return {
        "num_elements": num_elements,
        "num_rays": num_rays,
        "seq_time_ms": seq_time,
        "par_time_ms": par_time,
        "speedup": speedup,
        "improvement_pct": improvement_pct,
        "seq_paths": seq_paths,
        "par_paths": par_paths,
    }


def run_scaling_benchmark():
    """
    Run benchmarks with increasing scene complexity to test scaling.
    """
    print(f"\n{'#' * 80}")
    print("SCALING BENCHMARK: Testing with increasing ray counts")
    print(f"{'#' * 80}\n")

    results = []

    # Test with different numbers of rays (parallel benefits show with more rays)
    ray_counts = [10, 25, 50, 100, 200]
    element_count = 30
    iterations = 5

    for num_rays in ray_counts:
        result = run_benchmark(element_count, num_rays, iterations)
        results.append(result)

    # Summary table
    print(f"\n{'=' * 80}")
    print("SCALING SUMMARY:")
    print(f"{'=' * 80}")
    print(f"{'Elements':<12} {'Rays':<8} {'Sequential (ms)':<18} {'Parallel (ms)':<18} {'Speedup':<10}")
    print(f"{'-' * 80}")

    for r in results:
        print(
            f"{r['num_elements']:<12} {r['num_rays']:<8} "
            f"{r['seq_time_ms']:<18.2f} {r['par_time_ms']:<18.2f} "
            f"{r['speedup']:<10.2f}x"
        )

    print(f"{'=' * 80}\n")

    # Average speedup
    avg_speedup = np.mean([r["speedup"] for r in results])
    print(f"Average speedup across all tests: {avg_speedup:.2f}x\n")


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark polymorphic raytracing engine (sequential vs parallel)"
    )
    parser.add_argument(
        "--elements", type=int, default=50, help="Number of optical elements (default: 50)"
    )
    parser.add_argument(
        "--rays", type=int, default=50, help="Number of rays from source (default: 50)"
    )
    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of iterations to average (default: 10)"
    )
    parser.add_argument(
        "--scaling", action="store_true", help="Run scaling benchmark with multiple ray counts"
    )

    args = parser.parse_args()

    print(f"\n{'#' * 80}")
    print("POLYMORPHIC RAYTRACING PERFORMANCE BENCHMARK")
    print("Comparing Sequential vs Parallel Processing")
    print(f"{'#' * 80}\n")

    if args.scaling:
        run_scaling_benchmark()
    else:
        run_benchmark(args.elements, args.rays, args.iterations)

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
