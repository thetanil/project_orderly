Status: done
Blocked by: 01, 03, 15
Spec: ../spec.md

# 02 Validator for all in-scope rules and the Problems screen

User stories: 14, 16, 17, 18, 20

## What to build

Extract validation into a pure Validator returning issues with rule, level, item id, field, message and optional quick-fix id. Implement the spec's rule catalogue in v2 numbering: R1–R13 and R21–R25 (including R22 raw HTML in Markdown fields), after structural JSON Schema validation from issue 15. R14–R17 are reserved and R18–R20 stay deferred; the schema document's R14–R16 are implemented once, as R23–R25. Every mutating Api call and snapshot returns the full issue list. Add the Problems screen: full list with level, rule, item, field, message; filter by rule and level; click jumps to the item and field; status bar shows saved / warnings / errors – not saved.

## Acceptance criteria

- [x] Each implemented rule has a failing and a passing Api-level test, including the schema document's example store being valid.
- [x] Problems screen lists, filters and jumps to items; status bar counts match the list.
- [x] Rules needing the previous valid store (R24, R25) are tested against the last-valid snapshot from issue 03, and are skipped cleanly when no snapshot exists.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_validator_rules.py`, `tests/ui/test_problems_and_fixes.py`.
