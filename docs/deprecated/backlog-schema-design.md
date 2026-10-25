# PO Backlog Store: JSON Schema Design

**Purpose:** a single JSON file that holds the PO backlog. Agents read and edit it, validate it after every change, and sync it two-way with Azure DevOps through the ADO MCP.

**Hierarchy:** Business Epic → Program Objective → Feature → Work Item. Work Items are planned into Iterations.

---

## 1. Design principles

1. **Flat store, hierarchy by reference.** All items live in one map keyed by a stable local id, and `parent` points to another key. Agents can edit one item without walking a tree, and moving an item under a new parent is a single-field change.
2. **Local ids are permanent.** Items pulled from ADO get the key `ado-<id>`. Items created locally get `new-<slug>` and keep that key after ADO assigns an id. References therefore never need rewriting.
3. **Config-driven types.** Rules such as "Problems have a priority but no story points" are not hard-coded. Each type declares its level, ADO type name, estimation rule, priority rule and states in `adoMapping.types`. That lets you add an Enabler or Spike type without changing the schema.
4. **Effort is derived, never estimated, above the Work Item level.** Feature effort is the sum of its children's story points. Program Objective and Business Epic effort roll up the same way. Roll-ups are recomputed, never hand-edited.
5. **Sync state is separated from content.** `ado` and `sync` blocks belong to the sync process only. Agents editing the backlog never touch them.
6. **3-way merge.** Each synced item carries `sync.base`, a snapshot of its fields at the last sync. Local changes are `current ≠ base`, and remote changes are `ADO ≠ base`. When the same field changed on both sides, the sync records a conflict instead of overwriting either value.

---

## 2. Store layout

```text
{
  schemaVersion   "1.0.0"
  project         org / project / team / default area path
  adoMapping      types (level, ADO type, rules, states) + field reference names
  iterations      { <localId>: iteration }
  items           { <localId>: item }   ← epics, POs, features, work items, all flat
  sync            store-level pull/push timestamps and WIQL scope
}
```

### Item ownership

| Block | Written by | Synced to ADO |
|---|---|---|
| `title`, `state`, `parent`, `iteration`, `areaPath`, `assignedTo`, `priority`, `storyPoints`, `description`, `acceptanceCriteria`, `tags`, `businessValue`, `timeCriticality`, `targetDate`, `custom` | Agents / PO | Yes |
| `rollup` | Recompute step | Optional (via `adoMapping.fields.rollupEffort`) |
| `localNotes` | Agents / PO | No |
| `ado`, `sync` | Sync process only | — |

---

## 3. JSON Schema (draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.local/po-backlog/backlog.schema.json",
  "title": "PO backlog store",
  "type": "object",
  "required": ["schemaVersion", "project", "adoMapping", "iterations", "items"],
  "additionalProperties": false,
  "properties": {
    "$schema": { "type": "string" },
    "schemaVersion": { "const": "1.0.0" },
    "project": { "$ref": "#/$defs/project" },
    "adoMapping": { "$ref": "#/$defs/adoMapping" },
    "iterations": {
      "type": "object",
      "propertyNames": { "$ref": "#/$defs/localId" },
      "additionalProperties": { "$ref": "#/$defs/iteration" }
    },
    "items": {
      "description": "All items at every level, keyed by local id. Hierarchy via `parent`.",
      "type": "object",
      "propertyNames": { "$ref": "#/$defs/localId" },
      "additionalProperties": { "$ref": "#/$defs/item" }
    },
    "sync": { "$ref": "#/$defs/storeSync" }
  },

  "$defs": {
    "localId": {
      "description": "Stable key: 'ado-<id>' for pulled items, 'new-<slug>' for locally created ones. Never changes.",
      "type": "string",
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    },
    "nullableLocalId": { "anyOf": [{ "$ref": "#/$defs/localId" }, { "type": "null" }] },
    "level": { "enum": ["businessEpic", "programObjective", "feature", "workItem"] },
    "stateCategory": { "enum": ["Proposed", "InProgress", "Resolved", "Completed", "Removed"] },
    "html": { "description": "Rich text as HTML (ADO's native format).", "type": "string" },
    "adoFieldRef": { "type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$" },
    "scalar": { "type": ["string", "number", "integer", "boolean", "null"] },

    "project": {
      "type": "object",
      "required": ["organization", "project"],
      "additionalProperties": false,
      "properties": {
        "organization": { "type": "string", "minLength": 1 },
        "project": { "type": "string", "minLength": 1 },
        "team": { "type": "string" },
        "defaultAreaPath": { "type": "string" }
      }
    },

    "typeConfig": {
      "type": "object",
      "required": ["level", "adoType", "estimation", "priority", "states"],
      "additionalProperties": false,
      "properties": {
        "level": { "$ref": "#/$defs/level" },
        "adoType": { "description": "Exact ADO work item type name.", "type": "string", "minLength": 1 },
        "estimation": {
          "description": "Story point rule. Use 'forbidden' for Problems and for every level above workItem.",
          "enum": ["required", "optional", "forbidden"]
        },
        "priority": { "enum": ["required", "optional"] },
        "states": {
          "description": "ADO state name -> state category.",
          "type": "object",
          "minProperties": 1,
          "additionalProperties": { "$ref": "#/$defs/stateCategory" }
        }
      }
    },

    "adoMapping": {
      "type": "object",
      "required": ["types", "fields"],
      "additionalProperties": false,
      "properties": {
        "types": {
          "type": "object",
          "minProperties": 1,
          "propertyNames": { "$ref": "#/$defs/localId" },
          "additionalProperties": { "$ref": "#/$defs/typeConfig" }
        },
        "fields": {
          "description": "Local field -> ADO reference name. System.* fields are fixed and not listed.",
          "type": "object",
          "required": ["storyPoints", "priority"],
          "additionalProperties": false,
          "properties": {
            "storyPoints": { "$ref": "#/$defs/adoFieldRef" },
            "priority": { "$ref": "#/$defs/adoFieldRef" },
            "acceptanceCriteria": { "$ref": "#/$defs/adoFieldRef" },
            "businessValue": { "$ref": "#/$defs/adoFieldRef" },
            "timeCriticality": { "$ref": "#/$defs/adoFieldRef" },
            "targetDate": { "$ref": "#/$defs/adoFieldRef" },
            "rollupEffort": {
              "description": "ADO field that receives rollup.storyPoints for Features/POs/Epics. null = keep local.",
              "anyOf": [{ "$ref": "#/$defs/adoFieldRef" }, { "type": "null" }]
            },
            "custom": {
              "type": "object",
              "additionalProperties": { "$ref": "#/$defs/adoFieldRef" }
            }
          }
        }
      }
    },

    "iteration": {
      "type": "object",
      "required": ["id", "name", "path"],
      "additionalProperties": false,
      "properties": {
        "id": { "$ref": "#/$defs/localId" },
        "name": { "type": "string", "minLength": 1 },
        "path": { "description": "Full ADO iteration path.", "type": "string", "minLength": 1 },
        "startDate": { "type": ["string", "null"], "format": "date" },
        "finishDate": { "type": ["string", "null"], "format": "date" },
        "adoId": { "description": "ADO iteration GUID.", "type": ["string", "null"] }
      }
    },

    "rollup": {
      "description": "DERIVED from children. Never hand-edited. Excludes items in a Removed-category state.",
      "type": "object",
      "required": ["storyPoints", "estimatedCount", "unestimatedCount", "notEstimableCount"],
      "additionalProperties": false,
      "properties": {
        "storyPoints": { "type": "number", "minimum": 0 },
        "estimatedCount": { "type": "integer", "minimum": 0 },
        "unestimatedCount": { "description": "Leaf items that may have points but don't.", "type": "integer", "minimum": 0 },
        "notEstimableCount": { "description": "Leaf items whose type forbids points (e.g. Problems).", "type": "integer", "minimum": 0 }
      }
    },

    "syncedFields": {
      "description": "Snapshot of synced fields at last successful sync (merge base).",
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "title": { "type": "string" },
        "state": { "type": "string" },
        "parent": { "$ref": "#/$defs/nullableLocalId" },
        "iteration": { "$ref": "#/$defs/nullableLocalId" },
        "areaPath": { "type": ["string", "null"] },
        "assignedTo": { "type": ["string", "null"] },
        "priority": { "type": ["integer", "null"] },
        "storyPoints": { "type": ["number", "null"] },
        "description": { "type": ["string", "null"] },
        "acceptanceCriteria": { "type": ["string", "null"] },
        "tags": { "type": "array", "items": { "type": "string" } },
        "businessValue": { "type": ["integer", "null"] },
        "timeCriticality": { "type": ["integer", "null"] },
        "targetDate": { "type": ["string", "null"] },
        "custom": { "type": "object", "additionalProperties": { "$ref": "#/$defs/scalar" } },
        "rollupEffort": { "type": ["number", "null"] }
      }
    },

    "item": {
      "type": "object",
      "required": ["id", "type", "title", "state", "parent"],
      "additionalProperties": false,
      "properties": {
        "id": { "$ref": "#/$defs/localId" },
        "type": { "description": "Key into adoMapping.types.", "$ref": "#/$defs/localId" },
        "title": { "type": "string", "minLength": 1, "maxLength": 255 },
        "state": { "description": "ADO state name valid for this type.", "type": "string", "minLength": 1 },
        "parent": { "$ref": "#/$defs/nullableLocalId" },
        "iteration": { "$ref": "#/$defs/nullableLocalId" },
        "areaPath": { "type": ["string", "null"] },
        "assignedTo": { "description": "ADO unique name / email.", "type": ["string", "null"] },
        "priority": { "description": "1 = highest.", "type": ["integer", "null"], "minimum": 1, "maximum": 4 },
        "storyPoints": { "type": ["number", "null"], "minimum": 0 },
        "description": { "anyOf": [{ "$ref": "#/$defs/html" }, { "type": "null" }] },
        "acceptanceCriteria": { "anyOf": [{ "$ref": "#/$defs/html" }, { "type": "null" }] },
        "tags": {
          "type": "array",
          "uniqueItems": true,
          "items": { "type": "string", "minLength": 1, "pattern": "^[^;]+$" }
        },
        "businessValue": { "type": ["integer", "null"], "minimum": 0 },
        "timeCriticality": { "type": ["integer", "null"], "minimum": 0 },
        "targetDate": { "type": ["string", "null"], "format": "date" },
        "custom": { "type": "object", "additionalProperties": { "$ref": "#/$defs/scalar" } },
        "localNotes": { "description": "Never synced.", "type": "string" },
        "rollup": { "$ref": "#/$defs/rollup" },
        "ado": {
          "description": "SYNC-OWNED.",
          "type": "object",
          "required": ["id", "rev"],
          "additionalProperties": false,
          "properties": {
            "id": { "type": "integer", "minimum": 1 },
            "rev": { "type": "integer", "minimum": 1 },
            "url": { "type": "string", "format": "uri" },
            "changedDate": { "type": "string", "format": "date-time" },
            "changedBy": { "type": "string" }
          }
        },
        "sync": {
          "description": "SYNC-OWNED.",
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "base": { "$ref": "#/$defs/syncedFields" },
            "lastSyncedAt": { "type": "string", "format": "date-time" },
            "conflicts": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["field", "local", "remote"],
                "additionalProperties": false,
                "properties": {
                  "field": { "type": "string" },
                  "local": {},
                  "remote": {},
                  "remoteRev": { "type": "integer" },
                  "detectedAt": { "type": "string", "format": "date-time" }
                }
              }
            }
          }
        }
      }
    },

    "storeSync": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "lastPullAt": { "type": ["string", "null"], "format": "date-time" },
        "lastPushAt": { "type": ["string", "null"], "format": "date-time" },
        "scopeWiql": { "type": ["string", "null"] }
      }
    }
  }
}
```

---

## 4. Semantic rules (beyond JSON Schema)

JSON Schema can't follow references between items or compute sums. The validation step must check these rules as well. **E** means error (the store is invalid), and **W** means warning (valid, but worth surfacing to the PO).

| # | Rule | Level |
|---|---|---|
| R1 | Each map key equals the `id` inside its entry (items and iterations). | E |
| R2 | `item.type` exists in `adoMapping.types`. | E |
| R3 | `item.state` is a key of `adoMapping.types[type].states`. | E |
| R4 | `parent` (if set) exists, and its level is exactly one above: workItem → feature → programObjective → businessEpic. A businessEpic has `parent: null`. | E |
| R5 | Any item other than a businessEpic with `parent: null` is an orphan. | W |
| R6 | `iteration` (if set) exists in `iterations`. | E |
| R7 | Type `estimation: forbidden` → `storyPoints` is null. This covers Problems and everything above workItem. | E |
| R8 | Type `estimation: required` → `storyPoints` is null and the state category isn't Removed. | W |
| R9 | Type `priority: required` → `priority` is not null. This applies to Problems. | E |
| R10 | `rollup` is present on every non-workItem item and equals the recomputed value (§5). | E |
| R11 | `ado.id` is unique across items. | E |
| R12 | `iteration.finishDate ≥ startDate`, and iteration `path` is unique. | E |
| R13 | Every `custom` key on an item exists in `adoMapping.fields.custom`. | E |
| R14 | `sync.conflicts` is non-empty. This blocks push but is allowed while editing. | W |
| R15 | Compared with the previous version of the store, an item that has `ado.id` was deleted. Use a Removed state instead. | E |
| R16 | Compared with the previous version, an agent (not the sync) changed `ado` or `sync`. | E |

---

## 5. Roll-up computation

For each item at the feature, programObjective or businessEpic level:

- Skip children whose state category is **Removed**.
- For a **workItem** child:
  - If its type forbids estimation (e.g. Problem), add 1 to `notEstimableCount`.
  - If `storyPoints` is null, add 1 to `unestimatedCount`.
  - Otherwise, add its story points to `storyPoints` and add 1 to `estimatedCount`.
- For a **non-leaf** child, add up its `rollup` field by field.

The result:

- **Feature effort** = `rollup.storyPoints`, the sum of its Work Items' story points.
- A Feature with `notEstimableCount > 0` contains Problems: they carry priority, but their effort is invisible in the number.
- A Feature with `unestimatedCount > 0` has incomplete effort, and refinement is needed.

If `adoMapping.fields.rollupEffort` is set (for example `Microsoft.VSTS.Scheduling.Effort` on Feature), the roll-up is pushed to ADO as a one-way, local-to-ADO field.

---

## 6. ADO field mapping

| Store field | ADO field | Notes |
|---|---|---|
| `title` | `System.Title` | max 255 |
| `state` | `System.State` | per-type state names |
| `parent` | relation `System.LinkTypes.Hierarchy-Reverse` | change = remove old relation + add new |
| `iteration` | `System.IterationPath` | via `iterations[id].path` |
| `areaPath` | `System.AreaPath` | |
| `assignedTo` | `System.AssignedTo` | unique name |
| `tags` | `System.Tags` | array ↔ `"a; b"` |
| `description` | `System.Description` | HTML |
| `priority` | `adoMapping.fields.priority` | usually `Microsoft.VSTS.Common.Priority` |
| `storyPoints` | `adoMapping.fields.storyPoints` | Agile: `Microsoft.VSTS.Scheduling.StoryPoints`; Scrum: `…Effort` |
| `acceptanceCriteria` | `Microsoft.VSTS.Common.AcceptanceCriteria` | |
| `businessValue` / `timeCriticality` | `Microsoft.VSTS.Common.BusinessValue` / `…TimeCriticality` | WSJF inputs |
| `targetDate` | `Microsoft.VSTS.Scheduling.TargetDate` | |
| `rollup.storyPoints` | `adoMapping.fields.rollupEffort` | push only |
| `ado.id` / `ado.rev` | `id` / `rev` | read only |

---

## 7. Sync protocol (via ADO MCP)

### Pull (ADO → store)

1. Select items with `sync.scopeWiql`, for example by area path plus the work item types in the mapping. Fetch fields and relations in batches.
2. For each remote item:
   - **Not in the store:** add it as `ado-<id>`, set `base` to the remote values, and set `ado.rev`.
   - **`remote.rev == ado.rev`:** nothing has changed.
   - **`remote.rev > ado.rev`:** check each field:
     - If ADO changed it and the local value didn't, take the remote value.
     - If both sides changed it to different values, keep the local value and append a conflict.
     - Then set `base` to the remote values and update `ado.rev`.
3. Pull iterations for the team and upsert them by `path`.
4. Recompute roll-ups, then validate.

### Push (store → ADO)

1. Refuse to push if any item has `sync.conflicts`.
2. Handle **new items** (no `ado`) parents-first: epics, then POs, then features, then work items. Create each one with its fields and parent relation, then write `ado` and `base`.
3. Handle **changed items** (`current ≠ base` on synced fields). Send a JSON Patch that starts with `test /rev = ado.rev`, so the update fails if ADO moved on, followed by `replace` on the changed fields. If the MCP's update tool can't send a `test` op, re-read `rev` immediately before updating.
4. If the rev test fails, run a pull for that item. The pull will raise conflicts, and the push stops for that item.
5. On success, update `ado.rev`, `base`, `lastSyncedAt` and the store's `sync.lastPushAt`.

### Agent rules

- Validate after **every** change, and don't continue on errors.
- Never edit `ado`, `sync` or `rollup` by hand. Recompute the roll-ups instead.
- Never delete a synced item. Set a state from the Removed category instead.
- Create new items with `new-<slug>` keys.
- Resolve a conflict by setting the field to the chosen value and removing the conflict entry.

---

## 8. Example store

```json
{
  "$schema": "./backlog.schema.json",
  "schemaVersion": "1.0.0",
  "project": { "organization": "contoso", "project": "Payments", "team": "Checkout", "defaultAreaPath": "Payments\\Checkout" },
  "adoMapping": {
    "types": {
      "businessEpic":     { "level": "businessEpic",     "adoType": "Epic",              "estimation": "forbidden", "priority": "optional",
                            "states": { "New": "Proposed", "Active": "InProgress", "Done": "Completed", "Removed": "Removed" } },
      "programObjective": { "level": "programObjective", "adoType": "Program Objective", "estimation": "forbidden", "priority": "optional",
                            "states": { "New": "Proposed", "Active": "InProgress", "Done": "Completed", "Removed": "Removed" } },
      "feature":          { "level": "feature",          "adoType": "Feature",           "estimation": "forbidden", "priority": "optional",
                            "states": { "New": "Proposed", "Active": "InProgress", "Resolved": "Resolved", "Closed": "Completed", "Removed": "Removed" } },
      "story":            { "level": "workItem",         "adoType": "User Story",        "estimation": "required",  "priority": "optional",
                            "states": { "New": "Proposed", "Active": "InProgress", "Resolved": "Resolved", "Closed": "Completed", "Removed": "Removed" } },
      "problem":          { "level": "workItem",         "adoType": "Problem",           "estimation": "forbidden", "priority": "required",
                            "states": { "New": "Proposed", "Active": "InProgress", "Closed": "Completed", "Removed": "Removed" } }
    },
    "fields": {
      "storyPoints": "Microsoft.VSTS.Scheduling.StoryPoints",
      "priority": "Microsoft.VSTS.Common.Priority",
      "acceptanceCriteria": "Microsoft.VSTS.Common.AcceptanceCriteria",
      "rollupEffort": "Microsoft.VSTS.Scheduling.Effort",
      "custom": {}
    }
  },
  "iterations": {
    "pi26-4-s1": { "id": "pi26-4-s1", "name": "Sprint 1", "path": "Payments\\PI 26.4\\Sprint 1", "startDate": "2026-10-19", "finishDate": "2026-10-30" }
  },
  "items": {
    "ado-100": { "id": "ado-100", "type": "businessEpic", "title": "Self-service checkout", "state": "Active", "parent": null,
                 "rollup": { "storyPoints": 8, "estimatedCount": 2, "unestimatedCount": 0, "notEstimableCount": 1 },
                 "ado": { "id": 100, "rev": 4 } },
    "ado-200": { "id": "ado-200", "type": "programObjective", "title": "Cut checkout drop-off by 15%", "state": "Active", "parent": "ado-100",
                 "rollup": { "storyPoints": 8, "estimatedCount": 2, "unestimatedCount": 0, "notEstimableCount": 1 },
                 "ado": { "id": 200, "rev": 2 } },
    "ado-300": { "id": "ado-300", "type": "feature", "title": "One-click card payment", "state": "Active", "parent": "ado-200",
                 "rollup": { "storyPoints": 8, "estimatedCount": 2, "unestimatedCount": 0, "notEstimableCount": 1 },
                 "ado": { "id": 300, "rev": 7 } },
    "ado-301": { "id": "ado-301", "type": "story", "title": "Store tokenized card", "state": "Active", "parent": "ado-300",
                 "iteration": "pi26-4-s1", "priority": 2, "storyPoints": 5, "ado": { "id": 301, "rev": 3 } },
    "ado-302": { "id": "ado-302", "type": "story", "title": "Pay with stored card", "state": "New", "parent": "ado-300",
                 "iteration": "pi26-4-s1", "priority": 2, "storyPoints": 3, "ado": { "id": 302, "rev": 1 } },
    "ado-303": { "id": "ado-303", "type": "problem", "title": "3DS timeout on mobile", "state": "Active", "parent": "ado-300",
                 "iteration": "pi26-4-s1", "priority": 1, "storyPoints": null, "ado": { "id": 303, "rev": 2 } },
    "new-refund-flow": { "id": "new-refund-flow", "type": "story", "title": "Refund to stored card", "state": "Removed", "parent": "ado-300",
                 "priority": 3, "storyPoints": 8 }
  },
  "sync": { "lastPullAt": "2026-10-24T09:00:00Z", "lastPushAt": null, "scopeWiql": null }
}
```

Feature `ado-300` has an effort of **8** (5 + 3). The Problem `ado-303` is counted in `notEstimableCount`, and the Removed story is excluded. The `sync.base` blocks are left out of this example for brevity; a real pulled store would carry them.
