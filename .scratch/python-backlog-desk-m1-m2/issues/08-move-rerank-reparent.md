Status: done
Blocked by: 04
Spec: ../spec.md

# 08 Move, rerank and reparent

User stories: 30, 31, 32

## What to build

Alt+Up/Down and drag to rerank among siblings; drag or Tab/Shift+Tab to reparent, with only rows exactly one level above highlighted as drop targets. Rank uses midpoints and renumbers siblings only when gaps fall below 1e-6; R21 (duplicate rank) is never produced by the UI.

## Acceptance criteria

- [x] Api tests: midpoint rank, renumber fallback, reparent to wrong level refused, move is one undo step.
- [x] Drag and keyboard moves behave the same in the visual test.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_create_remove_move.py`, `tests/ui/test_structure_bulk_filters.py` (drag and keyboard give the same result).
