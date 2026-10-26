Status: ready-for-human
Blocked by: 01, 15
Spec: ../spec.md

# 10 Filters: type, state, iteration, assigned to me

User stories: 8, 9, 10, 39, 45

## What to build

Add filter chips for type, state and iteration and a "Mine" toggle; text filter keeps matching items in their hierarchy. Filters are view state in the frontend; counts in the status bar reflect visible rows. Add a current-user setting (one entry of `people`, stored in `.backlogdesk/settings.json`, not in the store; theme and density move there too) set from the UI; "Mine" filters on it and is disabled while it is unset.

## Acceptance criteria

- [x] Api test: the current-user setting persists across reopen and never appears in the store file.
- [ ] Filtering never changes data; with 3000 stress items filter updates stay under one frame budget (visible in the perf readout).

## Comments

Implemented on branch main; criteria ticked where an automated test or CI run demonstrates them. 1 criteria remain: they need a look in the real pywebview window on the owner's desktop (or a check not run in CI).
