import os


def test_platform_paths_exposes_core_dirs(tmp_path, monkeypatch):
    # Force HOME to tmp so paths resolve under it for the test
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows

    from optiverse.platform.paths import library_root_dir, assets_dir, get_library_path

    root = library_root_dir()
    assets = assets_dir()
    lib = get_library_path()

    assert os.path.isdir(root)
    assert os.path.isdir(assets)
    assert os.path.dirname(lib) == root


