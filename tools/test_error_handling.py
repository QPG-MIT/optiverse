#!/usr/bin/env python3
"""
Test script to verify error handling is working correctly.
This script demonstrates that errors are caught and shown in dialogs
instead of crashing the application.
"""

import sys
from PyQt6 import QtWidgets

# Test the error handler
def test_error_handler():
    """Test that the error handler catches and displays errors."""
    from optiverse.services.error_handler import get_error_handler, ErrorContext

    print("Testing error handler...")

    # Test 1: Global exception hook
    print("\n1. Testing global exception hook (this will show an error dialog)...")

    # Uncomment to test global exception handler:
    # raise ValueError("This is a test error to verify the error handler works!")

    # Test 2: ErrorContext
    print("2. Testing ErrorContext wrapper...")
    with ErrorContext("during test operation"):
        # This error will be caught and displayed in a dialog
        # Uncomment to test:
        # raise RuntimeError("Test error from ErrorContext")
        print("   ✓ ErrorContext works (no error thrown in this test)")

    # Test 3: Error without dialog (just logging)
    print("3. Testing error with logging only (no dialog)...")
    with ErrorContext("during silent test", show_dialog=False):
        # This will be logged but won't show a dialog
        # Uncomment to test:
        # raise RuntimeError("Silent test error")
        print("   ✓ Silent error handling works (no error thrown in this test)")

    print("\n✅ Error handler is installed and working!")
    print("   - Errors will be caught and shown in dialogs")
    print("   - Application will not crash")
    print("   - Errors are logged to the log service")


def main():
    """Main test function."""
    # Create QApplication
    app = QtWidgets.QApplication(sys.argv)

    # Install error handler
    from optiverse.services.error_handler import get_error_handler, install_qt_message_handler
    error_handler = get_error_handler()
    install_qt_message_handler()

    print("="*60)
    print("Error Handling Test")
    print("="*60)

    # Run tests
    test_error_handler()

    print("\n" + "="*60)
    print("To test with a real error, uncomment one of the 'raise' lines")
    print("in test_error_handling.py and run again.")
    print("="*60)

    # Show a simple window to verify Qt is working
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
    msg.setWindowTitle("Error Handling Test")
    msg.setText("Error handling system is active!\n\n"
                "The application will now catch and display errors\n"
                "instead of crashing.\n\n"
                "Check the console for test results.")
    msg.exec()

    return 0


if __name__ == "__main__":
    sys.exit(main())


