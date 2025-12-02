def test_settings_roundtrip(qtbot, monkeypatch, tmp_path):
    # configure QSettings to use a temp location
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from optiverse.services.settings_service import SettingsService

    s = SettingsService(organization="PhotonicSandbox", application="PhotonicSandboxTest")
    s.set_value("ui/ray_width_px", 2.5)
    assert s.get_value("ui/ray_width_px", 0.0) == 2.5
