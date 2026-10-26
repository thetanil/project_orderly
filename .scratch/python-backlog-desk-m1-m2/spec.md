Status: ready-for-agent

# Backlog Desk (Python + pywebview): viewer, validation and editing (M1 + M2)

Source documents: `docs/deprecated/backlog-desk-ui-spec.md` (UI spec v0.1, milestones M1 and M2) and `docs/deprecated/backlog-schema-design.md` (schema, rules, rollup). The Go/Wails implementation never existed; this spec is the first real implementation, in Python with pywebview.

## Problem Statement

A Product Owner wants a fast desktop tool to read and edit a backlog stored as one JSON file (Epics, Program Objectives, Features, Stories, Problems), with hierarchy rules, story-point rollups and validation enforced continuously. Today there is only a visual prototype: a tree, a small inspector, and a partial rule set (R2, R3, R4, R7, R8, R9). It cannot create, remove, move or undo anything, it silently ignores most validation rules, it cannot show a Problems list, and it saves with no safety against corrupting the file. The owner also needs the loop "change → push → merge → run latest on my desktop" to stay short so look-and-feel and performance can be judged on real hardware at every step.

## Solution

Grow the prototype into the M1 and M2 milestones of the UI spec, keeping one Python backend that owns all state and a thin web frontend that is only a view.

- **M1, viewer and validation:** open a store file, browse the whole hierarchy in a fast tree with an inspector, and see every validation issue in the tree, the field, the status bar and a dedicated Problems screen, with quick fixes where the UI spec defines them.
- **M2, editing:** edit any field inline or in the inspector, create items, remove items (synced items become Removed, never deleted), move items by drag or keyboard (rerank and reparent), undo and redo everything, with rollups recomputed on every change and every valid change autosaved atomically (there is no Save button), never in an invalid state. Local autocomplete for parents, iterations, people and tags. External edits to the file are merged in, not just reloaded.
- **Agents as first-class editors:** the store is also edited by agents (e.g. Claude Code in a terminal), as in the schema document's purpose. A published JSON Schema and a headless `po validate` command let an agent validate after every change without the GUI.
- **Delivery loop:** every merge to `main` refreshes the rolling `latest` release; the owner runs it on their desktop with one command. The dev version runs from the repo root with one command. Both are documented in the README.

## User Stories

1. As a PO, I want to open a backlog file from the command line, so that I can work on my real data.
2. As a PO, I want a missing file path to start from sample data and be created on the first autosave, so that I can start a new backlog without hand-writing JSON.
3. As a PO, I want an invalid or unreadable file to produce a clear message naming the problem, so that I can fix it instead of seeing a stack trace.
4. As a PO, I want to see the whole hierarchy (Epic → Program Objective → Feature → Story/Problem) as a tree ordered by rank, so that I understand the backlog at a glance.
5. As a PO, I want to expand and collapse single nodes, with keyboard arrows or by clicking, so that I can navigate quickly.
6. As a PO, I want Expand all and Collapse all, so that I can see everything or just the top level.
7. As a PO, I want the tree to stay smooth with several thousand items, so that large backlogs are usable.
8. As a PO, I want to filter by title or id and see matching items in their hierarchy, so that I can find things fast.
9. As a PO, I want to filter by type, state, iteration and "assigned to me", so that I can focus on my work.
10. As a PO, I want removed items hidden by default and shown struck through on demand, so that they do not clutter the view but are not lost.
11. As a PO, I want each row to show type colour, id, title, state chip, priority, story points (or rollup for higher levels) and a validity badge, so that I can scan status without opening items.
12. As a PO, I want a rollup shown for Features, Objectives and Epics with a hint for unestimated and not-estimable children, so that I can see incomplete effort.
13. As a PO, I want an inspector that shows only the fields allowed for the item's type (story points hidden when forbidden, rollup instead), so that I cannot enter data the rules reject.
14. As a PO, I want required fields marked and their errors shown beneath the field, so that I know what to fix.
15. As a PO, I want the state dropdown to list only states valid for the item's type, coloured by category, so that I cannot pick an invalid state.
16. As a PO, I want every validation issue listed on a Problems screen with level, rule, item, field and message, so that I can review the backlog's health.
17. As a PO, I want to filter the Problems list by rule and level, so that I can work through one kind of issue at a time.
18. As a PO, I want clicking a problem to jump to the item and field, and F8 to go to the next problem, so that fixing is quick.
19. As a PO, I want quick fixes for the rules that have them (wrong parent level, orphan, points on a forbidden type, missing estimate, missing priority, duplicate rank, raw HTML in Markdown, synced item deleted), so that common issues take one click.
20. As a PO, I want the status bar to show "saved", "N warnings" or "N errors – not saved", so that I always know whether my work is on disk.
21. As a PO, I want every valid change saved automatically with no Save button, and errors to pause autosave without discarding my in-memory edits, so that I never lose work and never write an invalid file.
22. As a PO, I want the file written atomically (temp file then rename), so that a crash cannot leave a half-written backlog.
23. As a PO, I want a copy of the last valid store kept in `.backlogdesk/` next to the file, so that rules comparing against the previous version (synced item deleted, sync-owned fields edited) can work.
24. As a PO, I want to edit title, state, priority, story points, iteration, assignee, tags and description in the inspector, so that I can change any field of any item.
25. As a PO, I want inline editing of title, state, priority and story points in the tree row, so that quick changes do not need the inspector.
26. As a PO, I want rollups recomputed on load and after every change up the whole parent chain, and persisted in the file, so that totals are never stale, cannot be hand-edited, and are ready to sync to ADO (which does not sum them itself).
27. As a PO, I want to create an item by choosing type, title and parent, with the key generated as `new-<slug>` and shown before creation, so that I control naming and the key never changes afterward.
28. As a PO, I want only valid parent levels offered when choosing a parent, so that I cannot create orphans or wrong-level children.
29. As a PO, I want "Remove" on an item that has ever been synced to set its Removed state, and a real delete only for never-synced `new-*` items with confirmation, so that I cannot break future sync.
30. As a PO, I want to rerank siblings with Alt+Up/Down and drag, so that ordering is quick.
31. As a PO, I want to reparent by drag or Tab/Shift+Tab, with only exactly-one-level-above rows accepted as targets, so that hierarchy rules hold.
32. As a PO, I want rank changes to use midpoint ranks and renumber siblings only when gaps get too small, so that reordering does not rewrite many items.
33. As a PO, I want to select several items and bulk-edit state, iteration, priority, tags or assignee, so that large changes are cheap.
34. As a PO, I want undo and redo (Ctrl+Z / Ctrl+Shift+Z) for every edit, create, remove and move, so that mistakes are cheap.
35. As a PO, I want an edit's validation and rollup result in one response, so that the UI never shows data that disagrees with the rules.
36. As a PO, I want autocomplete for parent, iteration, assignee and tags with fuzzy matching under about 20 ms, so that typing stays fast.
37. As a PO, I want `#` in a description to suggest items and insert a reference, and `@` to suggest people, so that cross-references are easy.
38. As a PO, I want a command palette (Ctrl+K) to jump to items and screens, so that I can navigate without the mouse.
39. As a PO, I want compact and comfortable row densities and a dark default theme with a light toggle remembered between launches, so that the tool fits my eyes and screen.
40. As a PO, I want an external edit to the file (for example by an agent in a terminal) detected while the app is open and merged with my in-memory state, with only true conflicts (same field changed on both sides) shown to me to resolve, so that neither my change nor the agent's is lost.
41. As a PO, I want sync-owned and derived blocks (`remotes`, `rollup`) to be read-only everywhere in the UI, so that I cannot corrupt them.
42. As a developer, I want `uv run --extra gui po gui` from the repo root to launch the dev version, and `--stress N` to generate exactly N valid items, so that I can test performance.
43. As a developer, I want every push to `main` to refresh a rolling `latest` prerelease with a wheel, and one documented command to run it on my desktop on any OS, so that I can judge each change on real hardware.
44. As a developer, I want the status bar to show API round-trip and render time, so that I can judge performance without a profiler.
45. As a PO, I want to set who I am (current user) once, so that "assigned to me" filtering and people suggestions know me.
46. As an agent editing the store, I want `po validate FILE` to print every issue in a machine-readable form and exit non-zero on E-level issues, so that I can validate after every change without the GUI.
47. As an agent editing the store, I want a published JSON Schema file for the store, so that I can check structure with standard tools.

## Implementation Decisions

- **Architecture:** one Python backend owns all state and every write to disk; the frontend never touches files. The backend is exposed to the frontend through a single API object (pywebview's `js_api`). The frontend is a Svelte + TypeScript app built with Vite, with CodeMirror 6 for every Markdown block (description, acceptance criteria, local notes). The build output is static files shipped inside the Python package; Python never renders HTML (no server-side templating), it only exposes the API and loads the built page.
- **Modules** (deep modules with small interfaces):
  - *Store:* holds the model and items in memory; applies a single mutation operation; maintains the children index; keeps an undo/redo history of operations; atomic save; keeps the last-valid snapshot.
  - *Validator:* pure function from store (plus optional previous-valid snapshot) to a list of issues, each with rule, level (E or W), item id, field, message and optional quick-fix identifier.
  - *Rollup:* pure function computing rollups per the schema document; run on load and after every mutation. Rollups **are persisted** in the store (ADO does not sum children, so the sync must push them via `rollupEffort`), but they are derived and never editable: the stored value is always overwritten by the recomputed one. If the recomputed rollups on load differ from the file, the corrected store is autosaved (if valid); this is not an undo step.
  - *Completion index:* in-memory index of items, people, iterations, tags; fuzzy ranked suggestions; rebuilt incrementally on change.
  - *Api:* thin adapter. Every mutating call returns the changed items (the item and its ancestors), the full issue list and the dirty flag in one response.
- **Schema:** a written JSON Schema (draft 2020-12) for store v2, shipped in the package as `backlog.schema.json`, extending the shape already used by the prototype: `schemaVersion`; `project`; a `model` block with per-type level, label, colour, estimation, priority rules and state-to-category maps (including the `bug` type from the UI spec's v2.1 additions); `people`; `iterations`; flat `items` keyed by stable local id, each with `rank`, the content fields from the schema document (title, state, parent, iteration, areaPath, assignedTo, priority, storyPoints, description, acceptanceCriteria, tags, businessValue, timeCriticality, targetDate, custom, localNotes), `rollup` (derived) and `remotes` (sync-owned). Items from ADO use `ado-<id>` keys and local ones `new-<slug>`; keys never change. `remotes` and `rollup` are read-only. Schema version is checked on open. Structural validation by the JSON Schema runs before the semantic rules.
- **Rule catalogue (v2 numbering, against the v2 shape).** The schema document's R14–R16 were renumbered to R23–R25 in v2; they are implemented once, under the v2 numbers.

  | # | Rule | Level |
  |---|---|---|
  | R1 | Map key equals the entry's `id` (items, iterations) | E |
  | R2 | `type` exists in `model.types` | E |
  | R3 | `state` is a state of that type | E |
  | R4 | `parent` exists and is exactly one level above; a businessEpic has no parent | E |
  | R5 | Non-epic with no parent (orphan) | W |
  | R6 | `iteration` exists in `iterations` | E |
  | R7 | `estimation: forbidden` → no story points | E |
  | R8 | `estimation: required`, not Removed, no story points | W |
  | R9 | `priority: required` → priority set | E |
  | R10 | Every non-workItem item has a `rollup` equal to the recomputed value (never surfaces in the GUI, which recomputes on load; catches hand edits via `po validate`) | E |
  | R11 | `remotes.ado.id` unique across items | E |
  | R12 | Iteration `finishDate ≥ startDate`, iteration `path` unique | E |
  | R13 | Every `custom` key on an item is a declared custom field | E |
  | R14–R17 | Reserved (meaning in v2 unknown; likely link rules) | — |
  | R18–R20 | Need/trace links; deferred with `needs.json` | — |
  | R21 | Duplicate `rank` among siblings | W |
  | R22 | Raw HTML in a Markdown field | W |
  | R23 | Sync conflicts present on an item (blocks push, allowed while editing) | W |
  | R24 | Item with a `remotes` entry deleted versus last-valid | E |
  | R25 | `remotes` changed versus last-valid by anything other than the sync | E |
- **Autosave and gates:** there is no Save button and no Ctrl+S. After every mutation (debounced while typing), if there are no E-level issues the store is written atomically; otherwise autosave pauses, the status bar shows "N errors – not saved", and in-memory state is kept. Fixing the errors resumes autosave. Sample/stress data with no file stays in memory and the status bar says so.
- **Mutation semantics:** all UI edits go through one operation type (set field, create, remove, move, and a batch of these for bulk edits and merges) so undo/redo, validation and autosave have exactly one path. Each operation is convertible to and from JSON Patch so that later milestones (Claude proposals in M6, sync diffs in M5) reuse the same path. Move sets parent and rank together; rank uses midpoints with renumbering fallback. Remove sets a Removed-category state for any item with a `remotes` entry and deletes only never-synced items.
- **Stored text is Markdown only.** Every rich-text field in the store (description, acceptanceCriteria, localNotes) is GFM Markdown, never HTML; R22 flags any HTML that gets in. HTML exists only at the ADO boundary (M4), converted on pull and push.
- **App state folder:** everything that is not backlog content lives in `.backlogdesk/` next to the store, never in `backlog.json`: `settings.json` (current user, theme, density), `last-valid.json`, and later the sync queue, staged incoming changes, template ids and Claude sessions. The folder is created on first save; a missing folder means default settings and no snapshot.
- **Current user:** an app setting in `.backlogdesk/settings.json` (not in the store) naming one entry in `people`; used by the "Mine" filter and to rank people suggestions. Set from the UI; unset means "Mine" is disabled.
- **IDs:** new keys are `new-<slug>` of the title, de-duplicated with a numeric suffix.
- **External change detection and merge:** a file watcher (or polling fallback, so no native dependency is required) detects changes on disk. The Store keeps the content it last loaded or saved as the merge base and does a 3-way merge per item and field: base = last loaded/saved, mine = in memory, theirs = disk. A field changed on one side only takes that side; the same field changed to different values on both sides (or an item deleted on one side and edited on the other) is a conflict the user resolves (keep mine / take theirs) before autosave resumes. If there are no unsaved local changes, the merge reduces to a plain reload. The merge is applied as one undoable batch operation, and is followed by rollup recompute and validation. Autosave never overwrites an external change silently.
- **Frontend components:** windowed (virtualised) tree; inspector; Problems screen; command palette; keyboard shortcuts from the UI spec; dark default theme with persisted light toggle; row density toggle; perf readout in the status bar.
- **CLI:** `po gui [FILE] [--stress N] [--debug]`; command options are passed through to the command untouched. Missing FILE starts from sample data and is created on the first autosave. `po validate FILE [--previous SNAPSHOT] [--json]` runs the same Validator headlessly (the previous snapshot defaults to `.backlogdesk/last-valid.json` next to FILE, if any), prints issues, and exits non-zero on any E-level issue.
- **Frontend build:** Node is a development and CI requirement only. CI builds the frontend before building the wheel, and the wheel contains the built assets so end users need no Node. Built assets are not committed. Dev run builds (or watches) the frontend before launching the window.
- **Packaging:** the GUI dependency is an optional extra; on Linux it installs the Qt backend from pip, elsewhere the platform default.
- **Delivery:** CI tests on push and pull request; a push to `main` replaces the rolling `latest` prerelease with a wheel carrying a dev-stamped version (so uv never serves a stale cache); tag pushes still produce versioned releases. README documents dev run, test run and run-latest.
- **Out-of-date documents:** the documents under `docs/deprecated/` are the source of requirements but are not authoritative where this spec or the code differ; the schema document in the repo is v1.0.0 while the UI spec assumes v2.1.0 (see Further Notes).

## Testing Decisions

- **What makes a good test:** assert external behaviour only, through the seam: inputs are calls the frontend makes, outputs are returned snapshots, deltas, issues, and files on disk. Do not assert on internal data structures, private helpers or JS DOM details.
- **One seam:** the Api object, driven in Python against a real Store with files in a temporary directory. No GUI process is started. Validator, rollup, undo/redo, move/rank, create/remove, atomic save, completion and stress-data generation are all exercised through Api calls.
- **Scenarios to cover:** each implemented rule has at least one failing and one passing case; the schema document's example store yields the rollup values it documents; edits return item plus ancestors with updated rollups; autosave is skipped with errors and happens without; loading a store with stale rollups writes corrected rollups; external edits merge without loss and same-field edits surface as conflicts; `po validate` exit codes and JSON output; a crash simulated between temp write and rename leaves the old file intact; undo/redo round-trips every mutation kind to byte-identical store state; synced items cannot be deleted; moves reject targets that are not exactly one level above; stress data of N items is exactly N and has no E-level issues; a missing file path starts from sample and creates the file on the first autosave; CLI passes `--stress` through to the command.
- **Frontend:** verified manually through the visual test on the owner's desktop (this is the purpose of the delivery loop). CI must at least type-check and build the frontend, and a build failure fails the pipeline. No JS test harness in this spec.
- **Prior art:** the existing store tests (rollup against the schema example, update recomputation, stress data validity, missing-file creation) and CLI tests (command passthrough) are the pattern to extend.

## Out of Scope

- Azure DevOps sync (pull, push, queue, conflict resolver), authentication, markdown/HTML conversion (UI spec M4–M5).
- Templates and template lint (M3).
- Claude integration (M6).
- Plan board and traceability matrix (M7), and rules R17–R20 that depend on `needs.json`.
- Multi-user use, Jira/GitHub mirrors, Anthropic API keys.
- A JS unit/component test harness, and Markdown preview rendering beyond what CodeMirror provides (the "As ADO sees it" tab belongs to M4).
- Code signing, installers and auto-update of the desktop app.

## Further Notes

- **Schema version gap:** the schema document in the repo is v1.0.0 (rules R1–R16, `adoMapping`, `ado`/`sync` blocks), while the UI spec is written against v2.0.0/2.1.0 (`model.types`, `remotes`, rules up to R25, needs links, templates). The v2.0.0 schema document is not in the repo, so R21–R25 are only known from the UI spec's descriptions and R14–R17 are reserved. The prototype already follows the v2-style shape. Issue 15 writes the v2 JSON Schema for this implementation and records the decision in the first ADR.
- **Decided (record in the issue 15 ADR):** stored text is Markdown only; non-content app state lives in `.backlogdesk/`.
- **ADO and Markdown (M4 concern, shapes the schema now):** ADO's rich-text fields are HTML by default, so M4 converts HTML → Markdown on pull and Markdown → HTML on push. The conversion is lossy (colours, fonts, merged-cell tables, @mention markup) and not round-trip stable, so the sync must not compare converted text naively or every pull would look like a local edit. Plan, following the UI spec's `richTextHashes`: `remotes.ado` keeps a hash of the remote HTML at last sync; on pull, an unchanged hash means "no remote change" and the HTML is not re-converted; on push, only fields whose Markdown differs from `base` are converted and sent. Pulled HTML that can't be represented in Markdown gets a W-level issue on that field. If the ADO organisation has Markdown enabled for work item fields, no conversion is needed (UI spec open question; check the org). Issue 15's schema reserves `remotes.ado.richTextHashes` so M4 needs no schema change.
- No `CONTEXT.md` or ADRs exist yet; domain terms used here (Epic, Program Objective, Feature, Work Item, Rollup, Removed category, synced item, local id) come from the deprecated documents and should be captured in a glossary when the domain-modelling step is run.
- Features should be tracked as vertical-slice issues under this directory's `issues/` folder when the spec is broken down.
- The existing vanilla-JS prototype screen is ported to Svelte as the first slice, with identical behaviour, before new features are added.
- The prototype's current behaviours that this spec keeps: dark default theme with persisted toggle, windowed tree, rollup display, `--stress N` exact counts, and `po gui FILE` creating a missing file (now on the first autosave). The prototype's Save button is dropped in favour of autosave (issue 03).
- Issue 15 (schema) and issue 01 (toolchain) are the two roots; 02 and 03 depend on 15.
