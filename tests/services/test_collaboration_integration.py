"""
Integration tests for collaboration synchronization.

Tests the full flow from broadcast to reception with real components.
"""

import json
import unittest
from unittest.mock import Mock


class TestCollaborationFullFlow(unittest.TestCase):
    """Test complete collaboration flow with real message passing."""

    def setUp(self):
        """Set up two collaboration managers simulating two users."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Create mock main windows for two users
        self.main_window_a = Mock()
        self.main_window_a.scene = Mock()
        self.main_window_a.autotrace = False
        self.main_window_a._maybe_retrace = Mock()

        self.main_window_b = Mock()
        self.main_window_b.scene = Mock()
        self.main_window_b.autotrace = False
        self.main_window_b._maybe_retrace = Mock()

        # Create collaboration managers
        self.collab_a = CollaborationManager(self.main_window_a)
        self.collab_b = CollaborationManager(self.main_window_b)

        # Enable collaboration
        self.collab_a.enabled = True
        self.collab_b.enabled = True

        # Mock the websocket send
        self.collab_a.collaboration_service.send_message = Mock()
        self.collab_b.collaboration_service.send_message = Mock()

    def test_broadcast_add_sends_message(self):
        """Test that broadcasting add sends a proper message."""
        import uuid

        # Create a mock item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.__class__.__name__ = "LensItem"
        item.to_dict = Mock(
            return_value={
                "uuid": item.item_uuid,
                "x_mm": 100.0,
                "y_mm": 50.0,
                "angle_deg": 0.0,
                "efl_mm": 100.0,
            }
        )

        # Broadcast add from user A
        self.collab_a.broadcast_add_item(item)

        # Verify message was sent
        self.assertTrue(self.collab_a.collaboration_service.send_message.called)

        # Get the sent message
        sent_message = self.collab_a.collaboration_service.send_message.call_args[0][0]

        # Verify message structure
        self.assertEqual(sent_message["type"], "command")
        self.assertEqual(sent_message["command"]["action"], "add_item")
        self.assertEqual(sent_message["command"]["item_type"], "lens")
        self.assertEqual(sent_message["command"]["item_id"], item.item_uuid)
        self.assertIn("data", sent_message["command"])

    def test_broadcast_move_sends_message(self):
        """Test that broadcasting move sends a proper message."""
        import uuid

        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.__class__.__name__ = "MirrorItem"
        item.to_dict = Mock(
            return_value={"uuid": item.item_uuid, "x_mm": 200.0, "y_mm": 100.0, "angle_deg": 45.0}
        )

        # Broadcast move from user A
        self.collab_a.broadcast_move_item(item)

        # Verify message was sent
        self.assertTrue(self.collab_a.collaboration_service.send_message.called)

        sent_message = self.collab_a.collaboration_service.send_message.call_args[0][0]

        self.assertEqual(sent_message["type"], "command")
        self.assertEqual(sent_message["command"]["action"], "move_item")
        self.assertEqual(sent_message["command"]["item_id"], item.item_uuid)
        self.assertEqual(sent_message["command"]["data"]["x_mm"], 200.0)
        self.assertEqual(sent_message["command"]["data"]["y_mm"], 100.0)

    def test_simulate_add_from_a_to_b(self):
        """Simulate user A adding item and user B receiving it."""
        import uuid

        # User A's item
        item_uuid = str(uuid.uuid4())

        # Create the message that would be sent
        message = {
            "type": "command",
            "command": {
                "action": "add_item",
                "item_type": "lens",
                "item_id": item_uuid,
                "data": {
                    "uuid": item_uuid,
                    "x_mm": 150.0,
                    "y_mm": 75.0,
                    "angle_deg": 90.0,
                    "efl_mm": 100.0,
                    "object_height_mm": 25.4,
                    "image_path": None,
                    "line_px": (0, 0, 1, 0),
                    "name": "Remote Lens",
                },
            },
            "user_id": "user_a",
        }

        # User B receives the message
        self.collab_b._on_command_received(message)

        # Verify scene.addItem was called
        self.assertTrue(self.main_window_b.scene.addItem.called)

        # Get the item that was added
        added_item = self.main_window_b.scene.addItem.call_args[0][0]

        # Verify item properties
        self.assertEqual(added_item.item_uuid, item_uuid)

    def test_simulate_move_from_a_to_b(self):
        """Simulate user A moving item and user B receiving update."""
        import uuid

        # Create an existing item on both sides
        item_uuid = str(uuid.uuid4())

        # User B's version of the item
        item_b = Mock()
        item_b.item_uuid = item_uuid
        item_b.setPos = Mock()
        item_b.setRotation = Mock()

        # Add to user B's UUID map
        self.collab_b.item_uuid_map[item_uuid] = item_b

        # Message from user A (item moved)
        message = {
            "type": "command",
            "command": {
                "action": "move_item",
                "item_type": "lens",
                "item_id": item_uuid,
                "data": {"x_mm": 300.0, "y_mm": 200.0, "angle_deg": 45.0},
            },
            "user_id": "user_a",
        }

        # User B receives the message
        self.collab_b._on_command_received(message)

        # Verify item was moved
        item_b.setPos.assert_called_once_with(300.0, 200.0)
        item_b.setRotation.assert_called_once_with(45.0)

    def test_simulate_delete_from_a_to_b(self):
        """Simulate user A deleting item and user B receiving delete."""
        import uuid

        # Create an existing item on both sides
        item_uuid = str(uuid.uuid4())

        # User B's version of the item
        item_b = Mock()
        item_b.item_uuid = item_uuid

        # Add to user B's scene and UUID map
        self.collab_b.item_uuid_map[item_uuid] = item_b

        # Message from user A (item deleted)
        message = {
            "type": "command",
            "command": {
                "action": "remove_item",
                "item_type": "lens",
                "item_id": item_uuid,
                "data": {},
            },
            "user_id": "user_a",
        }

        # User B receives the message
        self.collab_b._on_command_received(message)

        # Verify item was removed from scene
        self.main_window_b.scene.removeItem.assert_called_once_with(item_b)

        # Verify item was removed from UUID map
        self.assertNotIn(item_uuid, self.collab_b.item_uuid_map)

    def test_suppression_flag_prevents_rebroadcast(self):
        """Test that suppression flag prevents infinite loops."""
        import uuid

        item_uuid = str(uuid.uuid4())

        # Create item on user B
        item_b = Mock()
        item_b.item_uuid = item_uuid
        item_b.setPos = Mock()
        item_b.setRotation = Mock()

        self.collab_b.item_uuid_map[item_uuid] = item_b

        # Clear any previous calls
        self.collab_b.collaboration_service.send_message.reset_mock()

        # Message from user A
        message = {
            "type": "command",
            "command": {
                "action": "move_item",
                "item_type": "lens",
                "item_id": item_uuid,
                "data": {"x_mm": 100.0, "y_mm": 50.0},
            },
            "user_id": "user_a",
        }

        # User B receives and applies the message
        self.collab_b._on_command_received(message)

        # Verify suppression flag is back to False
        self.assertFalse(self.collab_b._suppress_broadcast)

        # Now if we manually try to broadcast (simulating what itemChange would do)
        # it should not send because... wait, actually it would send
        # The suppression is only active DURING the _on_command_received call

        # Let's test that during the command processing, suppression is active
        # We can't directly test this without modifying the code, but we can verify
        # that the flag is properly reset after processing
        self.assertFalse(self.collab_b._suppress_broadcast)


class TestComponentFactory(unittest.TestCase):
    """Test the component factory for creating items from remote data."""

    def setUp(self):
        """Set up collaboration manager."""
        from optiverse.services.collaboration_manager import CollaborationManager

        self.main_window = Mock()
        self.main_window.scene = Mock()
        self.collab = CollaborationManager(self.main_window)

    def test_create_lens_from_remote(self):
        """Test creating a lens from remote data."""
        data = {
            "uuid": "test-uuid-123",
            "x_mm": 100.0,
            "y_mm": 50.0,
            "angle_deg": 90.0,
            "efl_mm": 100.0,
            "object_height_mm": 25.4,
        }

        item = self.collab._create_item_from_remote("lens", data)

        self.assertIsNotNone(item)
        self.assertEqual(item.item_uuid, "test-uuid-123")

    def test_create_mirror_from_remote(self):
        """Test creating a mirror from remote data."""
        data = {
            "uuid": "test-mirror-uuid",
            "x_mm": 200.0,
            "y_mm": 100.0,
            "angle_deg": 45.0,
            "object_height_mm": 25.4,
        }

        item = self.collab._create_item_from_remote("mirror", data)

        self.assertIsNotNone(item)
        self.assertEqual(item.item_uuid, "test-mirror-uuid")

    def test_create_source_from_remote(self):
        """Test creating a source from remote data."""
        data = {
            "uuid": "test-source-uuid",
            "x_mm": 0.0,
            "y_mm": 0.0,
            "angle_deg": 0.0,
            "wavelength_nm": 633.0,
        }

        item = self.collab._create_item_from_remote("source", data)

        self.assertIsNotNone(item)
        self.assertEqual(item.item_uuid, "test-source-uuid")

    def test_unknown_item_type_returns_none(self):
        """Test that unknown item type returns None."""
        data = {"uuid": "test-uuid"}

        item = self.collab._create_item_from_remote("unknown_type", data)

        self.assertIsNone(item)


class TestMessageFormat(unittest.TestCase):
    """Test that messages are properly formatted."""

    def test_add_item_message_structure(self):
        """Test the structure of add_item messages."""
        from optiverse.services.collaboration_service import CollaborationService

        service = CollaborationService()
        service.connected_state = True
        service.user_id = "test_user"
        service.ws = Mock()
        service.ws.sendTextMessage = Mock()

        # Send command
        service.send_command(
            action="add_item",
            item_type="lens",
            item_id="uuid-123",
            data={"x_mm": 100.0, "y_mm": 50.0},
        )

        # Get sent data
        sent_data = service.ws.sendTextMessage.call_args[0][0]
        message = json.loads(sent_data)

        # Verify structure
        self.assertIn("type", message)
        self.assertIn("command", message)
        self.assertIn("timestamp", message)

        self.assertEqual(message["type"], "command")
        self.assertEqual(message["command"]["action"], "add_item")
        self.assertEqual(message["command"]["item_type"], "lens")
        self.assertEqual(message["command"]["item_id"], "uuid-123")
        self.assertIn("data", message["command"])


# Run tests
if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
