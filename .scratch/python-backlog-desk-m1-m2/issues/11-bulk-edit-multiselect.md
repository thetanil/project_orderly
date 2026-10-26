Status: ready-for-agent
Blocked by: 04
Spec: ../spec.md

# 11 Multi-select and bulk edit

User stories: 33

## What to build

Shift/Ctrl-click multi-select in the tree and a bulk panel for state, iteration, priority, tags and assignee, applied as one batch operation (one undo step, one validation pass, one autosave).

## Acceptance criteria

- [ ] Api test: a bulk operation over N items is one undo step and returns one consolidated response.
- [ ] Items for which a field is not allowed are skipped and reported, not corrupted.
