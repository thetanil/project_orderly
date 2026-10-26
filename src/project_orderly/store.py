"""In-memory backlog store: open, mutate (one operation path), undo/redo, save, merge.

Every edit is an *operation* (``set``, ``create``, ``put``, ``delete``, ``move``,
``renumber``, ``assign``, ``section`` or a ``batch`` of these). ``Store.apply`` runs
it, recomputes rollups and records one undo step. Validation is a pure function of
the store (see ``validator``); autosave lives here because it needs the merge base.
"""

from __future__ import annotations

import copy
import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import validator
from .rollup import LEVELS, category, children_index, compute_rollups, level_index, type_info

SCHEMA_MAJOR = "2"
SCHEMA_VERSION = "2.0.0"
STATE_DIR = ".backlogdesk"
SECTIONS = ("schemaVersion", "project", "model", "people", "iterations")
EDITABLE = (
    "title", "state", "priority", "storyPoints", "iteration", "assignedTo", "tags",
    "description", "acceptanceCriteria", "localNotes", "areaPath", "businessValue",
    "timeCriticality", "targetDate",
)
HISTORY_LIMIT = 500
MIN_GAP = 1e-6


class StoreError(Exception):
    """The store file cannot be opened (unreadable, invalid JSON, wrong version, bad structure)."""


class OpError(Exception):
    """An operation was refused; nothing changed."""


@dataclass
class Applied:
    changed: List[str] = field(default_factory=list)  # ids whose item (or rollup) changed or was created
    deleted: List[str] = field(default_factory=list)
    created: List[str] = field(default_factory=list)
    skipped: List[Dict[str, str]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.changed or self.deleted)


def _num(v: float) -> Any:
    return int(v) if float(v) == int(v) else float(v)


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "item"


def parse_store_text(text: str, source: str = "file") -> Dict[str, Any]:
    """Parse and check version + structure; raises StoreError with a readable message."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise StoreError(f"{source} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})")
    if not isinstance(data, dict):
        raise StoreError(f"{source} must contain a JSON object")
    v = data.get("schemaVersion")
    if v is None:
        raise StoreError(f"{source} has no schemaVersion; this version of Backlog Desk reads schema {SCHEMA_MAJOR}.x")
    if not isinstance(v, str) or v.split(".")[0] != SCHEMA_MAJOR:
        raise StoreError(f"{source} has unsupported schemaVersion {v!r}; this version of Backlog Desk reads schema {SCHEMA_MAJOR}.x")
    errs = validator.structure_issues(data)
    if errs:
        shown = "; ".join(
            f"{e['itemId'] + ': ' if e['itemId'] else ''}{(e['field'] + ': ') if e['field'] else ''}{e['message']}" for e in errs[:5]
        )
        more = f" (and {len(errs) - 5} more)" if len(errs) > 5 else ""
        raise StoreError(f"{source} does not match the store schema: {shown}{more}")
    return data


def atomic_write(path: Path, text: str) -> None:
    """Write via temp file then rename, so a crash never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _core(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """An item without its derived rollup (what merges compare)."""
    if item is None:
        return None
    return {k: v for k, v in item.items() if k != "rollup"}


class Store:
    def __init__(self, data: Dict[str, Any], path: Optional[Path] = None):
        data = copy.deepcopy(data)
        self.schema_version: str = data.get("schemaVersion", SCHEMA_VERSION)
        self.project: Dict[str, Any] = data.get("project", {})
        self.model: Dict[str, Any] = data["model"]
        self.people: Dict[str, Any] = data.get("people", {})
        self.iterations: Dict[str, Any] = data.get("iterations", {})
        self.items: Dict[str, Dict[str, Any]] = data["items"]
        self.path: Optional[Path] = Path(path) if path else None
        self.dirty = False
        self.conflicts: List[Dict[str, Any]] = []
        self.external_error: Optional[str] = None
        self.save_error: Optional[str] = None
        self.last_valid: Optional[Dict[str, Any]] = None
        self._undo: List[Dict[str, Any]] = []
        self._redo: List[Dict[str, Any]] = []
        self._kids: Dict[Optional[str], List[str]] = {}
        self._issues: Optional[List[Dict[str, Any]]] = None
        self._structure = validator.StructureCache()
        self._base: Dict[str, Any] = {}
        self._saved_canon: Optional[str] = None
        self._disk_text: Optional[str] = None
        self._sig: Optional[Tuple[int, int]] = None
        self.reindex()
        self.rollups_changed = bool(self._recompute())
        self.dirty = self.rollups_changed
        self._base = self._snapshot()

    # -- construction --------------------------------------------------
    @classmethod
    def open(cls, path: Path) -> "Store":
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise StoreError(f"cannot read {path}: {getattr(e, 'strerror', None) or e}")
        data = parse_store_text(text, str(path))
        store = cls(data, path)
        store._remember_disk(text, data)
        store._base = store._snapshot(data)
        try:
            lv = json.loads((store.state_dir / "last-valid.json").read_text(encoding="utf-8"))
            store.last_valid = lv if isinstance(lv, dict) else None
        except (OSError, ValueError):
            store.last_valid = None
        return store

    @property
    def state_dir(self) -> Path:
        assert self.path is not None
        return self.path.parent / STATE_DIR

    # -- structure -----------------------------------------------------
    def reindex(self) -> None:
        self._kids = children_index(self.items)
        self._issues = None

    def children(self, iid: Optional[str]) -> List[str]:
        return list(self._kids.get(iid, []))

    def ancestors(self, iid: str) -> List[str]:
        out, seen, cur = [], {iid}, self.items.get(iid, {}).get("parent")
        while cur is not None and cur in self.items and cur not in seen:
            out.append(cur)
            seen.add(cur)
            cur = self.items[cur].get("parent")
        return out

    def level(self, item: Dict[str, Any]) -> str:
        return self.model["types"][item["type"]]["level"]

    def category(self, item: Dict[str, Any]) -> str:
        return category(self.model, item)

    def removed_state(self, type_: str) -> str:
        for s, c in self.model["types"][type_]["states"].items():
            if c == "Removed":
                return s
        raise OpError(f"type {type_} has no Removed state")

    def default_state(self, type_: str) -> str:
        states = self.model["types"][type_]["states"]
        return next((s for s, c in states.items() if c == "Proposed"), next(iter(states)))

    def parent_level(self, type_: str) -> Optional[str]:
        i = LEVELS.index(self.model["types"][type_]["level"])
        return LEVELS[i - 1] if i > 0 else None

    def parent_candidates(self, type_: str) -> List[str]:
        """Ids that are exactly one level above ``type_`` (never removed ones)."""
        lvl = self.parent_level(type_)
        if lvl is None:
            return []
        return [i for i, it in self.items.items() if it["type"] in self.model["types"] and self.level(it) == lvl and self.category(it) != "Removed"]

    # -- rollup --------------------------------------------------------
    def _recompute(self) -> Dict[str, Any]:
        """Overwrite stored rollups with recomputed ones; returns {id: old rollup} for changed ones."""
        want = compute_rollups(self.model, self.items, self._kids)
        changed: Dict[str, Any] = {}
        for iid, item in self.items.items():
            new = want.get(iid)
            old = item.get("rollup")
            if new != old:
                changed[iid] = old
                if new is None:
                    item.pop("rollup", None)
                else:
                    item["rollup"] = new
        return changed

    # -- validation ----------------------------------------------------
    def data(self) -> Dict[str, Any]:
        d: Dict[str, Any] = dict(schemaVersion=self.schema_version)
        if self.project:
            d["project"] = self.project
        d.update(model=self.model, people=self.people, iterations=self.iterations, items=self.items)
        return d

    def issues(self) -> List[Dict[str, Any]]:
        if self._issues is None:
            self._issues = validator.validate(self.data(), self.last_valid, self._structure)
        return self._issues

    def error_count(self) -> int:
        return validator.counts(self.issues())["errors"]

    # -- operations ----------------------------------------------------
    def apply(self, op: Dict[str, Any]) -> Applied:
        """Run an operation, recompute rollups, record one undo step."""
        before: Dict[str, Optional[Dict[str, Any]]] = {}
        sections_before: Dict[str, Any] = {}

        def snap(iid: str) -> None:
            if iid not in before:
                it = self.items.get(iid)
                before[iid] = copy.deepcopy(it) if it is not None else None

        def snap_section(name: str) -> None:
            if name not in sections_before:
                sections_before[name] = copy.deepcopy(self._section(name))

        res = Applied()
        try:
            for o in self._flatten(op):
                self._apply_one(o, snap, snap_section, res)
        except OpError:
            # roll back a partially applied batch
            for iid, b in before.items():
                if b is None:
                    self.items.pop(iid, None)
                else:
                    self.items[iid] = b
            for name, v in sections_before.items():
                self._set_section(name, v)
            self.reindex()
            self._recompute()
            raise
        self.reindex()
        for iid, old in self._recompute().items():
            if iid not in before:
                it = self.items[iid]
                prev = copy.deepcopy(it)
                if old is None:
                    prev.pop("rollup", None)
                else:
                    prev["rollup"] = old
                before[iid] = prev
        self._structure.invalidate(before)
        if sections_before:
            self._structure.invalidate()
        entry_items = {}
        for iid, b in before.items():
            a = self.items.get(iid)
            if b != a:
                entry_items[iid] = (b, copy.deepcopy(a) if a is not None else None)
        entry_sections = {n: (b, copy.deepcopy(self._section(n))) for n, b in sections_before.items() if b != self._section(n)}
        res.changed = [i for i in entry_items if i in self.items]
        res.deleted = [i for i, (b, a) in entry_items.items() if a is None]
        if entry_items or entry_sections:
            self._push({"items": entry_items, "sections": entry_sections})
            self.dirty = True
            self._issues = None
        return res

    def _flatten(self, op: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        if op.get("op") == "batch":
            for o in op["ops"]:
                yield from self._flatten(o)
        else:
            yield op

    def _section(self, name: str) -> Any:
        return {"schemaVersion": self.schema_version, "project": self.project, "model": self.model,
                "people": self.people, "iterations": self.iterations}[name]

    def _set_section(self, name: str, value: Any) -> None:
        if name == "schemaVersion":
            self.schema_version = value
        elif name == "project":
            self.project = value
        elif name == "model":
            self.model = value
        elif name == "people":
            self.people = value
        elif name == "iterations":
            self.iterations = value
        else:
            raise OpError(f"unknown section {name}")

    def _push(self, entry: Dict[str, Any]) -> None:
        self._undo.append(entry)
        del self._undo[:-HISTORY_LIMIT]
        self._redo.clear()

    def _apply_one(self, o: Dict[str, Any], snap, snap_section, res: Applied) -> None:
        kind = o.get("op")
        if kind == "set":
            iid = o["id"]
            item = self._get(iid)
            snap(iid)
            self._set_field(item, o["field"], o.get("value"))
        elif kind == "create":
            item = self.build_item(o["type"], o.get("title", ""), o.get("parent"), o.get("key"), o.get("fields"))
            snap(item["id"])
            self.items[item["id"]] = item
            res.created.append(item["id"])
            self.reindex()
        elif kind == "put":
            item = copy.deepcopy(o["item"])
            snap(item["id"])
            self.items[item["id"]] = item
            res.created.append(item["id"])
            self.reindex()
        elif kind == "delete":
            iid = o["id"]
            item = self._get(iid)
            if item.get("remotes"):
                raise OpError("a synced item cannot be deleted; remove it instead (sets a Removed state)")
            if self._kids.get(iid):
                raise OpError("item has children; move or delete them first")
            snap(iid)
            del self.items[iid]
            self.reindex()
        elif kind == "move":
            self._move(o, snap)
        elif kind == "renumber":
            self._renumber(o.get("parent"), snap)
        elif kind == "assign":  # raw field assignment for merges (field None = whole item)
            iid, f = o["id"], o.get("field")
            if f is None:
                snap(iid)
                if o.get("value") is None:
                    self.items.pop(iid, None)
                else:
                    self.items[iid] = copy.deepcopy(o["value"])
            else:
                item = self._get(iid)
                snap(iid)
                if o.get("value") is None:
                    item.pop(f, None)
                else:
                    item[f] = copy.deepcopy(o["value"])
            self.reindex()
        elif kind == "section":
            snap_section(o["name"])
            self._set_section(o["name"], copy.deepcopy(o["value"]))
        else:
            raise OpError(f"unknown operation {kind!r}")

    def _get(self, iid: str) -> Dict[str, Any]:
        item = self.items.get(iid)
        if item is None:
            raise OpError(f"no such item: {iid}")
        return item

    # -- field edits ---------------------------------------------------
    def _set_field(self, item: Dict[str, Any], f: str, value: Any) -> None:
        if f not in EDITABLE:
            raise OpError(f"field is not editable: {f}")
        value = self.coerce(item, f, value)
        if value is None:
            item.pop(f, None)
        else:
            item[f] = value
        if f in ("state", "storyPoints", "priority"):
            self._issues = None

    def coerce(self, item: Dict[str, Any], f: str, value: Any) -> Any:
        info = type_info(self.model, item)
        if info is None:
            raise OpError(f"item {item['id']} has unknown type {item['type']!r}")
        blank = value is None or (isinstance(value, str) and value.strip() == "")
        if f == "title":
            if blank:
                raise OpError("title cannot be empty")
            return str(value).strip()
        if f == "state":
            if value not in info["states"]:
                raise OpError(f"{value!r} is not a state of {item['type']}")
            return value
        if f == "priority":
            if blank:
                return None
            try:
                p = int(float(value))
            except (TypeError, ValueError):
                raise OpError("priority must be a number 1-4")
            if not 1 <= p <= 4:
                raise OpError("priority must be between 1 and 4")
            return p
        if f in ("storyPoints", "businessValue", "timeCriticality"):
            if blank:
                return None
            try:
                n = float(value)
            except (TypeError, ValueError):
                raise OpError(f"{f} must be a number")
            if f == "storyPoints":
                if info["estimation"] == "forbidden":
                    raise OpError("story points are not allowed on this type")
                if n < 0:
                    raise OpError("story points cannot be negative")
            return _num(n)
        if f == "iteration":
            if blank:
                return None
            if value not in self.iterations:
                raise OpError(f"unknown iteration {value!r}")
            return value
        if f == "tags":
            raw = value if isinstance(value, (list, tuple)) else ([] if blank else str(value).split(","))
            tags: List[str] = []
            for t in raw:
                t = str(t).strip()
                if t and t not in tags:
                    tags.append(t)
            return tags or None
        # assignedTo, areaPath, targetDate and the Markdown blocks
        if blank:
            return None
        if not isinstance(value, str):
            raise OpError(f"{f} must be text")
        return value

    # -- create --------------------------------------------------------
    def suggest_key(self, title: str) -> str:
        base = "new-" + slugify(title)
        key, n = base, 1
        while key in self.items:
            n += 1
            key = f"{base}-{n}"
        return key

    def build_item(self, type_: str, title: str, parent: Optional[str], key: Optional[str] = None,
                   fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        info = self.model["types"].get(type_)
        if info is None:
            raise OpError(f"unknown type {type_!r}")
        title = (title or "").strip()
        if not title:
            raise OpError("title cannot be empty")
        self._check_parent(type_, parent)
        if key:
            if not re.fullmatch(r"new-[a-z0-9][a-z0-9-]*", key):
                raise OpError("key must look like new-<slug> (lowercase letters, digits, dashes)")
            if key in self.items:
                raise OpError(f"key {key} already exists")
        else:
            key = self.suggest_key(title)
        siblings = [self.items[i].get("rank", 0) for i in self._kids.get(parent, []) if i in self.items]
        item: Dict[str, Any] = dict(id=key, type=type_, title=title, state=self.default_state(type_), parent=parent,
                                    rank=_num(max(siblings) + 1) if siblings else 1)
        if info["priority"] == "required":
            item["priority"] = 2
        for f, v in (fields or {}).items():
            tmp = dict(item)
            val = self.coerce(tmp, f, v) if f in EDITABLE else None
            if val is not None:
                item[f] = val
        return item

    def _check_parent(self, type_: str, parent: Optional[str]) -> None:
        want = self.parent_level(type_)
        if want is None:
            if parent is not None:
                raise OpError("an epic has no parent")
            return
        p = self.items.get(parent) if parent is not None else None
        if p is None:
            raise OpError(f"{self.model['types'][type_]['label']} needs a parent (one level above)")
        pinfo = type_info(self.model, p)
        if pinfo is None or pinfo["level"] != want:
            raise OpError(f"parent must be a {want}, not {pinfo['level'] if pinfo else 'an unknown type'}")

    # -- move / rank ---------------------------------------------------
    def _move(self, o: Dict[str, Any], snap) -> None:
        iid, parent = o["id"], o.get("parent")
        item = self._get(iid)
        self._check_parent(item["type"], parent)
        if parent == iid or parent in self._descendants(iid):
            raise OpError("cannot move an item under itself")
        sibs = [i for i in self._kids.get(parent, []) if i != iid]
        index = len(sibs) if o.get("index") is None else max(0, min(int(o["index"]), len(sibs)))
        prev = self.items[sibs[index - 1]].get("rank", 0) if index > 0 else None
        nxt = self.items[sibs[index]].get("rank", 0) if index < len(sibs) else None
        if prev is None and nxt is None:
            rank: float = 1
        elif prev is None:
            rank = nxt - 1
        elif nxt is None:
            rank = prev + 1
        else:
            rank = (prev + nxt) / 2
        snap(iid)
        if prev is not None and nxt is not None and nxt - prev < MIN_GAP * 2:
            order = sibs[:index] + [iid] + sibs[index:]
            for n, sid in enumerate(order, 1):
                snap(sid)
                self.items[sid]["rank"] = n
            item["parent"] = parent
        else:
            item["parent"] = parent
            item["rank"] = _num(rank)
        self.reindex()

    def _renumber(self, parent: Optional[str], snap) -> None:
        for n, sid in enumerate(self._kids.get(parent, []), 1):
            if self.items[sid].get("rank") != n:
                snap(sid)
                self.items[sid]["rank"] = n
        self.reindex()

    def _descendants(self, iid: str) -> set:
        out, stack = set(), [iid]
        while stack:
            for c in self._kids.get(stack.pop(), []):
                if c not in out:
                    out.add(c)
                    stack.append(c)
        return out

    # -- undo / redo ---------------------------------------------------
    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> Applied:
        if not self._undo:
            raise OpError("nothing to undo")
        entry = self._undo.pop()
        self._redo.append(entry)
        return self._restore(entry, 0)

    def redo(self) -> Applied:
        if not self._redo:
            raise OpError("nothing to redo")
        entry = self._redo.pop()
        self._undo.append(entry)
        return self._restore(entry, 1)

    def _restore(self, entry: Dict[str, Any], side: int) -> Applied:
        res = Applied()
        for iid, pair in entry["items"].items():
            target = pair[side]
            if target is None:
                self.items.pop(iid, None)
                res.deleted.append(iid)
            else:
                self.items[iid] = copy.deepcopy(target)
                res.changed.append(iid)
        for name, pair in entry["sections"].items():
            self._set_section(name, copy.deepcopy(pair[side]))
        self._structure.invalidate(list(entry["items"]) if not entry["sections"] else None)
        self.reindex()
        self._recompute()
        self.dirty = True
        return res

    # -- JSON Patch ----------------------------------------------------
    @staticmethod
    def to_patch(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """An undo-history entry as RFC 6902 JSON Patch (what M5/M6 will reuse)."""
        patch: List[Dict[str, Any]] = []
        for iid, (b, a) in entry["items"].items():
            base = f"/items/{iid.replace('~', '~0').replace('/', '~1')}"
            if b is None:
                patch.append(dict(op="add", path=base, value=a))
            elif a is None:
                patch.append(dict(op="remove", path=base))
            else:
                for k in sorted(set(b) | set(a)):
                    if b.get(k) == a.get(k):
                        continue
                    if k not in a:
                        patch.append(dict(op="remove", path=f"{base}/{k}"))
                    else:
                        patch.append(dict(op="add" if k not in b else "replace", path=f"{base}/{k}", value=a[k]))
        return patch

    @staticmethod
    def ops_from_patch(patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """JSON Patch over ``/items`` as a batch operation (replace/add field -> assign)."""
        ops: List[Dict[str, Any]] = []
        for p in patch:
            parts = [s.replace("~1", "/").replace("~0", "~") for s in p["path"].split("/")[1:]]
            if parts[0] != "items" or len(parts) not in (2, 3):
                raise OpError(f"unsupported patch path {p['path']}")
            iid, f = parts[1], parts[2] if len(parts) == 3 else None
            value = None if p["op"] == "remove" else p["value"]
            ops.append(dict(op="assign", id=iid, field=f, value=value))
        return dict(op="batch", ops=ops)

    # -- persistence ---------------------------------------------------
    def _snapshot(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        d = copy.deepcopy(data) if data is not None else copy.deepcopy(self.data())
        return dict(items={k: _core(v) for k, v in d["items"].items()},
                    sections={n: d.get(n, {} if n != "schemaVersion" else SCHEMA_VERSION) for n in SECTIONS})

    def serialize(self) -> str:
        d = self.data()
        d = dict(d, items={k: d["items"][k] for k in sorted(d["items"])})
        return json.dumps(d, indent=2, ensure_ascii=False) + "\n"

    @staticmethod
    def canonical(data: Dict[str, Any]) -> str:
        items = data.get("items", {})
        d = {k: v for k, v in data.items() if k != "items"}
        d["items"] = {k: items[k] for k in sorted(items)}
        return json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True)

    def _remember_disk(self, text: str, data: Dict[str, Any]) -> None:
        self._disk_text = text
        self._saved_canon = self.canonical(data)
        try:
            st = self.path.stat()  # type: ignore[union-attr]
            self._sig = (st.st_mtime_ns, st.st_size)
        except OSError:
            self._sig = None

    def save(self) -> None:
        """Atomically write the store, then keep the written content as the last-valid snapshot."""
        assert self.path is not None
        text = self.serialize()
        atomic_write(self.path, text)
        data = json.loads(text)
        self._remember_disk(text, data)
        self._base = self._snapshot(data)
        self.dirty = False
        self.save_error = None
        try:
            atomic_write(self.state_dir / "last-valid.json", text)
            self.last_valid = data
            self._issues = None
        except OSError as e:
            self.save_error = f"saved, but could not update {STATE_DIR}/last-valid.json: {e}"

    def status(self) -> Dict[str, Any]:
        c = validator.counts(self.issues())
        if self.path is None:
            state = "memory"
        elif self.conflicts:
            state = "conflicts"
        elif self.external_error:
            state = "external-error"
        elif c["errors"]:
            state = "errors"
        elif self.save_error and self.dirty:
            state = "save-failed"
        elif self.dirty:
            state = "unsaved"
        else:
            state = "saved"
        return dict(state=state, errors=c["errors"], warnings=c["warnings"], conflicts=len(self.conflicts),
                    message=self.external_error or self.save_error)

    def autosave(self) -> Optional[Dict[str, Any]]:
        """Save if clean and quiet. Merges an external edit first. Returns the merge (or None)."""
        merged = None
        if self.path is None:
            return None
        if self.disk_changed():
            merged = self.merge_external()
        if self.conflicts or self.external_error or not self.dirty or self.error_count():
            return merged
        try:
            self.save()
        except OSError as e:
            self.save_error = f"could not save: {e}"
        return merged

    # -- external changes ----------------------------------------------
    def disk_changed(self) -> bool:
        if self.path is None:
            return False
        try:
            st = self.path.stat()
        except OSError:
            return False
        if self._sig == (st.st_mtime_ns, st.st_size):
            return False
        try:
            text = self.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        if text == self._disk_text:
            self._sig = (st.st_mtime_ns, st.st_size)
            return False
        return True

    def merge_external(self) -> Optional[Dict[str, Any]]:
        """3-way merge of the file on disk into memory (base = last loaded/saved).

        Returns {"changed", "deleted", "conflicts"}, or None when the file is unreadable
        (the message is kept in ``external_error`` and autosave stays paused).
        """
        assert self.path is not None
        try:
            text = self.path.read_text(encoding="utf-8")
            theirs = parse_store_text(text, str(self.path))
        except (OSError, UnicodeDecodeError, StoreError) as e:
            self.external_error = f"{self.path.name} changed on disk but cannot be read yet: {e}"
            self._issues = None
            return None
        self.external_error = None
        base_items = self._base["items"]
        their_items = {k: _core(v) for k, v in theirs["items"].items()}
        ops: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []
        for iid in list(dict.fromkeys(list(self.items) + list(their_items) + list(base_items))):
            b, t = base_items.get(iid), their_items.get(iid)
            m = _core(self.items.get(iid))
            if m == t:
                continue
            if m == b:  # only theirs changed
                ops.append(dict(op="assign", id=iid, field=None, value=copy.deepcopy(t)))
            elif t == b:  # only mine changed
                continue
            elif m is None or t is None:
                conflicts.append(dict(itemId=iid, field=None, mine=m, theirs=t))
            else:
                bb = b or {}
                for f in sorted(set(m) | set(t) | set(bb)):
                    fm, ft, fb = m.get(f), t.get(f), bb.get(f)
                    if fm == ft:
                        continue
                    if fm == fb:
                        ops.append(dict(op="assign", id=iid, field=f, value=copy.deepcopy(ft)))
                    elif ft == fb:
                        continue
                    else:
                        conflicts.append(dict(itemId=iid, field=f, mine=fm, theirs=ft))
        for name in SECTIONS:
            if theirs.get(name, {} if name != "schemaVersion" else SCHEMA_VERSION) != self._section(name):
                ops.append(dict(op="section", name=name, value=copy.deepcopy(theirs.get(name, {}))))
        # a plain-reload merge may legitimately touch items that fail local coercion: use raw ops
        res = self.apply(dict(op="batch", ops=ops)) if ops else Applied()
        self.conflicts = conflicts
        self._remember_disk(text, theirs)
        self._base = self._snapshot(theirs)
        self.dirty = self.canonical(self.data()) != self._saved_canon
        self._issues = None
        return dict(changed=res.changed, deleted=res.deleted, conflicts=len(conflicts))

    def resolve_conflict(self, item_id: str, field_: Optional[str], choice: str) -> Applied:
        idx = next((i for i, c in enumerate(self.conflicts) if c["itemId"] == item_id and c["field"] == field_), None)
        if idx is None:
            raise OpError("no such conflict")
        c = self.conflicts[idx]
        res = Applied()
        if choice == "theirs":
            res = self.apply(dict(op="assign", id=item_id, field=field_, value=copy.deepcopy(c["theirs"])))
        elif choice != "mine":
            raise OpError("choice must be 'mine' or 'theirs'")
        del self.conflicts[idx]
        self.dirty = True
        self._issues = None
        return res


# -- sample + stress data -------------------------------------------------
def sample_data() -> Dict[str, Any]:
    return json.loads((Path(__file__).parent / "sample_backlog.json").read_text(encoding="utf-8"))


def stress_data(base: Dict[str, Any], n: int, seed: int = 1) -> Dict[str, Any]:
    """Generate exactly n valid items (n >= 1) under the base model for performance checks."""
    rnd = random.Random(seed)
    types = base["model"]["types"]
    items: Dict[str, Any] = {}
    counter = [10000]

    def add(iid: str, type_: str, title: str, parent: Optional[str], rank: int, **extra: Any) -> None:
        if len(items) >= n:
            return
        state = extra.pop("state", None) or rnd.choice(list(types[type_]["states"]))
        counter[0] += 1
        items[iid] = dict(id=iid, type=type_, title=title, state=state, parent=parent, rank=rank,
                          remotes=dict(ado=dict(id=counter[0], rev=1)), **extra)

    e = 0
    while len(items) < n:
        e += 1
        eid = f"ado-e{e}"
        add(eid, "businessEpic", f"Epic {e}", None, e, state="Active")
        for p in range(4):
            pid = f"{eid}-p{p}"
            add(pid, "programObjective", f"Objective {e}.{p}", eid, p, state="Active")
            for f in range(5):
                fid = f"{pid}-f{f}"
                add(fid, "feature", f"Feature {e}.{p}.{f}", pid, f, state="Active")
                for w in range(rnd.randint(3, 8)):
                    prob = rnd.random() < 0.15
                    sp = None if prob or rnd.random() < 0.2 else rnd.choice([1, 2, 3, 5, 8])
                    extra: Dict[str, Any] = dict(priority=rnd.randint(1, 4))
                    if sp is not None:
                        extra["storyPoints"] = sp
                    add(f"{fid}-w{w}", "problem" if prob else "story", f"{'Problem' if prob else 'Story'} {e}.{p}.{f}.{w}",
                        fid, w, state=rnd.choice(["New", "Active", "Closed"]), **extra)
    out = {k: v for k, v in base.items() if k != "items"}
    out["items"] = items
    return out
