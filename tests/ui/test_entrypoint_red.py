def test_app_entry_imports():
    # Import should succeed and expose a main() callable
    from optiverse.app.main import main

    assert callable(main)
