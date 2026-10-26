# 0001. Store v2: shape, numbering, rollups, Markdown only, app state folder

Status: accepted

## Context

The schema document (`docs/deprecated/backlog-schema-design.md`) is v1.0.0; the UI spec was written against v2.x, whose schema document is not in the repo. Backlog Desk M1/M2 is the first real implementation and needs one written, checkable shape. The store is edited by a GUI and by agents, and will later be synced with Azure DevOps (ADO).

## Decisions

1. **v2 shape.** `backlog.schema.json` (JSON Schema draft 2020-12, shipped in the package) is the structural contract: `schemaVersion` (`"2.x.y"`), `project`, `model` (types with level, label, colour, estimation, priority, states → category; includes `bug`; optional `customFields`), `people`, `iterations`, and flat `items` keyed by stable local id. Items from ADO are `ado-<id>`, local ones `new-<slug>`; keys never change. Structural validation runs first; its errors map to item + field. A missing or unknown major version is rejected on open with a readable message. Items reject unknown properties so an agent's typo is an error, not silently ignored data.
2. **Rule numbering.** The v1 rules R14–R16 are implemented once, under their v2 numbers **R23–R25** (sync conflicts present; synced item deleted versus last-valid; `remotes` changed versus last-valid by something other than the sync). R14–R17 are reserved, R18–R20 (need/trace links) are deferred with `needs.json`. The catalogue lives in `validator.py`; the Validator is a pure function of the store and an optional last-valid snapshot.
3. **Rollups are persisted but always recomputed.** ADO does not sum children, so the sync must push `rollup` values. They are derived: the stored value is overwritten by the recomputed one on load and after every operation, and cannot be edited. A load that corrects stale rollups autosaves the corrected store, and this is not an undo step. R10 exists for hand edits and is only visible through `po validate`.
4. **Stored text is Markdown only.** `description`, `acceptanceCriteria` and `localNotes` are GFM Markdown; R22 warns about raw HTML. HTML exists only at the ADO boundary (M4): HTML → Markdown on pull, Markdown → HTML on push. That conversion is lossy and not round-trip stable, so the sync must not compare converted text naively. The schema reserves `remotes.ado.richTextHashes` (hash of the remote HTML at last sync): an unchanged hash means "no remote change" and the HTML is not re-converted; on push only fields whose Markdown differs from `base` are converted and sent. HTML that cannot be represented gets a W-level issue on that field.
5. **App state is not backlog content.** Everything that is not the backlog lives in `.backlogdesk/` next to the store: `settings.json` (current user, theme, density), `last-valid.json` (the last content written by a successful autosave, used by R24/R25), and later the sync queue and Claude sessions. The folder is created on first save. `backlog.json` never contains app state.
6. **One mutation path.** All edits are operations (`set`, `create`, `delete`, `move`, …, or a `batch`) applied by the Store, which recomputes rollups and records one undo step. Undo history entries convert to RFC 6902 JSON Patch so that sync diffs (M5) and Claude proposals (M6) can reuse the same path.
7. **Items are written sorted by key** so that saves are deterministic and diffs between saves (or between a human and an agent) are small.

## Consequences

- Agents validate with `po validate FILE` (no GUI needed) and with the published JSON Schema.
- The v1 prototype's files (no `schemaVersion`) are not opened; they must be migrated to v2 by hand once.
- ADO sync (M4/M5) can be added without a schema change; only `remotes.ado` is written by it.
