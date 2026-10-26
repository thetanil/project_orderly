Status: ready-for-agent
Blocked by: 02, 04, 05, 06, 07, 08, 12
Spec: ../spec.md

# 09 Quick fixes

User stories: 19

## What to build

Implement quick fixes from the UI spec table for rules whose fix is in scope: R4 (open parent picker filtered to valid level), R5 (pick parent), R7 (clear story points), R8 (focus story points field), R9 (focus priority), R21 (renumber siblings), R22 (convert HTML to Markdown), R24 (undo delete, set Removed). Each fix is one undoable step and exposed through the Api by issue id.

## Acceptance criteria

- [ ] Api test per quick fix: the issue disappears and no new E-level issue appears.
- [ ] Problems screen shows a Fix button only where a fix exists.
