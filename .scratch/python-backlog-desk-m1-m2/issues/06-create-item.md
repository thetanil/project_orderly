Status: ready-for-agent
Blocked by: 04
Spec: ../spec.md

# 06 Create item

User stories: 27, 28

## What to build

`+ New` / `N` dialog: type, title, parent (only valid parent levels offered), with the generated `new-<slug>` key shown and editable before creation, de-duplicated with a numeric suffix. The new item appears selected and is undoable.

## Acceptance criteria

- [ ] Api tests: key generation and de-duplication; creating under an invalid-level parent is refused; undo removes the item.
- [ ] Created item has valid defaults for its type (state of Proposed category).

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
