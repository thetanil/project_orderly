Status: done
Blocked by: 02, 06, 08
Spec: ../spec.md

# 13 Command palette and keyboard shortcuts

User stories: 38, 18, 30

## What to build

Ctrl+K command palette over items, screens and actions (fuzzy); shortcuts from the UI spec for this milestone: N, Enter/Esc, arrows, Alt+Up/Down, Tab/Shift+Tab, Ctrl+Z/Ctrl+Shift+Z, F8 (next problem). There is no Ctrl+S: saving is automatic (issue 03).

## Acceptance criteria

- [x] Every shortcut listed works in the visual test; palette finds an item by id or title in the stress dataset.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/ui/test_shell_and_open.py` (palette, N, Enter/Esc, arrows, Ctrl+Z, F8, `/`), `tests/ui/test_structure_bulk_filters.py` (Alt+Up/Down, Tab/Shift+Tab).
