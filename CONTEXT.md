# Backlog Desk: domain glossary

- **Store**: the one JSON file holding a backlog (`schemaVersion` 2.x). Edited by the GUI and by agents.
- **Item**: an entry of `items`, keyed by a stable **local id** (`ado-<n>` from ADO, `new-<slug>` local). Keys never change.
- **Type / level**: `model.types` names item types; each has a level (Epic > Program Objective > Feature > Work Item). A parent is exactly one level above.
- **Work Item**: Story, Problem or Bug (the leaf level). The only level that carries story points directly.
- **Category**: Proposed, InProgress, Resolved, Completed or Removed; every state of a type maps to one.
- **Removed category**: the state category that replaces deletion for items that were ever synced.
- **Synced item**: an item with a `remotes` entry. It can be set to Removed but never deleted.
- **Rollup**: derived story-point totals (and unestimated / not-estimable counts) for non-work-items. Persisted, never edited.
- **Issue / Problem**: one validator finding (rule R1–R25, level E or W, item, field, message, optional quick fix).
- **Operation**: the single kind of edit (`set`, `create`, `delete`, `move`, `batch`, …); one operation is one undo step.
- **Last-valid snapshot**: the content last written by a successful autosave, in `.backlogdesk/last-valid.json`.
- **Merge base**: the content last loaded or saved; basis of the 3-way merge of external edits.
