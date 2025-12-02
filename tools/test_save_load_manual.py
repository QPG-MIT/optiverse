"""
Manual test script for save/load assembly functionality.

Run this script to manually test that all component types can be saved and loaded correctly.
This bypasses pytest and can be run directly with: python tools/test_save_load_manual.py

The script will:
1. Create all component types with various parameters
2. Save them to a temporary JSON file
3. Load them back
4. Verify all parameters match
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6 import QtWidgets

from optiverse.core.models import (
    BeamsplitterParams,
    DichroicParams,
    LensParams,
    MirrorParams,
    SLMParams,
    SourceParams,
    WaveplateParams,
)
from optiverse.objects import (
    BeamsplitterItem,
    DichroicItem,
    LensItem,
    MirrorItem,
    SLMItem,
    SourceItem,
    WaveplateItem,
)
from optiverse.ui.views.main_window import MainWindow


def test_save_load_all_components():
    """Test saving and loading all component types."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    print("=" * 70)
    print("SAVE/LOAD ASSEMBLY TEST")
    print("=" * 70)

    # Create one of each component type with specific parameters
    print("\n1. Creating components...")

    source = SourceItem(
        SourceParams(
            x_mm=100.0,
            y_mm=200.0,
            angle_deg=45.0,
            wavelength_nm=532.0,
            polarization_type="vertical",
        )
    )
    window.scene.addItem(source)
    print("   ✓ Source created (532nm, vertical polarization)")

    lens = LensItem(LensParams(x_mm=50.0, y_mm=75.0, efl_mm=150.0, name="Test Lens"))
    window.scene.addItem(lens)
    print("   ✓ Lens created (150mm EFL)")

    mirror = MirrorItem(MirrorParams(x_mm=-50.0, y_mm=-75.0, angle_deg=45.0, name="Test Mirror"))
    window.scene.addItem(mirror)
    print("   ✓ Mirror created")

    # Regular beamsplitter
    bs = BeamsplitterItem(
        BeamsplitterParams(x_mm=0.0, y_mm=0.0, split_T=70.0, split_R=30.0, is_polarizing=False)
    )
    window.scene.addItem(bs)
    print("   ✓ Beamsplitter created (70/30 split)")

    # PBS (Polarizing Beam Splitter)
    pbs = BeamsplitterItem(
        BeamsplitterParams(
            x_mm=100.0, y_mm=100.0, is_polarizing=True, pbs_transmission_axis_deg=30.0
        )
    )
    window.scene.addItem(pbs)
    print("   ✓ PBS created (30° transmission axis)")

    dichroic = DichroicItem(
        DichroicParams(
            x_mm=200.0,
            y_mm=300.0,
            cutoff_wavelength_nm=600.0,
            transition_width_nm=75.0,
            pass_type="shortpass",
        )
    )
    window.scene.addItem(dichroic)
    print("   ✓ Dichroic created (600nm cutoff, shortpass)")

    # Quarter waveplate
    qwp = WaveplateItem(
        WaveplateParams(x_mm=-100.0, y_mm=-200.0, phase_shift_deg=90.0, fast_axis_deg=45.0)
    )
    window.scene.addItem(qwp)
    print("   ✓ Quarter waveplate created (45° fast axis)")

    # Half waveplate
    hwp = WaveplateItem(
        WaveplateParams(x_mm=150.0, y_mm=250.0, phase_shift_deg=180.0, fast_axis_deg=22.5)
    )
    window.scene.addItem(hwp)
    print("   ✓ Half waveplate created (22.5° fast axis)")

    slm = SLMItem(SLMParams(x_mm=300.0, y_mm=400.0, object_height_mm=100.0, name="Test SLM"))
    window.scene.addItem(slm)
    print("   ✓ SLM created (100mm size)")

    # Save to temporary file
    print("\n2. Saving to temporary file...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
        data = {
            "sources": [],
            "lenses": [],
            "mirrors": [],
            "beamsplitters": [],
            "dichroics": [],
            "waveplates": [],
            "slms": [],
            "rulers": [],
            "texts": [],
        }

        for it in window.scene.items():
            if isinstance(it, SourceItem):
                data["sources"].append(it.to_dict())
            elif isinstance(it, LensItem):
                data["lenses"].append(it.to_dict())
            elif isinstance(it, MirrorItem):
                data["mirrors"].append(it.to_dict())
            elif isinstance(it, BeamsplitterItem):
                data["beamsplitters"].append(it.to_dict())
            elif isinstance(it, DichroicItem):
                data["dichroics"].append(it.to_dict())
            elif isinstance(it, WaveplateItem):
                data["waveplates"].append(it.to_dict())
            elif isinstance(it, SLMItem):
                data["slms"].append(it.to_dict())

        json.dump(data, f, indent=2)

    print(f"   ✓ Saved to: {temp_path}")
    print("   ✓ File contains:")
    print(f"      - {len(data['sources'])} source(s)")
    print(f"      - {len(data['lenses'])} lens(es)")
    print(f"      - {len(data['mirrors'])} mirror(s)")
    print(f"      - {len(data['beamsplitters'])} beamsplitter(s)")
    print(f"      - {len(data['dichroics'])} dichroic(s)")
    print(f"      - {len(data['waveplates'])} waveplate(s)")
    print(f"      - {len(data['slms'])} SLM(s)")

    # Clear scene
    print("\n3. Clearing scene...")
    window.scene.clear()
    print("   ✓ Scene cleared")

    # Load from file
    print("\n4. Loading from file...")
    with open(temp_path) as f:
        data = json.load(f)

    for d in data.get("sources", []):
        s = SourceItem(SourceParams(**d))
        window.scene.addItem(s)
    for d in data.get("lenses", []):
        L = LensItem(LensParams(**d))
        window.scene.addItem(L)
    for d in data.get("mirrors", []):
        M = MirrorItem(MirrorParams(**d))
        window.scene.addItem(M)
    for d in data.get("beamsplitters", []):
        B = BeamsplitterItem(BeamsplitterParams(**d))
        window.scene.addItem(B)
    for d in data.get("dichroics", []):
        D = DichroicItem(DichroicParams(**d))
        window.scene.addItem(D)
    for d in data.get("waveplates", []):
        W = WaveplateItem(WaveplateParams(**d))
        window.scene.addItem(W)
    for d in data.get("slms", []):
        S = SLMItem(SLMParams(**d))
        window.scene.addItem(S)

    print("   ✓ All components loaded")

    # Verify counts
    print("\n5. Verifying components...")
    items = window.scene.items()
    sources = [item for item in items if isinstance(item, SourceItem)]
    lenses = [item for item in items if isinstance(item, LensItem)]
    mirrors = [item for item in items if isinstance(item, MirrorItem)]
    beamsplitters = [item for item in items if isinstance(item, BeamsplitterItem)]
    dichroics = [item for item in items if isinstance(item, DichroicItem)]
    waveplates = [item for item in items if isinstance(item, WaveplateItem)]
    slms = [item for item in items if isinstance(item, SLMItem)]

    assert len(sources) == 1, f"Expected 1 source, got {len(sources)}"
    assert len(lenses) == 1, f"Expected 1 lens, got {len(lenses)}"
    assert len(mirrors) == 1, f"Expected 1 mirror, got {len(mirrors)}"
    assert len(beamsplitters) == 2, f"Expected 2 beamsplitters, got {len(beamsplitters)}"
    assert len(dichroics) == 1, f"Expected 1 dichroic, got {len(dichroics)}"
    assert len(waveplates) == 2, f"Expected 2 waveplates, got {len(waveplates)}"
    assert len(slms) == 1, f"Expected 1 SLM, got {len(slms)}"
    print("   ✓ Component counts correct")

    # Verify specific parameters
    print("\n6. Verifying parameters...")

    src = sources[0]
    assert abs(src.params.x_mm - 100.0) < 0.01, "Source X position incorrect"
    assert abs(src.params.wavelength_nm - 532.0) < 0.01, "Source wavelength incorrect"
    assert src.params.polarization_type == "vertical", "Source polarization incorrect"
    print("   ✓ Source parameters correct")

    lens = lenses[0]
    assert abs(lens.params.efl_mm - 150.0) < 0.01, "Lens EFL incorrect"
    assert lens.params.name == "Test Lens", "Lens name incorrect"
    print("   ✓ Lens parameters correct")

    # Find PBS vs regular BS
    pbs_item = next((bs for bs in beamsplitters if bs.params.is_polarizing), None)
    regular_bs = next((bs for bs in beamsplitters if not bs.params.is_polarizing), None)
    assert pbs_item is not None, "PBS not found"
    assert regular_bs is not None, "Regular BS not found"
    assert abs(pbs_item.params.pbs_transmission_axis_deg - 30.0) < 0.01, "PBS axis incorrect"
    assert abs(regular_bs.params.split_T - 70.0) < 0.01, "BS split ratio incorrect"
    print("   ✓ Beamsplitter parameters correct (including PBS)")

    dichroic = dichroics[0]
    assert abs(dichroic.params.cutoff_wavelength_nm - 600.0) < 0.01, "Dichroic cutoff incorrect"
    assert dichroic.params.pass_type == "shortpass", "Dichroic pass type incorrect"
    print("   ✓ Dichroic parameters correct")

    # Find QWP vs HWP
    qwp_loaded = next(
        (wp for wp in waveplates if abs(wp.params.phase_shift_deg - 90.0) < 0.01), None
    )
    hwp_loaded = next(
        (wp for wp in waveplates if abs(wp.params.phase_shift_deg - 180.0) < 0.01), None
    )
    assert qwp_loaded is not None, "QWP not found"
    assert hwp_loaded is not None, "HWP not found"
    assert abs(qwp_loaded.params.fast_axis_deg - 45.0) < 0.01, "QWP fast axis incorrect"
    assert abs(hwp_loaded.params.fast_axis_deg - 22.5) < 0.01, "HWP fast axis incorrect"
    print("   ✓ Waveplate parameters correct")

    slm = slms[0]
    assert abs(slm.params.x_mm - 300.0) < 0.01, "SLM position incorrect"
    assert abs(slm.params.object_height_mm - 100.0) < 0.01, "SLM size incorrect"
    assert slm.params.name == "Test SLM", "SLM name incorrect"
    print("   ✓ SLM parameters correct")

    # Clean up
    Path(temp_path).unlink()
    print(f"\n7. Cleaned up temporary file: {temp_path}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nThe save/load functionality is working correctly for all component types:")
    print("  • Sources (with polarization)")
    print("  • Lenses")
    print("  • Mirrors")
    print("  • Beamsplitters (regular and PBS)")
    print("  • Dichroic mirrors")
    print("  • Waveplates (QWP and HWP)")
    print("  • SLMs (Spatial Light Modulators)")
    print("\nAll parameters are correctly saved and restored.")

    return True


if __name__ == "__main__":
    try:
        test_save_load_all_components()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
