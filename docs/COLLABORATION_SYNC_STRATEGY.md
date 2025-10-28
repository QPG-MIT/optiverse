# Collaborative Object Synchronization Strategy

## Goal
Enable real-time synchronization of optical components across multiple connected users.

## Requirements

### Functional Requirements
1. **Add Item**: When user A adds a component, user B sees it appear
2. **Move Item**: When user A moves a component, user B sees it move
3. **Rotate Item**: When user A rotates a component, user B sees it rotate
4. **Delete Item**: When user A deletes a component, user B sees it disappear
5. **Edit Properties**: When user A edits component properties, user B sees the changes

### Non-Functional Requirements
1. **No Infinite Loops**: Receiving a change should not trigger a broadcast
2. **UUID Tracking**: Each item has a unique UUID for cross-client identification
3. **Conflict Resolution**: Last-write-wins for simultaneous edits
4. **Performance**: < 100ms latency for local operations
5. **Reliability**: Handle disconnects gracefully

## Architecture

### Data Flow

```
User A Action → Local Scene Update → Broadcast Message → Server
                                                            ↓
User B ← Apply Change ← Receive Message ← Server Broadcast
```

### Message Format

```json
{
  "type": "command",
  "command": {
    "action": "add_item|move_item|remove_item|update_item",
    "item_type": "lens|mirror|source|beamsplitter|...",
    "item_id": "uuid-string",
    "data": {
      "x_mm": 100.0,
      "y_mm": 50.0,
      "angle_deg": 45.0,
      "focal_length_mm": 100.0,
      ...
    }
  },
  "user_id": "DESKTOP-RPPS2RC",
  "timestamp": "2025-10-28T14:00:00.123"
}
```

## Implementation Plan

### Phase 1: Detection (Broadcast)
**Hook into Qt signals to detect changes:**

1. **Item Added**
   - Signal: `scene.selectionChanged` after drag-drop
   - Or: Override `scene.addItem()` 
   - Extract: item type, UUID, position, rotation, properties
   - Broadcast: `add_item` command

2. **Item Moved**
   - Signal: `item.itemChange(QGraphicsItem.ItemPositionHasChanged)`
   - Extract: UUID, new position
   - Broadcast: `move_item` command

3. **Item Rotated**
   - Signal: `item.itemChange(QGraphicsItem.ItemRotationHasChanged)`
   - Extract: UUID, new angle
   - Broadcast: `move_item` command (includes rotation)

4. **Item Removed**
   - Signal: Override `scene.removeItem()`
   - Extract: UUID
   - Broadcast: `remove_item` command

5. **Properties Changed**
   - Signal: Property dialog accepted
   - Extract: UUID, changed properties
   - Broadcast: `update_item` command

### Phase 2: Application (Receive)
**Apply changes from other users:**

1. **Receive Command**
   - Parse message
   - Validate UUID exists (for move/delete) or doesn't exist (for add)
   - Set suppression flag to prevent re-broadcast
   - Apply change to local scene
   - Clear suppression flag

2. **Add Item**
   - Create item from type and data
   - Set UUID to match remote
   - Add to scene at specified position/rotation

3. **Move Item**
   - Find item by UUID
   - Update position and/or rotation
   - Trigger re-trace if needed

4. **Remove Item**
   - Find item by UUID
   - Remove from scene

5. **Update Properties**
   - Find item by UUID
   - Update properties via `from_dict()`
   - Trigger re-trace if needed

### Phase 3: Broadcast Suppression

**Problem**: Receiving a change applies it locally, which triggers the change signal, which would broadcast again → infinite loop

**Solution**: Suppression flag pattern

```python
class CollaborationManager:
    def __init__(self):
        self._suppress_broadcast = False
    
    def broadcast_move_item(self, item):
        if self._suppress_broadcast:
            return  # Don't broadcast changes from remote
        # ... send to server
    
    def _apply_remote_change(self, data):
        self._suppress_broadcast = True
        try:
            # Apply change (this triggers signals)
            item.setPos(x, y)
        finally:
            self._suppress_broadcast = False
```

### Phase 4: UUID Management

**Every item needs a persistent UUID:**

```python
# In base_obj.py or component classes
import uuid

class OpticalComponent:
    def __init__(self):
        self.item_uuid = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            'uuid': self.item_uuid,
            'x_mm': self.x(),
            'y_mm': self.y(),
            'angle_deg': self.rotation(),
            ...
        }
    
    def from_dict(self, data):
        if 'uuid' in data:
            self.item_uuid = data['uuid']
        ...
```

## Test Strategy

### Unit Tests

1. **Test: Item broadcasts on add**
   - Create item
   - Verify `broadcast_add_item()` was called
   - Verify message format

2. **Test: Item broadcasts on move**
   - Move item
   - Verify `broadcast_move_item()` was called
   - Verify position data correct

3. **Test: Suppression prevents re-broadcast**
   - Set suppression flag
   - Move item
   - Verify no broadcast

4. **Test: Remote add creates item**
   - Receive `add_item` message
   - Verify item appears in scene
   - Verify UUID matches

5. **Test: Remote move updates position**
   - Receive `move_item` message
   - Verify item moved to new position

### Integration Tests

1. **Test: Two clients sync add**
   - Client A adds item
   - Verify Client B receives and creates item
   - Verify same UUID

2. **Test: Two clients sync move**
   - Both clients have same item
   - Client A moves item
   - Verify Client B sees movement
   - Verify positions match

3. **Test: Multiple rapid changes**
   - Client A moves item 10 times quickly
   - Verify Client B receives all updates
   - Verify final position matches

## Implementation Checklist

- [ ] Add UUID to all optical components
- [ ] Hook `itemChange()` for position/rotation detection
- [ ] Hook `addItem()` / `removeItem()` for add/delete detection
- [ ] Implement `broadcast_add_item()` with full data
- [ ] Implement `broadcast_move_item()` with position/rotation
- [ ] Implement `broadcast_remove_item()` with UUID
- [ ] Implement `_apply_add_item()` to create from remote data
- [ ] Implement `_apply_move_item()` to update position
- [ ] Implement `_apply_remove_item()` to delete
- [ ] Add suppression flag mechanism
- [ ] Test with two Optiverse instances
- [ ] Handle edge cases (disconnect during move, etc.)

## Success Metrics

- ✅ Item added on A appears on B within 200ms
- ✅ Item moved on A updates on B within 100ms
- ✅ Item deleted on A disappears on B within 100ms
- ✅ No infinite broadcast loops
- ✅ No duplicate items
- ✅ UUIDs stay consistent
- ✅ Works with 2-5 simultaneous users

## Next Steps

1. Write unit tests for broadcast detection
2. Implement broadcast hooks
3. Write tests for remote application
4. Implement remote application
5. Integration test with two instances
6. Add property synchronization
7. Add undo/redo synchronization (future)

