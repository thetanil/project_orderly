Status: ready-for-agent
Blocked by: none
Spec: ../spec.md

# 01 Svelte + Vite + TS toolchain, port the prototype

User stories: 42, 43, 44, 39, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15

## What to build

Replace the vanilla-JS prototype screen with a Svelte + TypeScript app built by Vite, behaviour unchanged: windowed tree with rollup and unestimated/not-estimable hints, inspector (title, state dropdown limited to the type's states and coloured by category, priority, story points hidden or shown as rollup per type, description), filter, show-removed, density toggle, dark default with persisted light toggle, perf readout, save (kept only until issue 03 replaces it with autosave), expand/collapse all, keyboard navigation. Built assets are loaded by the pywebview window from inside the package.

Pipeline: CI installs Node, type-checks and builds the frontend before `uv build`; the wheel contains the built assets; built assets are not committed; a frontend build or type error fails CI. The dev command builds (or watches) the frontend before opening the window. The `latest` release flow keeps working. README documents dev run, test run and run-latest, including the Node requirement for development only.

## Acceptance criteria

- [ ] `uv run --extra gui po gui` from a fresh checkout (with Node installed) shows the same screen the prototype did, including `--stress 3000` with exactly 3000 rows and no E-level issues.
- [ ] The wheel built by CI contains the built frontend and `uvx` run-latest works with no Node installed.
- [ ] A deliberate TypeScript error makes CI fail.
- [ ] Existing Api tests still pass; Api surface is unchanged.
