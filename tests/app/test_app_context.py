def test_app_context_create_default():
    from optiverse.app.app_context import AppContext

    ctx = AppContext.create_default()
    assert ctx.settings is not None
    assert ctx.storage is not None
