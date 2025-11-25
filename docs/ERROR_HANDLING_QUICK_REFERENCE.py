"""
Quick reference for using the error handling system in Optiverse.

IMPORT:
    from optiverse.services.error_handler import ErrorContext, handle_errors, get_error_handler

BASIC USAGE - Context Manager (Recommended):

    # With error dialog (user-facing operations)
    with ErrorContext("while saving file"):
        save_to_disk(data)

    # Silent mode (background/auto operations)
    with ErrorContext("during auto-retrace", show_dialog=False):
        self.retrace()

DECORATOR USAGE:

    @handle_errors
    def my_function(self):
        risky_operation()

MANUAL ERROR HANDLING:

    try:
        risky_operation()
    except Exception as e:
        get_error_handler().handle_error(e, "while doing something")

WHEN TO USE:

    ✅ File I/O operations
    ✅ Network operations
    ✅ Complex computations
    ✅ User-initiated actions
    ✅ Drag-and-drop handling

    ❌ Simple getters/setters
    ❌ Already wrapped in try/except
    ❌ Performance-critical tight loops

SILENT MODE - Use for:

    ✅ Auto-retrace operations
    ✅ Background processing
    ✅ Rapid repeated operations
    ✅ Non-critical failures

    ❌ User-initiated actions
    ❌ File save/load
    ❌ Critical operations

EXAMPLES FROM CODEBASE:

    # Save operation (show dialog)
    def save_assembly(self):
        with ErrorContext("while saving assembly"):
            self._save_to_file(path)

    # Raytracing (silent - no dialog spam)
    def _do_retrace(self):
        with ErrorContext("while raytracing", show_dialog=False):
            self.retrace()

    # Drag-and-drop (silent - user sees visual feedback)
    def dropEvent(self, e):
        with ErrorContext("while dropping component", show_dialog=False):
            self.parent().on_drop_component(rec, scene_pos)

ERROR MESSAGES:

    # Be specific and user-friendly
    ✅ "while saving assembly"
    ✅ "during component export"
    ✅ "while loading Zemax file"

    ❌ "in function"
    ❌ "error"
    ❌ "operation failed"

TESTING:

    # Test that error handling works
    python test_error_handling.py

    # View error logs in app
    Help → Show Logs → Filter: "Error Handler"

TROUBLESHOOTING:

    Q: Error dialogs not showing?
    A: Check if show_dialog=False is set

    Q: App still crashing?
    A: Error might be in error handler itself - check logs

    Q: Too many error dialogs?
    A: Use silent mode for rapid operations

    Q: Error not logged?
    A: Make sure error handler is installed (app/main.py)

PERFORMANCE:

    - Negligible overhead (<1µs per context)
    - Only activates when exceptions occur
    - Safe for hot paths (but prefer silent mode)

MORE INFO:

    See docs/ERROR_HANDLING.md for complete documentation
"""
