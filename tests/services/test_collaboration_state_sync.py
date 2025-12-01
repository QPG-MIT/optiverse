"""
Test-Driven Development: Collaboration State Synchronization

Tests for:
1. Initial state sync when joining a session
2. Host creating session with current/empty canvas
3. Client receiving full canvas state
4. Incremental updates after initial sync
"""

import json
import unittest
import uuid
from unittest.mock import Mock

from PyQt6.QtWidgets import QGraphicsScene


class TestSessionCreation(unittest.TestCase):
    """Test session creation with different canvas options."""

    def test_create_session_as_host_with_current_canvas(self):
        """Test creating a session as host with current canvas state."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Create mock main window with items
        main_window = Mock()
        main_window.scene = QGraphicsScene()

        # Add some mock items to the scene
        item1 = Mock()
        item1.item_uuid = str(uuid.uuid4())
        item1.to_dict = Mock(
            return_value={
                "uuid": item1.item_uuid,
                "x_mm": 100.0,
                "y_mm": 50.0,
                "angle_deg": 0.0,
                "focal_length_mm": 100.0,
            }
        )
        item1.__class__.__name__ = "LensItem"
        main_window.scene.addItem(item1)

        # Create collaboration manager
        collab = CollaborationManager(main_window)

        # Create session as host with current canvas
        collab.create_session(
            session_id="test-session", user_id="host-user", use_current_canvas=True
        )

        # Verify role is set to host
        assert collab.role == "host"
        assert collab.session_id == "test-session"

        # Verify canvas state was captured
        state = collab.get_session_state()
        assert state is not None
        assert "items" in state
        assert len(state["items"]) > 0

    def test_create_session_as_host_with_empty_canvas(self):
        """Test creating a session as host with empty canvas."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)

        # Create session as host with empty canvas
        collab.create_session(
            session_id="test-session", user_id="host-user", use_current_canvas=False
        )

        # Verify role is set to host
        assert collab.role == "host"

        # Verify canvas state is empty
        state = collab.get_session_state()
        assert state is not None
        assert "items" in state
        assert len(state["items"]) == 0

    def test_join_session_as_client(self):
        """Test joining a session as client."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)

        # Join session as client
        collab.join_session(
            server_url="ws://localhost:8765", session_id="test-session", user_id="client-user"
        )

        # Verify role is set to client
        assert collab.role == "client"
        assert collab.session_id == "test-session"

        # Client should request initial state
        # This will be verified by checking if request_sync was called


class TestInitialStateSync(unittest.TestCase):
    """Test initial state synchronization when joining."""

    def test_host_sends_initial_state_to_new_client(self):
        """Test that host sends full state when client joins."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Setup host
        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab_host = CollaborationManager(main_window)
        collab_host.role = "host"
        collab_host.enabled = True

        # Add items to host's scene
        item1 = Mock()
        item1.item_uuid = str(uuid.uuid4())
        item1.to_dict = Mock(
            return_value={"uuid": item1.item_uuid, "x_mm": 100.0, "y_mm": 50.0, "type": "lens"}
        )
        item1.__class__.__name__ = "LensItem"
        collab_host.item_uuid_map[item1.item_uuid] = item1

        # Mock collaboration service
        collab_host.collaboration_service = Mock()
        collab_host.collaboration_service.send_message = Mock()

        # Simulate new client connection
        collab_host._on_user_joined("new-client")

        # Verify host sent initial state
        calls = collab_host.collaboration_service.send_message.call_args_list
        assert len(calls) > 0

        # Check that a state sync message was sent
        state_sync_sent = False
        for call_args in calls:
            msg = call_args[0][0]
            if msg.get("type") == "sync:full_state":
                state_sync_sent = True
                assert "state" in msg
                assert "items" in msg["state"]
                break

        assert state_sync_sent, "Host should send full state to new client"

    def test_client_receives_and_applies_initial_state(self):
        """Test that client receives and applies full canvas state."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Setup client
        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        collab_client = CollaborationManager(main_window)
        collab_client.role = "client"
        collab_client.enabled = True

        # Create mock for retrace
        main_window.retrace = Mock()

        # Receive initial state from host
        initial_state = {
            "type": "sync:full_state",
            "state": {
                "items": [
                    {
                        "item_type": "lens",
                        "uuid": str(uuid.uuid4()),
                        "x_mm": 100.0,
                        "y_mm": 50.0,
                        "angle_deg": 0.0,
                        "focal_length_mm": 100.0,
                    },
                    {
                        "item_type": "mirror",
                        "uuid": str(uuid.uuid4()),
                        "x_mm": 200.0,
                        "y_mm": 100.0,
                        "angle_deg": 45.0,
                    },
                ],
                "version": 1,
                "timestamp": "2025-10-28T12:00:00",
            },
        }

        # Apply state
        collab_client._on_sync_state_received(initial_state)

        # Verify items were created
        assert len(collab_client.item_uuid_map) == 2

        # Verify items were added to scene
        items_in_scene = [item for item in main_window.scene.items()]
        assert len(items_in_scene) == 2

    def test_initial_state_includes_all_item_properties(self):
        """Test that initial state includes complete item data."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "host"

        # Create item with various properties
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(
            return_value={
                "uuid": item.item_uuid,
                "x_mm": 100.0,
                "y_mm": 50.0,
                "angle_deg": 45.0,
                "focal_length_mm": 100.0,
                "diameter_mm": 25.4,
                "coating": "AR",
            }
        )
        item.__class__.__name__ = "LensItem"
        collab.item_uuid_map[item.item_uuid] = item

        # Get session state
        state = collab.get_session_state()

        # Verify all properties are included
        item_data = state["items"][0]
        assert item_data["x_mm"] == 100.0
        assert item_data["y_mm"] == 50.0
        assert item_data["angle_deg"] == 45.0
        assert item_data["focal_length_mm"] == 100.0
        assert "uuid" in item_data


class TestIncrementalUpdates(unittest.TestCase):
    """Test incremental updates after initial sync."""

    def test_incremental_add_after_sync(self):
        """Test that adding items after sync sends incremental update."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "host"
        collab.enabled = True
        collab.initial_sync_complete = True

        # Mock collaboration service
        collab.collaboration_service = Mock()
        collab.collaboration_service.send_command = Mock()

        # Add new item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={"uuid": item.item_uuid, "x_mm": 100.0})
        item.__class__.__name__ = "LensItem"

        collab.broadcast_add_item(item)

        # Verify incremental command was sent (not full state)
        assert collab.collaboration_service.send_command.called
        call_args = collab.collaboration_service.send_command.call_args
        assert call_args[1]["action"] == "add_item"

    def test_no_broadcast_during_initial_sync(self):
        """Test that broadcasts are suppressed during initial sync."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()
        main_window.autotrace = False

        collab = CollaborationManager(main_window)
        collab.role = "client"
        collab.enabled = True
        collab.initial_sync_complete = False

        # Mock service
        collab.collaboration_service = Mock()
        collab.collaboration_service.send_command = Mock()

        # Receive initial state (this creates items)
        initial_state = {
            "type": "sync:full_state",
            "state": {
                "items": [
                    {
                        "item_type": "lens",
                        "uuid": str(uuid.uuid4()),
                        "x_mm": 100.0,
                        "y_mm": 50.0,
                        "angle_deg": 0.0,
                        "focal_length_mm": 100.0,
                    }
                ],
                "version": 1,
            },
        }

        collab._on_sync_state_received(initial_state)

        # Verify no commands were sent during sync
        assert not collab.collaboration_service.send_command.called


class TestSessionState(unittest.TestCase):
    """Test session state management."""

    def test_get_session_state_includes_version(self):
        """Test that session state includes version number."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "host"

        state = collab.get_session_state()

        assert "version" in state
        assert isinstance(state["version"], int)

    def test_version_increments_on_changes(self):
        """Test that version increments when canvas changes."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "host"
        collab.enabled = True

        initial_version = collab.get_session_state()["version"]

        # Make a change
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={"uuid": item.item_uuid})
        item.__class__.__name__ = "LensItem"
        collab.item_uuid_map[item.item_uuid] = item

        # Version should increment
        new_version = collab.get_session_state()["version"]
        assert new_version > initial_version

    def test_session_state_serializable(self):
        """Test that session state can be serialized to JSON."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.role = "host"

        # Add item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={"uuid": item.item_uuid, "x_mm": 100.0, "y_mm": 50.0})
        item.__class__.__name__ = "LensItem"
        collab.item_uuid_map[item.item_uuid] = item

        state = collab.get_session_state()

        # Should be serializable to JSON
        try:
            json_str = json.dumps(state)
            recovered = json.loads(json_str)
            assert recovered == state
        except (TypeError, ValueError) as e:
            self.fail(f"Session state not JSON serializable: {e}")


# Run tests if executed directly
if __name__ == "__main__":
    unittest.main()
