"""
Example: How to integrate collaboration into MainWindow

This file shows the code changes needed to add collaboration to the existing
MainWindow class. Copy the relevant parts into your actual main_window.py.
"""

from PyQt6 import QtWidgets, QtCore
from optiverse.services.collaboration_service import CollaborationService
import time
import uuid


class MainWindowCollaborationMixin:
    """
    Mixin class showing collaboration integration.
    Add these methods to your existing MainWindow class.
    """
    
    def _init_collaboration(self):
        """
        Call this from MainWindow.__init__() after other initialization.
        """
        # Create collaboration service
        self.collab_service = CollaborationService(self)
        
        # Connect signals
        self.collab_service.connected.connect(self._on_collab_connected)
        self.collab_service.disconnected.connect(self._on_collab_disconnected)
        self.collab_service.message_received.connect(self._on_remote_update)
        self.collab_service.user_joined.connect(self._on_user_joined)
        self.collab_service.user_left.connect(self._on_user_left)
        self.collab_service.error_occurred.connect(self._on_collab_error)
        
        # Flag to prevent echo (sending back received changes)
        self._suppress_collab_send = False
        
        # Add UI elements
        self._setup_collaboration_ui()
    
    def _setup_collaboration_ui(self):
        """Add collaboration UI elements to toolbar and status bar."""
        # Add Share button to toolbar
        share_action = QtWidgets.QAction("📤 Share", self)
        share_action.setToolTip("Share this design for collaboration")
        share_action.triggered.connect(self._show_share_dialog)
        
        # Add to toolbar (adjust based on your toolbar setup)
        if hasattr(self, 'toolbar'):
            self.toolbar.addAction(share_action)
        
        # Add connection status to status bar
        self.collab_status_label = QtWidgets.QLabel("Not connected")
        self.collab_status_label.setStyleSheet("color: gray;")
        self.statusBar().addPermanentWidget(self.collab_status_label)
    
    def _show_share_dialog(self):
        """Show dialog to create or join a collaboration session."""
        from share_dialog import ShareDialog  # Import the dialog
        
        dialog = ShareDialog(self)
        dialog.server_url = "ws://localhost:8080"  # Or make configurable
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            session_id = dialog.session_id
            user_id = dialog.user_id or f"User_{int(time.time())}"
            
            # Connect to session
            self.collab_service.connect_to_session(session_id, user_id)
    
    def _on_collab_connected(self):
        """Called when successfully connected to collaboration session."""
        self.collab_status_label.setText(f"🟢 Connected: {self.collab_service.session_id}")
        self.collab_status_label.setStyleSheet("color: green;")
        self.statusBar().showMessage("Connected to collaboration session", 3000)
        
        # Send current state to newly connected users
        # (They'll request it, or we can send proactively)
        self._send_full_state()
    
    def _on_collab_disconnected(self):
        """Called when disconnected from collaboration session."""
        self.collab_status_label.setText("Not connected")
        self.collab_status_label.setStyleSheet("color: gray;")
        self.statusBar().showMessage("Disconnected from collaboration", 3000)
    
    def _on_collab_error(self, error_message: str):
        """Called when a collaboration error occurs."""
        QtWidgets.QMessageBox.warning(
            self,
            "Collaboration Error",
            f"An error occurred: {error_message}"
        )
    
    def _send_full_state(self):
        """Send all components to sync with other users."""
        # Iterate through all items in the scene
        for item in self.scene.items():
            # Check if it's one of our component types
            if hasattr(item, 'serialize'):
                self._send_component_message('component:add', item)
    
    def _send_component_message(self, action_type: str, item):
        """
        Send a component state change to other users.
        
        Args:
            action_type: 'component:add', 'component:move', 'component:edit', 'component:delete'
            item: The component item
        """
        if not self.collab_service.is_connected():
            return
        
        if self._suppress_collab_send:
            return
        
        if not hasattr(item, 'serialize'):
            return
        
        try:
            message = {
                'type': action_type,
                'data': item.serialize()
            }
            self.collab_service.send_message(message)
        except Exception as e:
            print(f"Error sending component message: {e}")
    
    def _on_remote_update(self, message: dict):
        """
        Handle an update from another user.
        
        Args:
            message: The message dict received from server
        """
        msg_type = message.get('type', '')
        data = message.get('data', {})
        
        try:
            if msg_type == 'component:add':
                self._handle_remote_add(data)
            elif msg_type == 'component:move':
                self._handle_remote_move(data)
            elif msg_type == 'component:delete':
                self._handle_remote_delete(data)
            elif msg_type == 'component:edit':
                self._handle_remote_edit(data)
            
            # Retrace rays after any change
            if self.autotrace and hasattr(self, 'refresh_rays'):
                self.refresh_rays()
        
        except Exception as e:
            print(f"Error handling remote update: {e}")
    
    def _handle_remote_add(self, data: dict):
        """Add a component from another user."""
        # Suppress sending this change back
        self._suppress_collab_send = True
        try:
            kind = data.get('kind', '')
            
            # Import component classes (adjust imports based on your structure)
            from optiverse.widgets.source_item import SourceItem
            from optiverse.widgets.lens_item import LensItem
            from optiverse.widgets.mirror_item import MirrorItem
            from optiverse.widgets.beamsplitter_item import BeamsplitterItem
            
            # Create appropriate item
            item = None
            if kind == 'source':
                item = SourceItem()
            elif kind == 'lens':
                item = LensItem()
            elif kind == 'mirror':
                item = MirrorItem()
            elif kind == 'beamsplitter':
                item = BeamsplitterItem()
            
            if item and hasattr(item, 'deserialize'):
                item.deserialize(data)
                self.scene.addItem(item)
        
        finally:
            self._suppress_collab_send = False
    
    def _handle_remote_move(self, data: dict):
        """Move a component from another user."""
        comp_id = data.get('id')
        x_mm = data.get('x_mm', 0)
        y_mm = data.get('y_mm', 0)
        
        item = self._find_item_by_id(comp_id)
        if item:
            self._suppress_collab_send = True
            try:
                item.setPos(x_mm, y_mm)
                if 'angle_deg' in data:
                    item.setRotation(data['angle_deg'])
            finally:
                self._suppress_collab_send = False
    
    def _handle_remote_delete(self, data: dict):
        """Delete a component from another user."""
        comp_id = data.get('id')
        item = self._find_item_by_id(comp_id)
        if item:
            self._suppress_collab_send = True
            try:
                self.scene.removeItem(item)
            finally:
                self._suppress_collab_send = False
    
    def _handle_remote_edit(self, data: dict):
        """Edit a component from another user."""
        comp_id = data.get('id')
        item = self._find_item_by_id(comp_id)
        if item and hasattr(item, 'deserialize'):
            self._suppress_collab_send = True
            try:
                item.deserialize(data)
            finally:
                self._suppress_collab_send = False
    
    def _find_item_by_id(self, comp_id: str):
        """
        Find an item in the scene by its component ID.
        
        Args:
            comp_id: The component's unique ID
            
        Returns:
            The item if found, None otherwise
        """
        for item in self.scene.items():
            if hasattr(item, 'component_id') and item.component_id == comp_id:
                return item
        return None
    
    def _on_user_joined(self, user_id: str):
        """Called when another user joins the session."""
        self.statusBar().showMessage(f"👤 {user_id} joined", 3000)
        # Optionally: send full state to new user
    
    def _on_user_left(self, user_id: str):
        """Called when another user leaves the session."""
        self.statusBar().showMessage(f"👋 {user_id} left", 3000)


# ==============================================================================
# Example: Adding to existing component classes
# ==============================================================================

class ComponentItemSerializationExample:
    """
    Example methods to add to your component item classes
    (SourceItem, LensItem, MirrorItem, BeamsplitterItem)
    """
    
    def __init__(self):
        """Add unique ID during __init__."""
        # ... existing __init__ code ...
        
        # Add unique ID for collaboration
        self.component_id = str(uuid.uuid4())
    
    def serialize(self) -> dict:
        """
        Serialize component state for network transmission.
        Override this in each component type.
        """
        return {
            'id': self.component_id,
            'kind': 'source',  # or 'lens', 'mirror', 'beamsplitter'
            'x_mm': self.pos().x(),
            'y_mm': self.pos().y(),
            'angle_deg': self.rotation(),
            # Add type-specific fields here
            # For source: n_rays, spread_deg, color_hex, etc.
            # For lens: efl_mm, length_mm, etc.
            # For mirror: length_mm, etc.
            # For beamsplitter: split_T, split_R, length_mm, etc.
        }
    
    def deserialize(self, data: dict):
        """
        Restore component state from network data.
        Override this in each component type.
        """
        self.component_id = data.get('id', self.component_id)
        self.setPos(data.get('x_mm', 0), data.get('y_mm', 0))
        self.setRotation(data.get('angle_deg', 0))
        # Restore type-specific fields
    
    def mouseMoveEvent(self, event):
        """
        Override to send updates during drag.
        Add this to the END of existing mouseMoveEvent.
        """
        # ... existing mouseMoveEvent code ...
        super().mouseMoveEvent(event)
        
        # Send collaboration update
        self._send_collab_update('component:move')
    
    def _send_collab_update(self, action_type: str):
        """Helper to send component updates during interaction."""
        # Get main window
        if not self.scene():
            return
        
        views = self.scene().views()
        if not views:
            return
        
        main_window = views[0].window()
        if not hasattr(main_window, 'collab_service'):
            return
        
        if not main_window.collab_service.is_connected():
            return
        
        # Don't send if we're processing a remote update
        if getattr(main_window, '_suppress_collab_send', False):
            return
        
        # Send the update
        main_window._send_component_message(action_type, self)


# ==============================================================================
# Example: Full SourceItem with collaboration
# ==============================================================================

"""
Here's how SourceItem would look with collaboration support.
Apply similar changes to LensItem, MirrorItem, BeamsplitterItem.

from PyQt6 import QtWidgets, QtCore, QtGui
from .base_obj import BaseObj
import uuid

class SourceItem(BaseObj):
    def __init__(self):
        super().__init__()
        
        # Generate unique ID for collaboration
        self.component_id = str(uuid.uuid4())
        
        # Existing properties
        self.n_rays = 9
        self.spread_deg = 0.0
        self.color_hex = "#DC143C"
        self.size_mm = 10.0
        self.ray_length_mm = 1000.0
        
        # ... rest of existing __init__ ...
    
    def serialize(self) -> dict:
        return {
            'id': self.component_id,
            'kind': 'source',
            'x_mm': self.pos().x(),
            'y_mm': self.pos().y(),
            'angle_deg': self.rotation(),
            'n_rays': self.n_rays,
            'spread_deg': self.spread_deg,
            'color_hex': self.color_hex,
            'size_mm': self.size_mm,
            'ray_length_mm': self.ray_length_mm
        }
    
    def deserialize(self, data: dict):
        self.component_id = data.get('id', self.component_id)
        self.setPos(data.get('x_mm', 0), data.get('y_mm', 0))
        self.setRotation(data.get('angle_deg', 0))
        self.n_rays = data.get('n_rays', 9)
        self.spread_deg = data.get('spread_deg', 0.0)
        self.color_hex = data.get('color_hex', '#DC143C')
        self.size_mm = data.get('size_mm', 10.0)
        self.ray_length_mm = data.get('ray_length_mm', 1000.0)
        self.update()  # Trigger repaint
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # Send update while dragging
        self._send_collab_update('component:move')
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Send final position
        self._send_collab_update('component:move')
    
    def _send_collab_update(self, action_type: str):
        if not self.scene():
            return
        views = self.scene().views()
        if not views:
            return
        main_window = views[0].window()
        if hasattr(main_window, '_send_component_message'):
            if not getattr(main_window, '_suppress_collab_send', False):
                main_window._send_component_message(action_type, self)
"""


# ==============================================================================
# Summary of changes needed
# ==============================================================================

"""
TO INTEGRATE COLLABORATION:

1. In MainWindow.__init__():
   - Add: self._init_collaboration()

2. Add all methods from MainWindowCollaborationMixin to MainWindow class

3. In each component item class (SourceItem, LensItem, etc.):
   - Add: self.component_id = str(uuid.uuid4()) in __init__
   - Add: serialize() method
   - Add: deserialize() method
   - Add: self._send_collab_update('component:move') in mouseMoveEvent
   - Add: _send_collab_update() helper method

4. Create the ShareDialog (see separate file)

5. Start the collaboration server:
   python collaboration_server.py

6. Test:
   - Open two instances of the app
   - In first: Click Share → Create session
   - In second: Click Share → Join → paste session ID
   - Drag components in either window → should appear in both!

That's it! ~200-300 lines of code added to existing app.
"""

