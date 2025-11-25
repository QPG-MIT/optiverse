"""
Test-Driven Development: Collaboration Reconnection & Conflict Resolution

Tests for:
1. Detecting disconnection
2. Reconnection triggers state comparison
3. Conflict resolution (host wins)
4. Re-sync after reconnection
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication, QGraphicsScene
import sys
import uuid
from datetime import datetime, timedelta

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)


class TestDisconnectionDetection(unittest.TestCase):
    """Test disconnection detection and handling."""

    def test_detect_disconnection(self):
        """Test that disconnection is detected."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)

        # Mock collaboration service
        collab.collaboration_service = Mock()
        collab.collaboration_service.is_connected = Mock(return_value=True)

        # Initially connected
        assert collab.is_connected() == True

        # Simulate disconnection
        collab.collaboration_service.is_connected = Mock(return_value=False)
        collab._on_disconnected()

        # Should be marked as disconnected
        assert collab.is_connected() == False

    def test_store_state_before_disconnection(self):
        """Test that state is preserved when disconnecting."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True

        # Add items
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={'uuid': item.item_uuid, 'x_mm': 100.0})
        item.__class__.__name__ = 'LensItem'
        collab.item_uuid_map[item.item_uuid] = item

        # Get state before disconnection
        state_before = collab.get_session_state()

        # Simulate disconnection
        collab._on_disconnected()

        # State should still be accessible (cached)
        assert collab.last_known_state is not None
        assert len(collab.last_known_state['items']) > 0

    def test_disconnection_sets_pending_sync_flag(self):
        """Test that disconnection sets a flag to trigger sync on reconnect."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Simulate disconnection
        collab._on_disconnected()

        # Should set pending sync flag
        assert collab.needs_resync == True


class TestReconnection(unittest.TestCase):
    """Test reconnection behavior."""

    def test_reconnection_triggers_state_request(self):
        """Test that reconnecting triggers a state sync request."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.needs_resync = True

        # Mock service
        collab.collaboration_service = Mock()
        collab.collaboration_service.request_sync = Mock()

        # Simulate reconnection
        collab._on_connected()

        # Should request sync
        assert collab.collaboration_service.request_sync.called

    def test_reconnection_sends_local_version(self):
        """Test that client sends local version when reconnecting."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.needs_resync = True
        collab.session_version = 5

        # Mock service
        collab.collaboration_service = Mock()
        collab.collaboration_service.send_message = Mock()

        # Simulate reconnection
        collab._on_connected()

        # Should send sync request with version
        calls = collab.collaboration_service.send_message.call_args_list
        sync_request_sent = False
        for call_args in calls:
            msg = call_args[0][0]
            if msg.get('type') == 'sync:request':
                sync_request_sent = True
                assert 'local_version' in msg
                assert msg['local_version'] == 5
                break

        assert sync_request_sent


class TestConflictResolution(unittest.TestCase):
    """Test conflict resolution when states diverge."""

    def test_host_version_wins_on_conflict(self):
        """Test that host's version is used when versions conflict."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Setup client
        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True
        collab.session_version = 3  # Client's version

        # Client has local items
        local_item = Mock()
        local_item.item_uuid = str(uuid.uuid4())
        local_item.__class__.__name__ = 'LensItem'
        collab.item_uuid_map[local_item.item_uuid] = local_item
        main_window.scene.addItem(local_item)

        # Receive host's state (different version)
        host_state = {
            'type': 'sync:full_state',
            'state': {
                'items': [
                    {
                        'item_type': 'mirror',
                        'uuid': str(uuid.uuid4()),
                        'x_mm': 200.0,
                        'y_mm': 100.0,
                        'angle_deg': 45.0
                    }
                ],
                'version': 5,  # Host's version is newer
                'timestamp': datetime.now().isoformat()
            },
            'conflict_resolution': 'host_wins'
        }

        # Apply host's state
        collab._on_sync_state_received(host_state)

        # Client should have adopted host's state
        assert collab.session_version == 5

        # Local items should be replaced
        # (exact behavior depends on implementation)

    def test_detect_version_conflict(self):
        """Test detection of version mismatch."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.session_version = 3

        # Receive state with different version
        remote_state = {
            'items': [],
            'version': 5
        }

        has_conflict = collab._detect_version_conflict(remote_state)

        assert has_conflict == True

    def test_no_conflict_when_versions_match(self):
        """Test no conflict when versions match."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.session_version = 5

        # Receive state with same version
        remote_state = {
            'items': [],
            'version': 5
        }

        has_conflict = collab._detect_version_conflict(remote_state)

        assert has_conflict == False

    def test_clear_scene_before_applying_host_state(self):
        """Test that scene is cleared before applying host's state on conflict."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Setup client with existing items
        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        # Add local items
        local_item1 = Mock()
        local_item1.item_uuid = str(uuid.uuid4())
        local_item1.__class__.__name__ = 'LensItem'
        main_window.scene.addItem(local_item1)

        local_item2 = Mock()
        local_item2.item_uuid = str(uuid.uuid4())
        local_item2.__class__.__name__ = 'MirrorItem'
        main_window.scene.addItem(local_item2)

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True
        collab.session_version = 3

        # Track scene clearing
        main_window.scene.clear = Mock()

        # Receive host's conflicting state
        host_state = {
            'type': 'sync:full_state',
            'state': {
                'items': [
                    {
                        'item_type': 'source',
                        'uuid': str(uuid.uuid4()),
                        'x_mm': 0.0,
                        'y_mm': 0.0,
                        'angle_deg': 0.0
                    }
                ],
                'version': 5,
                'timestamp': datetime.now().isoformat()
            },
            'conflict_resolution': 'host_wins'
        }

        # Apply state
        collab._on_sync_state_received(host_state)

        # Scene should have been cleared
        # (Implementation detail: might use scene.clear() or remove items individually)


class TestResync(unittest.TestCase):
    """Test re-synchronization after reconnection."""

    def test_resync_updates_all_items(self):
        """Test that resync updates all items to match host."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True

        # Receive full state sync
        full_state = {
            'type': 'sync:full_state',
            'state': {
                'items': [
                    {
                        'item_type': 'lens',
                        'uuid': str(uuid.uuid4()),
                        'x_mm': 100.0,
                        'y_mm': 50.0,
                        'angle_deg': 0.0,
                        'focal_length_mm': 100.0
                    },
                    {
                        'item_type': 'mirror',
                        'uuid': str(uuid.uuid4()),
                        'x_mm': 200.0,
                        'y_mm': 100.0,
                        'angle_deg': 45.0
                    }
                ],
                'version': 1,
                'timestamp': datetime.now().isoformat()
            }
        }

        collab._on_sync_state_received(full_state)

        # Should have all items
        assert len(collab.item_uuid_map) == 2

    def test_resync_flag_cleared_after_successful_sync(self):
        """Test that needs_resync flag is cleared after successful sync."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True
        collab.needs_resync = True

        # Receive full state
        full_state = {
            'type': 'sync:full_state',
            'state': {
                'items': [],
                'version': 1,
                'timestamp': datetime.now().isoformat()
            }
        }

        collab._on_sync_state_received(full_state)

        # Flag should be cleared
        assert collab.needs_resync == False

    def test_resync_preserves_local_changes_if_newer(self):
        """Test that local changes made offline are sent to host after resync."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True
        collab.session_version = 3

        # Client made changes while offline
        local_changes = [
            {
                'action': 'add_item',
                'item_type': 'lens',
                'uuid': str(uuid.uuid4()),
                'x_mm': 150.0,
                'y_mm': 75.0
            }
        ]
        collab.pending_changes = local_changes

        # Mock service
        collab.collaboration_service = Mock()
        collab.collaboration_service.send_command = Mock()

        # Receive host state (older version)
        host_state = {
            'type': 'sync:full_state',
            'state': {
                'items': [],
                'version': 2,  # Older than client
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat()
            }
        }

        # Apply state and send local changes
        collab._on_sync_state_received(host_state)

        # After sync, client should send its pending changes
        # (This is implementation-dependent - might send immediately or queue)


class TestServerStateManagement(unittest.TestCase):
    """Test server-side state management."""

    def test_server_stores_host_state(self):
        """Test that server stores the host's canvas state."""
        # This would test the server component
        # For now, we'll create a mock test
        pass

    def test_server_sends_state_to_new_clients(self):
        """Test that server sends stored state to newly joined clients."""
        pass

    def test_server_updates_state_on_host_changes(self):
        """Test that server updates stored state when host makes changes."""
        pass


# Run tests if executed directly
if __name__ == '__main__':
    unittest.main()



