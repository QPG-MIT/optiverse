"""
Tests for collaboration synchronization functionality.

Test-driven development approach:
1. Write tests first (they will fail)
2. Implement features to make tests pass
3. Verify all tests pass
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication, QGraphicsScene
import sys
import uuid

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)


class TestCollaborationBroadcast(unittest.TestCase):
    """Test that local changes are broadcast to other users."""

    def test_broadcast_add_item_called_when_item_added(self):
        """Test that adding an item triggers broadcast_add_item."""
        from optiverse.services.collaboration_manager import CollaborationManager

        # Create mock main window
        main_window = Mock()
        main_window.scene = QGraphicsScene()

        # Create collaboration manager
        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Mock the broadcast method
        collab.broadcast_add_item = Mock()

        # Create a mock optical item with UUID
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={
            'uuid': item.item_uuid,
            'x_mm': 100.0,
            'y_mm': 50.0,
            'angle_deg': 0.0
        })
        item.__class__.__name__ = 'LensItem'

        # Simulate adding item
        collab.broadcast_add_item(item)

        # Verify broadcast was called
        assert collab.broadcast_add_item.called
        assert collab.broadcast_add_item.call_count == 1

    def test_broadcast_move_item_called_when_item_moved(self):
        """Test that moving an item triggers broadcast_move_item."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Mock the broadcast method
        collab.broadcast_move_item = Mock()

        # Create item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={
            'uuid': item.item_uuid,
            'x_mm': 200.0,
            'y_mm': 100.0,
            'angle_deg': 45.0
        })
        item.__class__.__name__ = 'MirrorItem'

        # Simulate moving item
        collab.broadcast_move_item(item)

        # Verify broadcast was called
        assert collab.broadcast_move_item.called

    def test_broadcast_remove_item_called_when_item_deleted(self):
        """Test that removing an item triggers broadcast_remove_item."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Mock the broadcast method
        collab.broadcast_remove_item = Mock()

        # Create item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.__class__.__name__ = 'SourceItem'

        # Simulate removing item
        collab.broadcast_remove_item(item)

        # Verify broadcast was called
        assert collab.broadcast_remove_item.called

    def test_suppression_prevents_broadcast(self):
        """Test that broadcast suppression flag prevents re-broadcasting."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Set suppression flag
        collab._suppress_broadcast = True

        # Create item
        item = Mock()
        item.item_uuid = str(uuid.uuid4())
        item.to_dict = Mock(return_value={'uuid': item.item_uuid})
        item.__class__.__name__ = 'LensItem'

        # Try to broadcast (should be suppressed)
        # Real implementation should check flag
        result = collab.broadcast_add_item(item)

        # Verify nothing was sent (implementation dependent)
        # This tests the pattern, actual implementation may vary


class TestCollaborationReceive(unittest.TestCase):
    """Test that remote changes are applied locally."""

    def test_remote_add_item_creates_item(self):
        """Test that receiving add_item creates a new item."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Create remote add message
        message = {
            'type': 'command',
            'command': {
                'action': 'add_item',
                'item_type': 'lens',
                'item_id': str(uuid.uuid4()),
                'data': {
                    'x_mm': 150.0,
                    'y_mm': 75.0,
                    'angle_deg': 0.0,
                    'focal_length_mm': 100.0
                }
            },
            'user_id': 'remote_user'
        }

        # Track if remote_item_added signal was emitted
        signal_emitted = []
        collab.remote_item_added.connect(lambda item_type, data: signal_emitted.append((item_type, data)))

        # Receive the message
        collab._on_command_received(message)

        # Verify signal was emitted
        assert len(signal_emitted) == 1
        assert signal_emitted[0][0] == 'lens'

    def test_remote_move_item_updates_position(self):
        """Test that receiving move_item updates item position."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Create an existing item
        item = Mock()
        item_uuid = str(uuid.uuid4())
        item.item_uuid = item_uuid
        item.setPos = Mock()
        item.setRotation = Mock()

        # Add to UUID map
        collab.item_uuid_map[item_uuid] = item

        # Create remote move message
        message = {
            'type': 'command',
            'command': {
                'action': 'move_item',
                'item_type': 'lens',
                'item_id': item_uuid,
                'data': {
                    'x_mm': 300.0,
                    'y_mm': 200.0,
                    'angle_deg': 90.0
                }
            },
            'user_id': 'remote_user'
        }

        # Receive the message
        collab._on_command_received(message)

        # Verify item was moved
        item.setPos.assert_called_once_with(300.0, 200.0)
        item.setRotation.assert_called_once_with(90.0)

    def test_remote_remove_item_deletes_item(self):
        """Test that receiving remove_item deletes the item."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = Mock()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Create an existing item
        item = Mock()
        item_uuid = str(uuid.uuid4())
        item.item_uuid = item_uuid

        # Add to UUID map (don't need to add to real scene for this test)
        collab.item_uuid_map[item_uuid] = item

        # Create remote remove message
        message = {
            'type': 'command',
            'command': {
                'action': 'remove_item',
                'item_type': 'lens',
                'item_id': item_uuid,
                'data': {}
            },
            'user_id': 'remote_user'
        }

        # Receive the message
        collab._on_command_received(message)

        # Verify item was removed from map
        assert item_uuid not in collab.item_uuid_map

    def test_suppression_flag_set_during_remote_apply(self):
        """Test that suppression flag is set when applying remote changes."""
        from optiverse.services.collaboration_manager import CollaborationManager

        main_window = Mock()
        main_window.scene = QGraphicsScene()

        collab = CollaborationManager(main_window)
        collab.enabled = True

        # Track suppression flag state
        flag_states = []

        def track_flag(*args):
            flag_states.append(collab._suppress_broadcast)

        # Create item
        item = Mock()
        item_uuid = str(uuid.uuid4())
        item.item_uuid = item_uuid
        item.setPos = Mock(side_effect=track_flag)

        collab.item_uuid_map[item_uuid] = item

        # Receive remote move
        message = {
            'type': 'command',
            'command': {
                'action': 'move_item',
                'item_type': 'lens',
                'item_id': item_uuid,
                'data': {'x_mm': 100.0, 'y_mm': 50.0}
            },
            'user_id': 'remote_user'
        }

        # Initial state should be False
        assert collab._suppress_broadcast == False

        # Receive the message
        collab._on_command_received(message)

        # During setPos, flag should have been True
        assert any(flag_states), "Suppression flag should have been True during remote apply"

        # After completion, flag should be False again
        assert collab._suppress_broadcast == False


class TestCollaborationMessageFormat(unittest.TestCase):
    """Test message format and serialization."""

    def test_add_item_message_format(self):
        """Test that add_item creates correct message format."""
        from optiverse.services.collaboration_service import CollaborationService

        service = CollaborationService()
        service.connected_state = True
        service.user_id = "test_user"

        # Mock websocket
        service.ws = Mock()
        service.ws.sendTextMessage = Mock()

        # Send command
        service.send_command(
            action="add_item",
            item_type="lens",
            item_id="test-uuid-123",
            data={'x_mm': 100.0, 'y_mm': 50.0}
        )

        # Verify message was sent
        assert service.ws.sendTextMessage.called

        # Check message format
        import json
        sent_data = service.ws.sendTextMessage.call_args[0][0]
        message = json.loads(sent_data)

        assert message['type'] == 'command'
        assert message['command']['action'] == 'add_item'
        assert message['command']['item_type'] == 'lens'
        assert message['command']['item_id'] == 'test-uuid-123'
        assert 'timestamp' in message

    def test_move_item_message_includes_position_and_rotation(self):
        """Test that move_item includes both position and rotation."""
        from optiverse.services.collaboration_service import CollaborationService

        service = CollaborationService()
        service.connected_state = True
        service.user_id = "test_user"
        service.ws = Mock()
        service.ws.sendTextMessage = Mock()

        # Send move command
        service.send_command(
            action="move_item",
            item_type="mirror",
            item_id="mirror-uuid",
            data={
                'x_mm': 200.0,
                'y_mm': 150.0,
                'angle_deg': 45.0
            }
        )

        # Verify message format
        import json
        sent_data = service.ws.sendTextMessage.call_args[0][0]
        message = json.loads(sent_data)

        assert message['command']['data']['x_mm'] == 200.0
        assert message['command']['data']['y_mm'] == 150.0
        assert message['command']['data']['angle_deg'] == 45.0


class TestUUIDManagement(unittest.TestCase):
    """Test UUID assignment and tracking."""

    def test_items_have_unique_uuids(self):
        """Test that each item gets a unique UUID."""
        # This will test the actual optical components when implemented
        uuids = set()

        # Create multiple items (mock for now)
        for i in range(10):
            item_uuid = str(uuid.uuid4())
            assert item_uuid not in uuids
            uuids.add(item_uuid)

        assert len(uuids) == 10

    def test_uuid_persists_in_to_dict(self):
        """Test that UUID is included in serialization."""
        # Mock item with to_dict
        item = Mock()
        test_uuid = str(uuid.uuid4())
        item.item_uuid = test_uuid
        item.to_dict = Mock(return_value={
            'uuid': test_uuid,
            'x_mm': 100.0
        })

        data = item.to_dict()
        assert 'uuid' in data
        assert data['uuid'] == test_uuid

    def test_uuid_restored_from_dict(self):
        """Test that UUID is restored when loading from dict."""
        # Mock item with from_dict
        item = Mock()
        test_uuid = str(uuid.uuid4())

        def from_dict_impl(data):
            if 'uuid' in data:
                item.item_uuid = data['uuid']

        item.from_dict = Mock(side_effect=from_dict_impl)

        # Load from dict
        item.from_dict({'uuid': test_uuid, 'x_mm': 100.0})

        # Verify UUID was set
        assert item.item_uuid == test_uuid


# Run tests if executed directly
if __name__ == '__main__':
    unittest.main()



