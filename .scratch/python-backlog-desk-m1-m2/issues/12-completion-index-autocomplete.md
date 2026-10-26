Status: ready-for-agent
Blocked by: 04, 05, 06
Spec: ../spec.md

# 12 Completion index and autocomplete

User stories: 36, 37

## What to build

Add the in-memory completion index (items, people, iterations, tags) with fuzzy ranking exposed through the Api, used for parent, iteration, assignee and tag fields, and as CodeMirror completions: `#` inserts an item reference, `@` a person. People come from the store's `people` block, with the current user (issue 10) ranked first. Index updates on every mutation.

## Acceptance criteria

- [ ] Api test: suggest returns ranked results for each kind; results for 3000 items arrive in under about 20 ms (measured in a test with a generous bound).
- [ ] Typing `#` and `@` in the editor offers matching entries.

## Comments

Implemented on branch main (backend tests under `tests/`; frontend type-checked, built and driven in a headless browser against the real Api; not yet judged on the owner's desktop).
