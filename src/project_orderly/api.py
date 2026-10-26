"""The single API object exposed to the frontend (pywebview's ``js_api``).

Thin adapter over Store / Validator / CompletionIndex. Every mutating call returns the
changed items (the item and its ancestors), the full issue list and the save status in
one response. Private attributes keep the store out of the JS-visible surface.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .completion import CompletionIndex
from .markdown import html_to_markdown
from .settings import Settings
from .store import STATE_DIR, OpError, Store, StoreError, sample_data, stress_data

BULK_FIELDS = ("state", "iteration", "priority", "tags", "assignedTo")


def _guard(fn: Callable) -> Callable:
    """Turn refused operations and a missing store into ``{"ok": False, "error": ...}``."""

    @functools.wraps(fn)
    def wrapper(self: "Api", *a: Any, **kw: Any) -> Dict[str, Any]:
        if self._store is None:
            return dict(ok=False, error=self._error or "no backlog is open")
        try:
            return fn(self, *a, **kw)
        except OpError as e:
            return self._fail(str(e))

    return wrapper


class Api:
    """Methods exposed to the frontend as ``window.pywebview.api.*``."""

    def __init__(self, store: Optional[Store], error: Optional[str] = None):
        self._store = store
        self._error = error
        self._index = CompletionIndex(store) if store is not None else None
        folder = store.state_dir if store is not None and store.path is not None else None
        self._settings = Settings(folder)

    # -- responses -----------------------------------------------------
    def _state(self) -> Dict[str, Any]:
        s = self._store
        return dict(issues=s.issues(), dirty=s.dirty, status=s.status(), conflicts=s.conflicts,
                    canUndo=s.can_undo(), canRedo=s.can_redo())

    def _fail(self, msg: str) -> Dict[str, Any]:
        return dict(ok=False, error=msg, **self._state())

    def _finish(self, applied: Any, focus: List[str] = (), **extra: Any) -> Dict[str, Any]:
        s = self._store
        merged = s.autosave()
        ids: List[str] = []
        for f in focus:
            ids.extend([f, *s.ancestors(f)] if f in s.items else [])
        ids.extend(applied.changed)
        ids = list(dict.fromkeys(i for i in ids if i in s.items))
        out = dict(ok=True, items=[s.items[i] for i in ids], deleted=list(applied.deleted), **self._state(), **extra)
        if applied.skipped:
            out["skipped"] = applied.skipped
        if merged is not None:  # an external edit was merged during autosave: send everything
            self._index.rebuild()
            out["snapshot"] = self.snapshot()
        else:
            self._index.refresh([*applied.changed, *applied.deleted])
        return out

    # -- reads ---------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        s = self._store
        if s is None:
            return dict(error=self._error, settings=self._settings.values)
        return dict(
            project=s.project, model=s.model, people=s.people, iterations=s.iterations,
            items=list(s.items.values()), path=str(s.path) if s.path else None,
            settings=self._settings.values, error=None, **self._state(),
        )

    def suggest(self, kind: str, query: str = "", limit: int = 20, for_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._index is None:
            return []
        return self._index.suggest(kind, query, limit, for_type, self._settings.values.get("currentUser"))

    # -- settings ------------------------------------------------------
    def get_settings(self) -> Dict[str, Any]:
        return dict(self._settings.values)

    def set_setting(self, key: str, value: Any) -> Dict[str, Any]:
        try:
            self._settings.set(key, value, self._store.people if self._store else None)
        except ValueError as e:
            return dict(ok=False, error=str(e), settings=self._settings.values)
        return dict(ok=True, settings=self._settings.values)

    # -- edits ---------------------------------------------------------
    @_guard
    def set_field(self, iid: str, field: str, value: Any) -> Dict[str, Any]:
        return self._finish(self._store.apply(dict(op="set", id=iid, field=field, value=value)), [iid])

    update = set_field  # prototype name

    @_guard
    def bulk_set(self, ids: List[str], field: str, value: Any, mode: Optional[str] = None) -> Dict[str, Any]:
        """One batch (one undo step, one validation, one autosave); unsupported items are skipped and reported."""
        if field not in BULK_FIELDS:
            raise OpError(f"bulk edit supports {', '.join(BULK_FIELDS)}")
        s = self._store
        ops: List[Dict[str, Any]] = []
        skipped: List[Dict[str, str]] = []
        for iid in ids:
            item = s.items.get(iid)
            if item is None:
                skipped.append(dict(id=iid, reason="no such item"))
                continue
            v = value
            if field == "tags":
                cur = list(item.get("tags") or [])
                incoming = value if isinstance(value, list) else [t for t in str(value or "").split(",")]
                incoming = [t.strip() for t in incoming if t.strip()]
                mode = mode or "add"
                v = {"add": cur + [t for t in incoming if t not in cur], "remove": [t for t in cur if t not in incoming], "set": incoming}.get(mode)
                if v is None:
                    raise OpError("tag mode must be add, remove or set")
            try:
                s.coerce(item, field, v)
            except OpError as e:
                skipped.append(dict(id=iid, reason=str(e)))
                continue
            ops.append(dict(op="set", id=iid, field=field, value=v))
        applied = s.apply(dict(op="batch", ops=ops))
        applied.skipped = skipped
        return self._finish(applied, [o["id"] for o in ops])

    @_guard
    def suggest_key(self, title: str) -> Dict[str, Any]:
        return dict(ok=True, key=self._store.suggest_key(title))

    @_guard
    def create(self, type: str, title: str, parent: Optional[str] = None, key: Optional[str] = None) -> Dict[str, Any]:
        applied = self._store.apply(dict(op="create", type=type, title=title, parent=parent, key=key))
        return self._finish(applied, applied.created, created=applied.created[0], selectId=applied.created[0])

    @_guard
    def remove(self, iid: str) -> Dict[str, Any]:
        """Set the Removed state (works for synced and local items; never deletes)."""
        s = self._store
        item = s.items.get(iid)
        if item is None:
            raise OpError(f"no such item: {iid}")
        applied = s.apply(dict(op="set", id=iid, field="state", value=s.removed_state(item["type"])))
        return self._finish(applied, [iid])

    @_guard
    def delete(self, iid: str) -> Dict[str, Any]:
        """Really delete a never-synced item. A synced item is refused and set to Removed instead."""
        s = self._store
        item = s.items.get(iid)
        if item is None:
            raise OpError(f"no such item: {iid}")
        if item.get("remotes"):
            out = self.remove(iid)
            out.update(deletedForReal=False, note="synced items cannot be deleted; set to Removed instead")
            return out
        applied = s.apply(dict(op="delete", id=iid))
        parent = item.get("parent")
        return self._finish(applied, [parent] if parent else [], deletedForReal=True)

    @_guard
    def move(self, iid: str, parent: Optional[str], index: Optional[int] = None) -> Dict[str, Any]:
        applied = self._store.apply(dict(op="move", id=iid, parent=parent, index=index))
        return self._finish(applied, [iid])

    @_guard
    def undo(self) -> Dict[str, Any]:
        applied = self._store.undo()
        return self._finish(applied, applied.changed[:1], selectId=(applied.changed or [None])[0])

    @_guard
    def redo(self) -> Dict[str, Any]:
        applied = self._store.redo()
        return self._finish(applied, applied.changed[:1], selectId=(applied.changed or [None])[0])

    # -- quick fixes ---------------------------------------------------
    @_guard
    def quick_fix(self, rule: str, iid: str, field: Optional[str] = None, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        s = self._store
        args = args or {}
        found = next((i for i in s.issues() if i["rule"] == rule and i["itemId"] == iid and (field is None or i.get("field") == field)), None)
        if found is None:
            raise OpError("that problem no longer exists")
        fix = found.get("fix")
        item = s.items.get(iid)
        if fix == "clear-points":
            return self._finish(s.apply(dict(op="set", id=iid, field="storyPoints", value=None)), [iid])
        if fix == "renumber":
            return self._finish(s.apply(dict(op="renumber", parent=item.get("parent"))), [iid])
        if fix == "html-to-markdown":
            f = found["field"]
            return self._finish(s.apply(dict(op="set", id=iid, field=f, value=html_to_markdown(item[f]))), [iid])
        if fix == "restore-removed":
            old = (s.last_valid or {}).get("items", {}).get(iid)
            if old is None:
                raise OpError("no last-valid copy of that item")
            old = dict(old)
            if old.get("type") in s.model["types"]:
                old["state"] = s.removed_state(old["type"])
            old.pop("rollup", None)
            return self._finish(s.apply(dict(op="put", item=old)), [iid])
        if fix == "pick-parent":
            if s.parent_level(item["type"]) is None:  # an epic with a parent: just clear it
                return self._finish(s.apply(dict(op="move", id=iid, parent=None)), [iid])
            if "parent" not in args:
                return dict(ok=True, ui="pick-parent", itemId=iid, candidates=self._index.suggest("item", "", 50, item["type"]))
            return self._finish(s.apply(dict(op="move", id=iid, parent=args["parent"])), [iid])
        if fix == "focus-field":
            return dict(ok=True, ui="focus-field", itemId=iid, field=found["field"])
        raise OpError("this problem has no quick fix")

    # -- external edits ------------------------------------------------
    def poll(self) -> Dict[str, Any]:
        """Called periodically by the frontend: merges an external edit of the file, retries a failed save."""
        s = self._store
        if s is None:
            return dict(ok=False, changed=False)
        merged = s.autosave()
        out: Dict[str, Any] = dict(ok=True, changed=merged is not None, **self._state())
        if merged is not None:
            self._index.rebuild()
            out["snapshot"] = self.snapshot()
        return out

    @_guard
    def resolve_conflict(self, iid: str, field: Optional[str], choice: str) -> Dict[str, Any]:
        applied = self._store.resolve_conflict(iid, field, choice)
        return self._finish(applied, [iid])


def open_store(path: Optional[str], stress: int = 0) -> Api:
    """Build the Api for ``po gui [FILE] [--stress N]``; open errors become a readable message."""
    if path:
        p = Path(path)
        if p.exists():
            try:
                store = Store.open(p)
            except StoreError as e:
                return Api(None, str(e))
            api = Api(store)
            if store.rollups_changed:  # stale rollups on disk: write the corrected store (not an undo step)
                store.autosave()
            return api
        print(f"{p} does not exist; starting from the sample (it is created on the first change)", file=sys.stderr)
        return Api(Store(sample_data(), p))
    if stress:
        return Api(Store(stress_data(sample_data(), stress)))
    return Api(Store(sample_data()))
