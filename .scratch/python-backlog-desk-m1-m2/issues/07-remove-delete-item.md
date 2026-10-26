Status: ready-for-agent
Blocked by: 04
Spec: ../spec.md

# 07 Remove and delete

User stories: 29, 41

## What to build

Remove on an item with a `remotes` entry sets a Removed-category state (never deletes); a never-synced `new-*` item can be truly deleted after confirmation. Removed items are hidden by default and shown struck through with the toggle. Rollups exclude removed items.

## Acceptance criteria

- [ ] Api tests: delete of a synced item is refused and Removed is set instead; delete of `new-*` removes it; undo restores both; rollups recomputed.

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
