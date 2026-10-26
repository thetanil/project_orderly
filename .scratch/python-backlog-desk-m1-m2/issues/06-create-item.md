Status: done
Blocked by: 04
Spec: ../spec.md

# 06 Create item

User stories: 27, 28

## What to build

`+ New` / `N` dialog: type, title, parent (only valid parent levels offered), with the generated `new-<slug>` key shown and editable before creation, de-duplicated with a numeric suffix. The new item appears selected and is undoable.

## Acceptance criteria

- [x] Api tests: key generation and de-duplication; creating under an invalid-level parent is refused; undo removes the item.
- [x] Created item has valid defaults for its type (state of Proposed category).

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_create_remove_move.py`, `tests/ui/test_structure_bulk_filters.py`.
