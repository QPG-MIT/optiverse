#!/usr/bin/env python3
"""
Qt WebSocket test client.

Tests if Qt's QWebSocket can connect to the minimal server and stay connected.
Run this after starting test_minimal_server.py.
"""
import sys
from PyQt6.QtCore import QCoreApplication, QUrl, QTimer
from PyQt6.QtWebSockets import QWebSocket


class TestClient:
    """Simple test client for WebSocket connection."""
    
    def __init__(self):
        self.ws = QWebSocket()
        self.message_count = 0
        self.connected = False
        
        # Connect signals
        self.ws.connected.connect(self.on_connected)
        self.ws.disconnected.connect(self.on_disconnected)
        self.ws.textMessageReceived.connect(self.on_message)
        self.ws.errorOccurred.connect(self.on_error)
        
        # Timer to send test messages
        self.timer = QTimer()
        self.timer.timeout.connect(self.send_test_message)
        self.timer.setInterval(5000)  # Every 5 seconds
    
    def connect_to_server(self, url: str):
        """Connect to the test server."""
        print(f"→ Connecting to: {url}")
        self.ws.open(QUrl(url))
    
    def on_connected(self):
        """Called when connected."""
        self.connected = True
        print("✓ CONNECTED")
        print(f"  State: {self.ws.state()}")
        print(f"  Valid: {self.ws.isValid()}")
        print("  Starting to send test messages every 5 seconds...")
        self.timer.start()
        self.send_test_message()
    
    def on_disconnected(self):
        """Called when disconnected."""
        self.connected = False
        self.timer.stop()
        
        close_code = self.ws.closeCode()
        close_reason = self.ws.closeReason()
        
        print("✗ DISCONNECTED")
        print(f"  Close code: {close_code} ({int(close_code)})")
        print(f"  Close reason: {close_reason}")
        print(f"  Messages sent before disconnect: {self.message_count}")
        
        # Exit after disconnect
        QCoreApplication.quit()
    
    def on_message(self, message: str):
        """Called when message received."""
        print(f"← Received: {message[:80]}")
    
    def on_error(self, error_code):
        """Called on error."""
        error_str = self.ws.errorString()
        print(f"✗ ERROR: ({error_code}) {error_str}")
    
    def send_test_message(self):
        """Send a test message."""
        if self.connected:
            self.message_count += 1
            message = f"Test message #{self.message_count}"
            print(f"→ Sending: {message}")
            self.ws.sendTextMessage(message)


def main():
    """Run the test client."""
    app = QCoreApplication(sys.argv)
    
    print("=" * 60)
    print("QT WEBSOCKET TEST CLIENT")
    print("=" * 60)
    print("Make sure test_minimal_server.py is running first!")
    print("=" * 60)
    
    client = TestClient()
    client.connect_to_server("ws://localhost:8765")
    
    print("\nTest: Connection should stay alive and messages should echo back")
    print("If it disconnects immediately, there's a protocol issue")
    print("Press Ctrl+C to stop\n")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

