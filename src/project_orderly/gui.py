"""pywebview desktop shell for Backlog Desk (visual prototype)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .store import Store, stress_data

UI_DIR = Path(__file__).parent / "ui"


class Api:
    """Methods exposed to the frontend as `window.pywebview.api.*`."""

    def __init__(self, store: Store, path: Optional[Path]):
        self.store = store
        self.path = path

    def _view(self, ids: List[str]) -> List[Dict[str, Any]]:
        return [self.store.items[i] for i in ids]

    def snapshot(self) -> Dict[str, Any]:
        s = self.store
        return dict(
            model=s.model,
            iterations=s.iterations,
            items=list(s.items.values()),
            issues=s.issues(),
            dirty=s.dirty,
            path=str(self.path) if self.path else None,
        )

    def update(self, iid: str, field: str, value: Any) -> Dict[str, Any]:
        changed = self.store.update(iid, field, value)
        return dict(items=self._view(changed), issues=self.store.issues(), dirty=self.store.dirty)

    def save(self) -> Dict[str, Any]:
        if self.path is None:
            return dict(ok=False, error="sample/stress data has no file; open a file with `po gui FILE`")
        if any(i["level"] == "E" for i in self.store.issues()):
            return dict(ok=False, error="blocked: store has errors")
        self.store.save(self.path)
        return dict(ok=True)


def load_store(path: Optional[str], stress: int) -> "tuple[Store, Optional[Path]]":
    sample = json.loads((UI_DIR / "sample_backlog.json").read_text(encoding="utf-8"))
    if path:
        p = Path(path)
        if p.exists():
            return Store.open(p), p
        print(f"{p} does not exist; starting from the sample (Save will create it)", file=sys.stderr)
        return Store(sample), p
    if stress:
        return Store(stress_data(sample, stress)), None
    return Store(sample), None


def main(args: List[str]) -> int:
    p = argparse.ArgumentParser(prog="po gui", description="Open the Backlog Desk window")
    p.add_argument("file", nargs="?", help="backlog JSON file (default: built-in sample)")
    p.add_argument("--stress", type=int, default=0, metavar="N", help="generate ~N items to test performance")
    p.add_argument("--debug", action="store_true", help="open web inspector")
    ns = p.parse_args(args)
    try:
        import webview
    except ImportError:
        print('pywebview is not installed. Install the GUI extra: pip install "project-orderly[gui]"', file=sys.stderr)
        return 1
    store, path = load_store(ns.file, ns.stress)
    api = Api(store, path)
    webview.create_window("Backlog Desk", str(UI_DIR / "index.html"), js_api=api, width=1280, height=800)
    webview.start(debug=ns.debug)
    return 0
