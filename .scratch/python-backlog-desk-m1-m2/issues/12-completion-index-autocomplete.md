Status: done
Blocked by: 04, 05, 06
Spec: ../spec.md

# 12 Completion index and autocomplete

User stories: 36, 37

## What to build

Add the in-memory completion index (items, people, iterations, tags) with fuzzy ranking exposed through the Api, used for parent, iteration, assignee and tag fields, and as CodeMirror completions: `#` inserts an item reference, `@` a person. People come from the store's `people` block, with the current user (issue 10) ranked first. Index updates on every mutation.

## Acceptance criteria

- [x] Api test: suggest returns ranked results for each kind; results for 3000 items arrive in under about 20 ms (measured in a test with a generous bound).
- [x] Typing `#` and `@` in the editor offers matching entries.

## Comments

Implemented on `main`. Every criterion is demonstrated by an automated test that runs in CI: `tests/test_bulk_settings_completion.py`, `tests/ui/test_editor.py` (# and @).
