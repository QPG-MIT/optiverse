#!/usr/bin/env python3
"""
Comprehensive collaboration server test.

Tests the full workflow:
1. Server starts and listens
2. Client connects and stays connected
3. Messages are exchanged
4. Server cleans up properly
"""
import sys
import time
import subprocess
import signal
from PyQt6.QtCore import QCoreApplication, QUrl, QTimer
from PyQt6.QtWebSockets import QWebSocket


class CollaborationTest:
    """Test harness for collaboration server."""

    def __init__(self):
        self.ws = QWebSocket()
        self.connected = False
        self.messages_received = []
        self.test_passed = False

        # Connect signals
        self.ws.connected.connect(self.on_connected)
        self.ws.disconnected.connect(self.on_disconnected)
        self.ws.textMessageReceived.connect(self.on_message)
        self.ws.errorOccurred.connect(self.on_error)

        # Test timeout
        self.timeout_timer = QTimer()
        self.timeout_timer.timeout.connect(self.on_timeout)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.setInterval(30000)  # 30 second timeout

        # Heartbeat timer
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        self.heartbeat_timer.setInterval(5000)  # Every 5 seconds

    def start_test(self, url: str):
        """Start the test."""
        print("=" * 70)
        print("COLLABORATION SERVER TEST")
        print("=" * 70)
        print(f"Test: Connect to {url}")
        print("Expected: Connection stays alive for at least 15 seconds")
        print("=" * 70)

        self.timeout_timer.start()
        self.ws.open(QUrl(url))

        # Schedule success check after 15 seconds
        QTimer.singleShot(15000, self.check_success)

    def on_connected(self):
        """Called when connected."""
        self.connected = True
        print("\n✓ TEST STEP 1: CONNECTED")
        print(f"  State: {self.ws.state()}")
        print(f"  Valid: {self.ws.isValid()}")

        # Start heartbeat
        self.heartbeat_timer.start()

        # Send initial message
        self.send_heartbeat()

    def on_disconnected(self):
        """Called when disconnected."""
        self.connected = False
        self.heartbeat_timer.stop()

        close_code_enum = self.ws.closeCode()
        close_reason = self.ws.closeReason()

        # Convert enum to int
        try:
            close_code = int(close_code_enum)
        except (ValueError, TypeError):
            close_code = 0

        print("\n✗ TEST FAILED: DISCONNECTED UNEXPECTEDLY")
        print(f"  Close code: {close_code} ({close_code_enum})")
        print(f"  Close reason: {close_reason}")
        print(f"  Messages received: {len(self.messages_received)}")

        self.test_passed = False
        QCoreApplication.quit()

    def on_message(self, message: str):
        """Called when message received."""
        self.messages_received.append(message)
        print(f"\n✓ TEST STEP 2: MESSAGE RECEIVED")
        print(f"  Message: {message[:100]}")
        print(f"  Total messages: {len(self.messages_received)}")

    def on_error(self, error_code):
        """Called on error."""
        error_str = self.ws.errorString()
        print(f"\n✗ TEST FAILED: ERROR")
        print(f"  Code: {error_code}")
        print(f"  Error: {error_str}")

        self.test_passed = False
        QCoreApplication.quit()

    def send_heartbeat(self):
        """Send heartbeat ping."""
        if self.connected:
            import json
            message = json.dumps({"type": "ping"})
            self.ws.sendTextMessage(message)
            print(f"\n→ Sent heartbeat ping")

    def check_success(self):
        """Check if test passed after 15 seconds."""
        if self.connected and len(self.messages_received) >= 2:
            print("\n" + "=" * 70)
            print("✓ TEST PASSED")
            print("=" * 70)
            print(f"Connection stayed alive for 15+ seconds")
            print(f"Messages received: {len(self.messages_received)}")
            print(f"Connection state: {self.ws.state()}")
            print("=" * 70)

            self.test_passed = True

            # Disconnect cleanly
            print("\nClosing connection...")
            self.ws.close()

            # Exit after a moment
            QTimer.singleShot(1000, QCoreApplication.quit)
        else:
            print("\n" + "=" * 70)
            print("✗ TEST FAILED")
            print("=" * 70)
            if not self.connected:
                print("Reason: Connection was lost")
            else:
                print(f"Reason: Not enough messages ({len(self.messages_received)} < 2)")
            print("=" * 70)

            self.test_passed = False
            QCoreApplication.quit()

    def on_timeout(self):
        """Called if test times out."""
        print("\n" + "=" * 70)
        print("✗ TEST TIMEOUT")
        print("=" * 70)
        print("Test did not complete in 30 seconds")
        print("=" * 70)

        self.test_passed = False
        if self.ws.isValid():
            self.ws.close()
        QCoreApplication.quit()


def main():
    """Run the test."""
    app = QCoreApplication(sys.argv)

    print("\n" + "=" * 70)
    print("STARTING COLLABORATION SERVER TEST")
    print("=" * 70)
    print("This test will:")
    print("  1. Connect to the collaboration server")
    print("  2. Send periodic heartbeat messages")
    print("  3. Verify connection stays alive for 15+ seconds")
    print("  4. Check that messages are received")
    print("\nMake sure collaboration_server_v2.py is running first!")
    print("=" * 70)

    # Give user time to read
    time.sleep(2)

    test = CollaborationTest()
    test.start_test("ws://localhost:8765/ws/test_session/test_user")

    exit_code = app.exec()

    # Return appropriate exit code
    if test.test_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())



