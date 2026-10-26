Status: ready-for-human
Blocked by: 04
Spec: ../spec.md

# 08 Move, rerank and reparent

User stories: 30, 31, 32

## What to build

Alt+Up/Down and drag to rerank among siblings; drag or Tab/Shift+Tab to reparent, with only rows exactly one level above highlighted as drop targets. Rank uses midpoints and renumbers siblings only when gaps fall below 1e-6; R21 (duplicate rank) is never produced by the UI.

## Acceptance criteria

- [x] Api tests: midpoint rank, renumber fallback, reparent to wrong level refused, move is one undo step.
- [ ] Drag and keyboard moves behave the same in the visual test.

## Comments

Implemented on branch main; criteria ticked where an automated test or CI run demonstrates them. 1 criteria remain: they need a look in the real pywebview window on the owner's desktop (or a check not run in CI).
