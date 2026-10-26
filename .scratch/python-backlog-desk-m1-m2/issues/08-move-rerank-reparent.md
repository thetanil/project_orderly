Status: ready-for-agent
Blocked by: 04
Spec: ../spec.md

# 08 Move, rerank and reparent

User stories: 30, 31, 32

## What to build

Alt+Up/Down and drag to rerank among siblings; drag or Tab/Shift+Tab to reparent, with only rows exactly one level above highlighted as drop targets. Rank uses midpoints and renumbers siblings only when gaps fall below 1e-6; R21 (duplicate rank) is never produced by the UI.

## Acceptance criteria

- [ ] Api tests: midpoint rank, renumber fallback, reparent to wrong level refused, move is one undo step.
- [ ] Drag and keyboard moves behave the same in the visual test.
