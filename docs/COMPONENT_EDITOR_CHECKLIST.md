# Component Editor Generalization - Implementation Checklist

## Pre-Implementation

- [ ] Review all strategy documents
  - [ ] Read `COMPONENT_EDITOR_GENERALIZATION_STRATEGY.md`
  - [ ] Review `COMPONENT_EDITOR_UI_MOCKUP.md`
  - [ ] Study `COMPONENT_EDITOR_IMPLEMENTATION_GUIDE.md`
  - [ ] Understand `COMPONENT_EDITOR_GENERALIZATION_SUMMARY.md`

- [ ] Set up development environment
  - [ ] Create feature branch: `feature/generalized-component-editor`
  - [ ] Ensure all existing tests pass
  - [ ] Back up current component library

- [ ] Design review meeting
  - [ ] Present mockups to team
  - [ ] Gather feedback
  - [ ] Finalize UI design

## Phase 1: Data Model (Days 1-2)

### Day 1 Morning: InterfaceDefinition Class

- [ ] Create `src/optiverse/core/interface_definition.py`
  - [ ] Define `InterfaceDefinition` dataclass
  - [ ] Implement `to_dict()` method
  - [ ] Implement `from_dict()` classmethod
  - [ ] Implement `get_color()` method
  - [ ] Implement `get_label()` method
  - [ ] Implement `length_mm()` method
  - [ ] Add docstrings

- [ ] Create `tests/core/test_interface_definition.py`
  - [ ] Test default creation
  - [ ] Test serialization round-trip
  - [ ] Test all element types
  - [ ] Test color coding
  - [ ] Test length calculation
  - [ ] Run tests: `pytest tests/core/test_interface_definition.py`

### Day 1 Afternoon: Interface Type Registry

- [ ] Create `src/optiverse/core/interface_types.py`
  - [ ] Define `INTERFACE_TYPES` dictionary
  - [ ] Implement `get_type_info()`
  - [ ] Implement `get_property_label()`
  - [ ] Implement `get_property_unit()`
  - [ ] Implement `get_property_range()`
  - [ ] Implement `get_type_color()`
  - [ ] Add docstrings

- [ ] Create `tests/core/test_interface_types.py`
  - [ ] Test type info retrieval
  - [ ] Test property metadata
  - [ ] Test all interface types
  - [ ] Run tests: `pytest tests/core/test_interface_types.py`

### Day 2 Morning: ComponentRecord Update

- [ ] Modify `src/optiverse/core/models.py`
  - [ ] Import `InterfaceDefinition`
  - [ ] Add `interfaces: List[InterfaceDefinition]` field
  - [ ] Mark legacy fields as deprecated
  - [ ] Implement `__post_init__()` with migration
  - [ ] Implement `_compute_kind()` method
  - [ ] Update docstrings

- [ ] Update `tests/core/test_component_record.py`
  - [ ] Test new interface-based creation
  - [ ] Test kind auto-computation
  - [ ] Run tests

### Day 2 Afternoon: Migration Utilities

- [ ] Create `src/optiverse/core/component_migration.py`
  - [ ] Implement `migrate_legacy_component()`
  - [ ] Implement `_migrate_simple_component()`
  - [ ] Implement `_migrate_refractive_object()`
  - [ ] Implement coordinate conversion
  - [ ] Add docstrings

- [ ] Create `tests/core/test_component_migration.py`
  - [ ] Test lens migration
  - [ ] Test mirror migration
  - [ ] Test beamsplitter migration
  - [ ] Test dichroic migration
  - [ ] Test refractive object migration
  - [ ] Test coordinate conversion
  - [ ] Test with real library components
  - [ ] Run tests: `pytest tests/core/test_component_migration.py`

- [ ] Integration test
  - [ ] Load existing component library
  - [ ] Verify all components migrate correctly
  - [ ] Check for data loss
  - [ ] Document any issues

## Phase 2: UI Widgets (Days 3-5)

### Day 3: CollapsibleInterfaceWidget - Part 1

- [ ] Create `src/optiverse/ui/widgets/__init__.py`

- [ ] Create `src/optiverse/ui/widgets/collapsible_interface_widget.py`
  - [ ] Define `CollapsibleInterfaceWidget` class
  - [ ] Implement header with expand/collapse button
  - [ ] Implement element type dropdown
  - [ ] Add color indicator
  - [ ] Add delete button

- [ ] Test widget creation
  - [ ] Run app, manually test widget
  - [ ] Verify expand/collapse works
  - [ ] Verify type dropdown works

### Day 4: CollapsibleInterfaceWidget - Part 2

- [ ] Continue `collapsible_interface_widget.py`
  - [ ] Implement geometry section
    - [ ] Add x1, y1 spinboxes
    - [ ] Add x2, y2 spinboxes
    - [ ] Add pixel coordinate labels (read-only)
    - [ ] Add length/angle display
  - [ ] Implement property section factory
    - [ ] Lens properties (EFL)
    - [ ] Mirror properties (reflectivity)
    - [ ] Beam splitter properties (T/R, PBS)
    - [ ] Dichroic properties (cutoff, width, type)
    - [ ] Refractive properties (n1, n2)
  - [ ] Connect signals
    - [ ] `interfaceChanged` signal
    - [ ] `deleteRequested` signal
    - [ ] Property value changes

- [ ] Create `tests/ui/test_collapsible_interface_widget.py`
  - [ ] Test widget creation for each type
  - [ ] Test property changes
  - [ ] Test signals
  - [ ] Run tests: `pytest tests/ui/test_collapsible_interface_widget.py`

### Day 5: InterfacePropertiesPanel

- [ ] Create `src/optiverse/ui/widgets/interface_properties_panel.py`
  - [ ] Define `InterfacePropertiesPanel` class
  - [ ] Implement scroll area with stacked widgets
  - [ ] Implement `add_interface()` method
  - [ ] Implement `remove_interface()` method
  - [ ] Implement `update_interface()` method
  - [ ] Implement `clear()` method
  - [ ] Implement selection handling
  - [ ] Connect signals from child widgets

- [ ] Create "Add Interface" dropdown menu
  - [ ] Add menu with all interface types
  - [ ] Add "Presets" submenu
  - [ ] Implement preset creation (BS Cube, etc.)

- [ ] Test panel
  - [ ] Test adding/removing interfaces
  - [ ] Test multiple interfaces
  - [ ] Test selection synchronization

## Phase 3: Integration (Days 6-7)

### Day 6: ComponentEditor Refactoring - Part 1

- [ ] Backup current `component_editor_dialog.py`

- [ ] Modify `src/optiverse/ui/views/component_editor_dialog.py`
  - [ ] Import new widgets
  - [ ] Remove old UI elements:
    - [ ] Remove `kind_combo`
    - [ ] Remove type-specific property fields
    - [ ] Remove old "Properties" section
  - [ ] Add new UI elements:
    - [ ] Add `InterfacePropertiesPanel`
    - [ ] Update layout
  - [ ] Update initialization

- [ ] Test basic layout
  - [ ] Run app
  - [ ] Verify new UI appears
  - [ ] Verify no crashes

### Day 7: ComponentEditor Refactoring - Part 2

- [ ] Continue modifying `component_editor_dialog.py`
  - [ ] Update `_sync_interfaces_to_canvas()`:
    - [ ] Convert mm → pixels for canvas
    - [ ] Use `InterfaceDefinition.get_color()`
  - [ ] Update `_on_canvas_lines_changed()`:
    - [ ] Convert pixels → mm
    - [ ] Update interface definitions
  - [ ] Update `_build_record_from_ui()`:
    - [ ] Use new interface list
    - [ ] Remove legacy field population
  - [ ] Update `_load_from_dict()`:
    - [ ] Call migration utilities
    - [ ] Populate interface panel
  - [ ] Update save/load functions

- [ ] Test canvas synchronization
  - [ ] Drag endpoint on canvas → verify mm coordinates update
  - [ ] Change mm coordinates → verify canvas updates
  - [ ] Test with multiple interfaces

## Phase 4: Coordinate System (Day 8)

### Coordinate Conversion Implementation

- [ ] Update coordinate conversion functions
  - [ ] Implement `_mm_to_pixels()` method
  - [ ] Implement `_pixels_to_mm()` method
  - [ ] Use `object_height_mm` and calibration line for scale
  - [ ] Handle edge cases (zero-length line, etc.)

- [ ] Update all coordinate handling
  - [ ] Canvas drawing: mm → pixels
  - [ ] Canvas dragging: pixels → mm
  - [ ] UI spinboxes: mm (with px reference)
  - [ ] Serialization: mm only

- [ ] Test coordinate accuracy
  - [ ] Create component with known dimensions
  - [ ] Verify round-trip accuracy
  - [ ] Test with various image sizes
  - [ ] Test with various object heights

- [ ] Add coordinate validation
  - [ ] Warn if coordinates out of image bounds
  - [ ] Validate line lengths
  - [ ] Check for degenerate cases

## Phase 5: Testing (Days 9-10)

### Day 9: Automated Testing

- [ ] Run all unit tests
  - [ ] `pytest tests/core/`
  - [ ] `pytest tests/ui/`
  - [ ] Fix any failures

- [ ] Run integration tests
  - [ ] `pytest tests/integration/`
  - [ ] Fix any failures

- [ ] Test backward compatibility
  - [ ] Load existing library
  - [ ] Verify all components work
  - [ ] Test save and reload
  - [ ] Verify no data loss

- [ ] Performance testing
  - [ ] Test with 1 interface
  - [ ] Test with 10 interfaces
  - [ ] Test with 50 interfaces
  - [ ] Measure performance (<100ms goal)

### Day 10: Manual Testing

- [ ] Test all interface types
  - [ ] Create lens interface
  - [ ] Create mirror interface
  - [ ] Create beam splitter interface
  - [ ] Create dichroic interface
  - [ ] Create refractive interface

- [ ] Test mixed components
  - [ ] Lens + mirror
  - [ ] BS + dichroic
  - [ ] Custom multi-element

- [ ] Test presets
  - [ ] BS Cube preset
  - [ ] PBS Cube preset
  - [ ] Other presets

- [ ] Test edge cases
  - [ ] Empty component
  - [ ] Single interface
  - [ ] Many interfaces (50+)
  - [ ] Zero-length interfaces
  - [ ] Out-of-bounds coordinates

- [ ] Test UI interactions
  - [ ] Expand/collapse all interfaces
  - [ ] Change element types
  - [ ] Drag endpoints on canvas
  - [ ] Edit coordinates manually
  - [ ] Add/delete interfaces
  - [ ] Reorder interfaces (if implemented)

- [ ] Test workflows
  - [ ] Create new component from scratch
  - [ ] Load library component
  - [ ] Edit and save
  - [ ] Copy/paste JSON
  - [ ] Export/import

## Phase 6: Polish & Documentation (Day 11)

### UI Polish

- [ ] Visual refinements
  - [ ] Adjust colors
  - [ ] Adjust spacing
  - [ ] Improve icons
  - [ ] Add tooltips

- [ ] Accessibility
  - [ ] Test keyboard navigation
  - [ ] Verify screen reader compatibility
  - [ ] Test high contrast mode

- [ ] Error handling
  - [ ] Add user-friendly error messages
  - [ ] Handle invalid inputs gracefully
  - [ ] Add recovery options

### Documentation

- [ ] Update user documentation
  - [ ] Update component editor guide
  - [ ] Add new feature descriptions
  - [ ] Update screenshots

- [ ] Update developer documentation
  - [ ] Update API docs
  - [ ] Document new classes
  - [ ] Update architecture diagrams

- [ ] Create migration guide
  - [ ] Document breaking changes
  - [ ] Provide migration instructions
  - [ ] List new features

- [ ] Create release notes
  - [ ] List new features
  - [ ] Document improvements
  - [ ] Note any known issues

## Phase 7: Deployment (Day 12-14)

### Alpha Release (Internal)

- [ ] Deploy to test environment
- [ ] Load production library
- [ ] Test all functionality
- [ ] Fix critical bugs
- [ ] Gather internal feedback

### Beta Release (Limited)

- [ ] Deploy to beta users
- [ ] Provide migration guide
- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Fix reported bugs

### Production Release

- [ ] Final testing
- [ ] Update version number
- [ ] Tag release in git
- [ ] Deploy to production
- [ ] Announce release
- [ ] Monitor for issues

## Post-Release

### Week 1

- [ ] Monitor bug reports
- [ ] Fix critical issues
- [ ] Respond to user questions
- [ ] Collect feedback

### Week 2-4

- [ ] Address non-critical bugs
- [ ] Plan improvements based on feedback
- [ ] Update documentation as needed
- [ ] Consider additional presets

## Success Metrics

After 1 week:
- [ ] No critical bugs reported
- [ ] All legacy components work
- [ ] User feedback mostly positive
- [ ] Performance acceptable

After 1 month:
- [ ] Users creating mixed-type components
- [ ] No major regressions
- [ ] New features being used
- [ ] Documentation is clear

## Rollback Plan

If critical issues arise:

- [ ] Identify the issue
- [ ] Assess severity
- [ ] If critical:
  - [ ] Revert to previous version
  - [ ] Notify users
  - [ ] Fix issue in dev
  - [ ] Re-deploy when fixed
- [ ] If non-critical:
  - [ ] Document workaround
  - [ ] Fix in next patch
  - [ ] Update documentation

## Notes

- Commit frequently with clear messages
- Test after each major change
- Ask for help when stuck
- Document any deviations from plan
- Keep strategy documents updated

## Completed Checklist

Mark items as complete: ~~- [x] Completed item~~

## Estimated Timeline

- Phase 1 (Data Model): 2 days
- Phase 2 (UI Widgets): 3 days
- Phase 3 (Integration): 2 days
- Phase 4 (Coordinates): 1 day
- Phase 5 (Testing): 2 days
- Phase 6 (Polish): 1 day
- Phase 7 (Deployment): 3 days

**Total: ~2 weeks**

## Resources

- Strategy: `docs/COMPONENT_EDITOR_GENERALIZATION_STRATEGY.md`
- UI Mockups: `docs/COMPONENT_EDITOR_UI_MOCKUP.md`
- Implementation: `docs/COMPONENT_EDITOR_IMPLEMENTATION_GUIDE.md`
- Summary: `docs/COMPONENT_EDITOR_GENERALIZATION_SUMMARY.md`

---

**Good luck with the implementation! 🚀**

