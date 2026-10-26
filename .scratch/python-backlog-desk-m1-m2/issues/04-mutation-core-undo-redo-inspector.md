Status: ready-for-agent
Blocked by: 01, 02
Spec: ../spec.md

# 04 Single mutation path, undo/redo, full inspector fields

User stories: 24, 25, 26, 35, 34, 41

## What to build

Introduce one mutation operation type (set field, and later create/remove/move) used by every UI edit. Each mutating Api call applies the operation, recomputes rollups, validates and returns changed items (item plus ancestors), full issues and saved/unsaved state in one response. Add undo/redo (Ctrl+Z / Ctrl+Shift+Z) over operations. Extend the inspector and inline tree editing to title, state, priority, story points, iteration, assignee and tags; `remotes` and `rollup` are read-only everywhere; fields forbidden by type are not shown.

## Acceptance criteria

- [ ] Api tests: edit returns item plus ancestors with updated rollups; undo/redo round-trips to a byte-identical store; attempts to set `remotes`/`rollup` are rejected.
- [ ] Inline edit in a tree row works for title, state, priority and story points.

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
