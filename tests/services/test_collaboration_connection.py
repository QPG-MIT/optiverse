"""
Test collaboration connection lifecycle to identify disconnect issue.

These tests require a running collaboration server at localhost:8765.
They are skipped on CI environments or when the server is not available.
"""

import os

import pytest
from PyQt6.QtTest import QTest

from optiverse.services.collaboration_service import CollaborationService

# Skip all tests in this module if we're on CI or server is not available
# CI environments typically set CI=true
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Collaboration server tests require a running server at localhost:8765",
)


class TestCollaborationConnection:
    """Test WebSocket connection lifecycle."""

    def test_websocket_stays_alive(self, qtbot):
        """Test that QWebSocket object persists after connection."""
        service = CollaborationService()

        # Track connection state changes
        connected_fired = []
        disconnected_fired = []

        service.connected.connect(lambda: connected_fired.append(True))
        service.disconnected.connect(lambda: disconnected_fired.append(True))

        # Store reference to ensure service doesn't get garbage collected

        # Connect
        service.set_server_url("ws://localhost:8765")
        service.connect_to_session("test", "test_user")

        # Wait for connection
        qtbot.waitUntil(lambda: len(connected_fired) > 0, timeout=5000)

        # Verify connected
        assert service.is_connected()
        assert len(connected_fired) == 1
        assert len(disconnected_fired) == 0

        # Wait 3 seconds to see if it auto-disconnects
        QTest.qWait(3000)

        # Should still be connected
        assert service.is_connected()
        assert len(disconnected_fired) == 0, f"Unexpected disconnects: {len(disconnected_fired)}"

        # Clean up
        service.disconnect_from_session()

    def test_multiple_connections_same_session(self, qtbot):
        """Test multiple clients in same session."""
        service1 = CollaborationService()
        service2 = CollaborationService()

        connected1 = []
        connected2 = []

        service1.connected.connect(lambda: connected1.append(True))
        service2.connected.connect(lambda: connected2.append(True))

        # Connect both
        service1.set_server_url("ws://localhost:8765")
        service1.connect_to_session("multi_test", "user1")

        qtbot.waitUntil(lambda: len(connected1) > 0, timeout=5000)

        service2.set_server_url("ws://localhost:8765")
        service2.connect_to_session("multi_test", "user2")

        qtbot.waitUntil(lambda: len(connected2) > 0, timeout=5000)

        # Both should be connected
        assert service1.is_connected()
        assert service2.is_connected()

        # Wait to verify no auto-disconnect
        QTest.qWait(2000)

        assert service1.is_connected()
        assert service2.is_connected()

        # Clean up
        service1.disconnect_from_session()
        service2.disconnect_from_session()

    def test_service_parent_lifecycle(self, qtbot, qapp):
        """Test that service with parent stays alive."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        service = CollaborationService(parent)

        connected_fired = []
        disconnected_fired = []

        service.connected.connect(lambda: connected_fired.append(True))
        service.disconnected.connect(lambda: disconnected_fired.append(True))

        service.set_server_url("ws://localhost:8765")
        service.connect_to_session("parent_test", "test_user")

        qtbot.waitUntil(lambda: len(connected_fired) > 0, timeout=5000)

        assert service.is_connected()

        # Parent still alive, connection should persist
        QTest.qWait(2000)
        assert service.is_connected()
        assert len(disconnected_fired) == 0

        # Clean up
        service.disconnect_from_session()
        parent.deleteLater()
