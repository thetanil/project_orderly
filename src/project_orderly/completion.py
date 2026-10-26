"""In-memory completion index: fuzzy-ranked suggestions for items, people, iterations, tags."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .rollup import LEVELS, category

CURRENT_USER_BONUS = 5.0


def score(q: str, text: str) -> Optional[float]:
    """Higher is better; None when ``q`` does not match ``text`` (both lowercase)."""
    if not q:
        return 1.0
    if text == q:
        return 100.0
    if text.startswith(q):
        return 90.0 - len(text) * 0.01
    pos = text.find(q)
    if pos >= 0:
        boundary = pos == 0 or not text[pos - 1].isalnum()
        return (80.0 if boundary else 60.0) - pos * 0.1
    # subsequence, tighter spans rank higher
    i = start = -1
    for ch in q:
        i = text.find(ch, i + 1)
        if i < 0:
            return None
        if start < 0:
            start = i
    return max(1.0, 40.0 - (i - start) * 0.5)


class CompletionIndex:
    def __init__(self, store: Any):
        self.store = store
        self.rebuild()

    def rebuild(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}
        self._tags: Counter = Counter()
        self._item_tags: Dict[str, Tuple[str, ...]] = {}
        self.refresh(list(self.store.items))

    def refresh(self, ids: Iterable[str]) -> None:
        """Incrementally update entries for the given item ids (changed, created or deleted)."""
        s = self.store
        for iid in ids:
            for t in self._item_tags.pop(iid, ()):
                self._tags[t] -= 1
                if self._tags[t] <= 0:
                    del self._tags[t]
            self._items.pop(iid, None)
            it = s.items.get(iid)
            if it is None:
                continue
            info = s.model["types"].get(it.get("type"))
            self._items[iid] = dict(
                id=iid, title=it.get("title", ""), type=it.get("type"), label=info["label"] if info else "?",
                level=info["level"] if info else None, removed=category(s.model, it) == "Removed",
                key=iid.lower(), tkey=it.get("title", "").lower(),
            )
            tags = tuple(it.get("tags") or ())
            self._item_tags[iid] = tags
            for t in tags:
                self._tags[t] += 1

    def suggest(self, kind: str, query: str = "", limit: int = 20, for_type: Optional[str] = None,
                current_user: Optional[str] = None) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        scored: List[Tuple[float, int, Dict[str, Any]]] = []
        if kind == "item":
            want = None
            if for_type is not None:
                want = self.store.parent_level(for_type)
                if want is None:
                    return []
            for e in self._items.values():
                if want is not None and (e["level"] != want or e["removed"]):
                    continue
                a, b = score(q, e["key"]), score(q, e["tkey"])
                best = max((x for x in (a, b) if x is not None), default=None)
                if best is not None:
                    scored.append((best - (50 if e["removed"] else 0), len(e["tkey"]), dict(id=e["id"], title=e["title"], type=e["type"], label=e["label"])))
        elif kind == "person":
            people = {pid: p.get("name", pid) for pid, p in self.store.people.items()}
            for it in self.store.items.values():
                a = it.get("assignedTo")
                if a and a not in people:
                    people[a] = a
            for pid, name in people.items():
                best = max((x for x in (score(q, pid.lower()), score(q, name.lower())) if x is not None), default=None)
                if best is not None:
                    bonus = CURRENT_USER_BONUS if pid == current_user else 0
                    scored.append((best + bonus, len(name), dict(id=pid, name=name)))
        elif kind == "iteration":
            for iid, it in self.store.iterations.items():
                best = max((x for x in (score(q, iid.lower()), score(q, it.get("name", "").lower()), score(q, it.get("path", "").lower())) if x is not None), default=None)
                if best is not None:
                    scored.append((best, len(it.get("name", "")), dict(id=iid, name=it.get("name"), path=it.get("path"))))
        elif kind == "tag":
            for t, n in self._tags.items():
                sc = score(q, t.lower())
                if sc is not None:
                    scored.append((sc + min(n, 50) * 0.01, len(t), dict(tag=t, count=n)))
        else:
            raise ValueError(f"unknown suggestion kind {kind!r}")
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [e for _, _, e in scored[:limit]]
