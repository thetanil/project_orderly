Status: done
Blocked by: 01, 15
Spec: ../spec.md

# 03 Open errors, schema version check, atomic autosave, last-valid snapshot

User stories: 1, 2, 3, 20, 21, 22, 23, 26

## What to build

Opening a missing path starts from sample and creates it on the first autosave; an unreadable or schema-invalid file produces a clear message in the UI (not a traceback); the schema version in the file is checked. On load, rollups are recomputed and, if they differ from the file, the corrected store is autosaved (not an undo step).

Remove the Save button and Ctrl+S. After every mutation (debounced while typing), the store autosaves: temp file then rename. Autosave is skipped while any E-level issue exists (in-memory edits kept, status bar shows "N errors – not saved") and resumes once they are fixed. After each successful save the previous valid store is kept as the last-valid snapshot in `.backlogdesk/last-valid.json` next to the store (folder created on first save). Sample/stress data with no file stays in memory and the status bar says so.

## Acceptance criteria

- [x] Api tests: a mutation that introduces an E-level issue does not touch the file and a later fixing mutation writes it; a store with stale rollups is rewritten with correct rollups on load; simulated failure between temp write and rename leaves the old file byte-identical; `.backlogdesk/last-valid.json` appears after a save and `backlog.json` contains no app state.
- [x] Opening a corrupt file shows a readable message and does not crash the window.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_autosave.py`, `tests/test_schema_and_open.py`, `tests/ui/test_shell_and_open.py` (corrupt file and missing schemaVersion in the window).
