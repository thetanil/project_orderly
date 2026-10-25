"""In-memory backlog store: load, mutate, roll up, validate.

Prototype subset of docs/deprecated/backlog-schema-design.md: rollups and
rules R2, R3, R4, R7, R8, R9 only.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

LEVELS = ["businessEpic", "programObjective", "feature", "workItem"]
EDITABLE = {"title", "state", "priority", "storyPoints", "description"}


class Store:
    def __init__(self, data: Dict[str, Any]):
        self.model: Dict[str, Any] = data["model"]
        self.items: Dict[str, Dict[str, Any]] = data["items"]
        self.iterations: Dict[str, Any] = data.get("iterations", {})
        self.dirty = False
        self._children: Dict[Optional[str], List[str]] = {}
        self.reindex()
        self.recompute()

    @classmethod
    def open(cls, path: Path) -> "Store":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    # -- structure -----------------------------------------------------
    def reindex(self) -> None:
        kids: Dict[Optional[str], List[str]] = {}
        for item in self.items.values():
            kids.setdefault(item.get("parent"), []).append(item["id"])
        for ids in kids.values():
            ids.sort(key=lambda i: self.items[i].get("rank", 0))
        self._children = kids

    def level(self, item: Dict[str, Any]) -> str:
        return self.model["types"][item["type"]]["level"]

    def category(self, item: Dict[str, Any]) -> str:
        return self.model["types"][item["type"]]["states"].get(item["state"], "Proposed")

    # -- rollup --------------------------------------------------------
    def recompute(self) -> None:
        def roll(iid: str) -> Dict[str, Any]:
            item = self.items[iid]
            total = dict(storyPoints=0, estimatedCount=0, unestimatedCount=0, notEstimableCount=0)
            for cid in self._children.get(iid, []):
                child = self.items[cid]
                if self.category(child) == "Removed":
                    continue
                if self.level(child) == "workItem":
                    if self.model["types"][child["type"]]["estimation"] == "forbidden":
                        total["notEstimableCount"] += 1
                    elif child.get("storyPoints") is None:
                        total["unestimatedCount"] += 1
                    else:
                        total["storyPoints"] += child["storyPoints"]
                        total["estimatedCount"] += 1
                else:
                    sub = roll(cid)
                    for k in total:
                        total[k] += sub[k]
            if self.level(item) != "workItem":
                item["rollup"] = total
            return total

        for rid in self._children.get(None, []):
            roll(rid)

    # -- validation ----------------------------------------------------
    def issues(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        types = self.model["types"]

        def add(rule: str, level: str, item: Dict[str, Any], msg: str) -> None:
            out.append(dict(rule=rule, level=level, itemId=item["id"], message=msg))

        for item in self.items.values():
            cfg = types.get(item["type"])
            if cfg is None:
                add("R2", "E", item, f"unknown type {item['type']}")
                continue
            if item["state"] not in cfg["states"]:
                add("R3", "E", item, f"state {item['state']!r} not valid for {item['type']}")
            parent = item.get("parent")
            if parent is not None:
                p = self.items.get(parent)
                if p is None:
                    add("R4", "E", item, f"parent {parent} not found")
                elif LEVELS.index(self.level(p)) != LEVELS.index(cfg["level"]) - 1:
                    add("R4", "E", item, "parent is not exactly one level above")
            sp = item.get("storyPoints")
            if cfg["estimation"] == "forbidden" and sp is not None:
                add("R7", "E", item, "story points not allowed on this type")
            if cfg["estimation"] == "required" and sp is None and self.category(item) != "Removed":
                add("R8", "W", item, "missing estimate")
            if cfg["priority"] == "required" and item.get("priority") is None:
                add("R9", "E", item, "priority required")
        return out

    # -- mutation ------------------------------------------------------
    def update(self, iid: str, field: str, value: Any) -> List[str]:
        """Set one field; returns ids whose derived data changed (item + ancestors)."""
        if field not in EDITABLE:
            raise ValueError(f"field not editable: {field}")
        item = self.items[iid]
        if field in ("priority", "storyPoints"):
            value = None if value in (None, "") else float(value)
            if field == "priority" and value is not None:
                value = int(value)
            elif value is not None and value == int(value):
                value = int(value)
        item[field] = value
        self.dirty = True
        self.recompute()
        changed, cur = [], iid
        while cur is not None:
            changed.append(cur)
            cur = self.items[cur].get("parent")
        return changed

    def save(self, path: Path) -> None:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(dict(model=self.model, iterations=self.iterations, items=self.items), indent=2), encoding="utf-8")
        tmp.replace(path)
        self.dirty = False


def stress_data(base: Dict[str, Any], n: int, seed: int = 1) -> Dict[str, Any]:
    """Generate ~n items under the base model for performance checks."""
    rnd = random.Random(seed)
    items: Dict[str, Any] = {}
    states = ["New", "Active", "Resolved", "Closed"]
    count = 0
    e = 0
    while count < n:
        e += 1
        eid = f"ado-e{e}"
        items[eid] = dict(id=eid, type="businessEpic", title=f"Epic {e}", state="Active", parent=None, rank=e)
        count += 1
        for p in range(4):
            pid = f"{eid}-p{p}"
            items[pid] = dict(id=pid, type="programObjective", title=f"Objective {e}.{p}", state="Active", parent=eid, rank=p)
            count += 1
            for f in range(5):
                fid = f"{pid}-f{f}"
                items[fid] = dict(id=fid, type="feature", title=f"Feature {e}.{p}.{f}", state="Active", parent=pid, rank=f)
                count += 1
                for w in range(rnd.randint(3, 8)):
                    wid = f"{fid}-w{w}"
                    prob = rnd.random() < 0.15
                    items[wid] = dict(
                        id=wid, type="problem" if prob else "story", parent=fid, rank=w,
                        title=f"{'Problem' if prob else 'Story'} {e}.{p}.{f}.{w}",
                        state=rnd.choice(states), priority=rnd.randint(1, 4),
                        storyPoints=None if prob or rnd.random() < 0.2 else rnd.choice([1, 2, 3, 5, 8]),
                    )
                    count += 1
    return dict(model=base["model"], iterations=base.get("iterations", {}), items=items)
