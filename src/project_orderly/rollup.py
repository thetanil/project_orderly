"""Rollup: derived effort totals for every non-work-item (pure)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

LEVELS = ["businessEpic", "programObjective", "feature", "workItem"]
ZERO = dict(storyPoints=0, estimatedCount=0, unestimatedCount=0, notEstimableCount=0)


def children_index(items: Dict[str, Dict[str, Any]]) -> Dict[Optional[str], List[str]]:
    kids: Dict[Optional[str], List[str]] = {}
    for iid, item in items.items():
        kids.setdefault(item.get("parent"), []).append(iid)
    for ids in kids.values():
        ids.sort(key=lambda i: (items[i].get("rank", 0), i))
    return kids


def type_info(model: Dict[str, Any], item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return model.get("types", {}).get(item.get("type"))


def category(model: Dict[str, Any], item: Dict[str, Any]) -> str:
    info = type_info(model, item)
    if info is None:
        return "Proposed"
    return info["states"].get(item.get("state"), "Proposed")


def _num(v: float) -> Any:
    return int(v) if v == int(v) else v


def compute_rollups(
    model: Dict[str, Any], items: Dict[str, Dict[str, Any]], kids: Optional[Dict[Optional[str], List[str]]] = None
) -> Dict[str, Dict[str, Any]]:
    """Return {item id: rollup} for every item whose type is not a work item."""
    kids = children_index(items) if kids is None else kids
    out: Dict[str, Dict[str, Any]] = {}
    visiting = set()

    def roll(iid: str) -> Dict[str, Any]:
        if iid in out:
            return out[iid]
        total = dict(ZERO)
        if iid in visiting:  # cycle from hand-edited parents (reported by R4)
            return total
        visiting.add(iid)
        for cid in kids.get(iid, []):
            child = items[cid]
            info = type_info(model, child)
            if info is None or category(model, child) == "Removed":
                continue
            if info["level"] == "workItem":
                if info["estimation"] == "forbidden":
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
        visiting.discard(iid)
        total["storyPoints"] = _num(total["storyPoints"])
        info = type_info(model, items[iid])
        if info is not None and info["level"] != "workItem":
            out[iid] = total
        return total

    for iid in items:
        roll(iid)
    return out


def level_index(model: Dict[str, Any], item: Dict[str, Any]) -> int:
    info = type_info(model, item)
    return LEVELS.index(info["level"]) if info else -1
