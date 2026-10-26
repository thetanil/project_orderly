Status: done
Blocked by: none
Spec: ../spec.md

# 15 Store schema v2 (JSON Schema) and first ADR

User stories: 47, 3, 26, 45

## What to build

Write `backlog.schema.json` (draft 2020-12) for store v2, shipped in the package, covering the shape listed under "Schema" in the spec: `schemaVersion`, `project`, `model` (types incl. `bug`, level, label, colour, estimation, priority, states), `people`, `iterations`, and `items` with `rank`, all content fields from the schema document, `rollup` (derived, persisted) and `remotes` (sync-owned; reserve `remotes.ado.richTextHashes` for M4). All rich-text fields are Markdown strings. Update the sample store and `stress_data` to match, including `schemaVersion` and a `people` block. Structural validation runs before the semantic rules and its errors map to item + field.

Record an ADR in `docs/adr/0001-…`: v2 shape and numbering (R14–R16 → R23–R25), rollups persisted but always recomputed, stored text is Markdown only (HTML only at the ADO boundary, with hash-based change detection as in the spec's Further Notes), and non-content app state in `.backlogdesk/`.

## Acceptance criteria

- [x] The sample store, stress data of any N, and the schema document's example (translated to v2) validate against the schema.
- [x] A store missing `schemaVersion` or with an unknown version is rejected on open with a readable message.
- [x] ADR exists and covers each decision listed above.

## Comments

Implemented on branch main; criteria ticked where an automated test or CI run demonstrates them.
