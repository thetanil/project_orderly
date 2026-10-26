"""Validator: pure function from a store (plus optional last-valid snapshot) to issues.

Structural JSON Schema errors come first (rule ``SCHEMA``), then rules R1-R13 and
R21-R25 (v2 numbering). R14-R17 are reserved and R18-R20 are deferred.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .markdown import MARKDOWN_FIELDS, has_html
from .rollup import LEVELS, category, children_index, compute_rollups

SCHEMA_PATH = Path(__file__).parent / "backlog.schema.json"

Issue = Dict[str, Any]

# quick-fix identifiers (see Api.quick_fix)
FIX_BY_RULE = {
    "R4": "pick-parent",
    "R5": "pick-parent",
    "R7": "clear-points",
    "R8": "focus-field",
    "R9": "focus-field",
    "R21": "renumber",
    "R22": "html-to-markdown",
    "R24": "restore-removed",
}


def load_schema() -> Dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validators():
    from jsonschema import Draft202012Validator

    schema = load_schema()
    whole = Draft202012Validator(schema)
    top = dict(schema)
    top["properties"] = dict(schema["properties"], items={"type": "object"})
    item = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/item"}
    return whole, Draft202012Validator(top), Draft202012Validator(item)


def _map_errors(errors, prefix: List[str]) -> List[Issue]:
    out: List[Issue] = []
    for err in sorted(errors, key=lambda e: list(map(str, e.absolute_path))):
        path = prefix + [str(p) for p in err.absolute_path]
        item_id: Optional[str] = None
        field: Optional[str] = None
        if path[:1] == ["items"] and len(path) >= 2:
            item_id = path[1]
            field = path[2] if len(path) > 2 else None
        else:
            field = "/".join(path) or None
        if err.validator == "required" and isinstance(err.instance, dict):
            missing = [p for p in err.validator_value if p not in err.instance]
            if missing:
                field = missing[0] if item_id is not None or not field else field + "/" + missing[0]
        elif err.validator == "additionalProperties" and isinstance(err.instance, dict):
            props = (err.schema.get("properties") or {}).keys()
            extra = [k for k in err.instance if k not in props]
            if extra:
                field = extra[0] if item_id is not None or not field else field + "/" + extra[0]
        out.append(issue("SCHEMA", "E", item_id, field, err.message[:200]))
    return out


def structure_issues(data: Dict[str, Any]) -> List[Issue]:
    return _map_errors(_validators()[0].iter_errors(data), [])


class StructureCache:
    """Per-item structural results, so a 3000-item store is not re-checked on every edit."""

    def __init__(self) -> None:
        self.by_id: Dict[str, List[Issue]] = {}

    def invalidate(self, ids: Optional[Iterable[str]] = None) -> None:
        if ids is None:
            self.by_id.clear()
        else:
            for i in ids:
                self.by_id.pop(i, None)

    def issues(self, data: Dict[str, Any]) -> List[Issue]:
        _, top, item_v = _validators()
        out = _map_errors(top.iter_errors(data), [])
        items = data.get("items")
        if not isinstance(items, dict):
            return out
        for gone in [k for k in self.by_id if k not in items]:
            del self.by_id[gone]
        for iid, item in items.items():
            got = self.by_id.get(iid)
            if got is None:
                got = self.by_id[iid] = _map_errors(item_v.iter_errors(item), ["items", iid])
            out.extend(got)
        return out


def issue(rule: str, level: str, item_id: Optional[str], field: Optional[str], message: str) -> Issue:
    out: Issue = dict(rule=rule, level=level, itemId=item_id, field=field, message=message)
    fix = FIX_BY_RULE.get(rule)
    if fix and item_id is not None:
        out["fix"] = fix
    return out


def validate(data: Dict[str, Any], previous: Optional[Dict[str, Any]] = None, cache: Optional[StructureCache] = None) -> List[Issue]:
    out: List[Issue] = cache.issues(data) if cache is not None else structure_issues(data)
    model = data.get("model") or {}
    types = model.get("types") or {}
    items: Dict[str, Dict[str, Any]] = data.get("items") or {}
    iterations: Dict[str, Dict[str, Any]] = data.get("iterations") or {}
    custom_fields = model.get("customFields") or {}

    def add(rule: str, level: str, iid: Optional[str], field: Optional[str], msg: str) -> None:
        out.append(issue(rule, level, iid, field, msg))

    # R1 key == id (items, iterations)
    for key, item in items.items():
        if isinstance(item, dict) and item.get("id") != key:
            add("R1", "E", key, "id", f"map key {key!r} differs from id {item.get('id')!r}")
    for key, it in iterations.items():
        if isinstance(it, dict) and it.get("id") != key:
            add("R1", "E", key, "id", f"iteration key {key!r} differs from id {it.get('id')!r}")

    # R12 iterations
    paths: Dict[str, str] = {}
    for key, it in iterations.items():
        if not isinstance(it, dict):
            continue
        s, f = it.get("startDate"), it.get("finishDate")
        if s and f and f < s:
            add("R12", "E", key, "finishDate", "finishDate is before startDate")
        p = it.get("path")
        if p in paths:
            add("R12", "E", key, "path", f"path duplicates iteration {paths[p]}")
        elif p is not None:
            paths[p] = key

    kids = children_index({k: v for k, v in items.items() if isinstance(v, dict)})
    ado_ids: Dict[Any, str] = {}
    for key, item in items.items():
        if not isinstance(item, dict):
            continue
        cfg = types.get(item.get("type"))
        if cfg is None:
            add("R2", "E", key, "type", f"unknown type {item.get('type')!r}")
            continue
        if item.get("state") not in cfg["states"]:
            add("R3", "E", key, "state", f"state {item.get('state')!r} is not a state of {item['type']}")
        parent = item.get("parent")
        lvl = LEVELS.index(cfg["level"])
        if parent is not None:
            p = items.get(parent)
            if p is None:
                add("R4", "E", key, "parent", f"parent {parent} not found")
            elif lvl == 0:
                add("R4", "E", key, "parent", "an epic has no parent")
            else:
                pcfg = types.get(p.get("type"))
                if pcfg is None or LEVELS.index(pcfg["level"]) != lvl - 1:
                    add("R4", "E", key, "parent", "parent is not exactly one level above")
        elif lvl > 0:
            add("R5", "W", key, "parent", "orphan: no parent")
        if item.get("iteration") is not None and item["iteration"] not in iterations:
            add("R6", "E", key, "iteration", f"iteration {item['iteration']!r} not found")
        sp = item.get("storyPoints")
        if cfg["estimation"] == "forbidden" and sp is not None:
            add("R7", "E", key, "storyPoints", "story points are not allowed on this type")
        if cfg["estimation"] == "required" and sp is None and category(model, item) != "Removed":
            add("R8", "W", key, "storyPoints", "missing estimate")
        if cfg["priority"] == "required" and item.get("priority") is None:
            add("R9", "E", key, "priority", "priority is required")
        ado = ((item.get("remotes") or {}).get("ado") or {})
        if "id" in ado:
            if ado["id"] in ado_ids:
                add("R11", "E", key, "remotes", f"ADO id {ado['id']} also used by {ado_ids[ado['id']]}")
            else:
                ado_ids[ado["id"]] = key
        for name in item.get("custom") or {}:
            if name not in custom_fields:
                add("R13", "E", key, f"custom.{name}", f"custom field {name!r} is not declared")
        for f in MARKDOWN_FIELDS:
            v = item.get(f)
            if isinstance(v, str) and has_html(v):
                add("R22", "W", key, f, "raw HTML in a Markdown field")
        if ado.get("conflicts"):
            add("R23", "W", key, "remotes", f"{len(ado['conflicts'])} unresolved sync conflict(s)")

    # R21 duplicate rank among siblings
    for parent, ids in kids.items():
        seen: Dict[Any, str] = {}
        for iid in ids:
            r = items[iid].get("rank")
            if r in seen:
                add("R21", "W", iid, "rank", f"same rank as sibling {seen[r]}")
            else:
                seen[r] = iid

    # R10 stored rollup equals recomputed
    if types:
        try:
            expected = compute_rollups(model, {k: v for k, v in items.items() if isinstance(v, dict)}, kids)
        except (KeyError, TypeError):
            expected = {}
        for iid, want in expected.items():
            if items[iid].get("rollup") != want:
                add("R10", "E", iid, "rollup", "stored rollup differs from the recomputed value")

    # R24 / R25 against the last-valid snapshot
    if previous is not None:
        prev_items = previous.get("items") or {}
        for iid, old in prev_items.items():
            if (old.get("remotes") or {}) and iid not in items:
                add("R24", "E", iid, None, "synced item was deleted (set a Removed state instead)")
        for iid, new in items.items():
            if not isinstance(new, dict):
                continue
            old_remotes = (prev_items.get(iid) or {}).get("remotes") or {}
            if (new.get("remotes") or {}) != old_remotes:
                add("R25", "E", iid, "remotes", "remotes changed by something other than the sync")
    return out


def counts(issues: List[Issue]) -> Dict[str, int]:
    e = sum(1 for i in issues if i["level"] == "E")
    return dict(errors=e, warnings=len(issues) - e)
