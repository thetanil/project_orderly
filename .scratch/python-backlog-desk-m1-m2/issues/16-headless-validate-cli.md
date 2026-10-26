Status: done
Blocked by: 02
Spec: ../spec.md

# 16 Headless `po validate` for agents

User stories: 46, 47

## What to build

`po validate FILE [--previous SNAPSHOT] [--json]` runs the JSON Schema and the same Validator the GUI uses, without starting a window or needing the GUI extra. Without `--previous`, `.backlogdesk/last-valid.json` next to FILE is used if present (so R24/R25 catch an agent deleting a synced item or editing `remotes`). Human-readable output by default; `--json` prints the issue list with rule, level, item id, field, message. Exit code 0 when there are no E-level issues, 1 otherwise, 2 when the file cannot be read. Document it in the README as the step agents run after every change.

## Acceptance criteria

- [x] CLI tests: clean store exits 0; store with an E-level issue exits 1 and lists it; hand-edited rollup reports R10; `--previous` with a deleted synced item reports R24; `--json` output parses.
- [x] Works with the base install (no `gui` extra).

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_cli_validate.py`.
