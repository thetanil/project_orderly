Status: ready-for-agent
Blocked by: 03, 04
Spec: ../spec.md

# 14 External file change detection and 3-way merge

User stories: 40

## What to build

Detect modification of the store file while the app is open (polling fallback, no native dependency). The Store keeps the content it last loaded or saved as the merge base and merges per item and field: base = last loaded/saved, mine = in memory, theirs = disk.

- Changed on one side only: take that side.
- Same field changed to different values on both sides, or item deleted on one side and edited on the other: conflict. The UI lists conflicts with keep mine / take theirs per field; autosave pauses until all are resolved.
- No unsaved local changes: the merge is a plain reload.

The merge is applied as one batch operation (one undo step), followed by rollup recompute and validation. The disk version becomes the new merge base. Autosave never overwrites an external change silently: if the file changed since the last load/save, autosave merges first.

## Acceptance criteria

- [ ] Api tests: an external edit to item A and a local edit to item B both survive; an external and a local edit to different fields of the same item both survive; the same field edited on both sides yields a conflict and the file is not written until it is resolved; external edit with no local changes reloads; undo reverts the merge in one step.
- [ ] Rollups are recomputed after the merge (an agent adding a story updates its feature's rollup).

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
