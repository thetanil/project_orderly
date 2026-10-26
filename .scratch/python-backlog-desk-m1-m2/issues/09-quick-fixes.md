Status: done
Blocked by: 02, 04, 05, 06, 07, 08, 12
Spec: ../spec.md

# 09 Quick fixes

User stories: 19

## What to build

Implement quick fixes from the UI spec table for rules whose fix is in scope: R4 (open parent picker filtered to valid level), R5 (pick parent), R7 (clear story points), R8 (focus story points field), R9 (focus priority), R21 (renumber siblings), R22 (convert HTML to Markdown), R24 (undo delete, set Removed). Each fix is one undoable step and exposed through the Api by issue id.

## Acceptance criteria

- [x] Api test per quick fix: the issue disappears and no new E-level issue appears.
- [x] Problems screen shows a Fix button only where a fix exists.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_quick_fixes.py`, `tests/ui/test_problems_and_fixes.py`.
