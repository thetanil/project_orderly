Status: ready-for-agent
Blocked by: 02, 06, 08
Spec: ../spec.md

# 13 Command palette and keyboard shortcuts

User stories: 38, 18, 30

## What to build

Ctrl+K command palette over items, screens and actions (fuzzy); shortcuts from the UI spec for this milestone: N, Enter/Esc, arrows, Alt+Up/Down, Tab/Shift+Tab, Ctrl+Z/Ctrl+Shift+Z, F8 (next problem). There is no Ctrl+S: saving is automatic (issue 03).

## Acceptance criteria

- [ ] Every shortcut listed works in the visual test; palette finds an item by id or title in the stress dataset.

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
