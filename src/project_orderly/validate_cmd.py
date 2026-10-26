"""``po validate FILE [--previous SNAPSHOT] [--json]``: headless validation for agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from . import validator
from .store import STATE_DIR, StoreError, parse_store_text


def main(args: List[str]) -> int:
    p = argparse.ArgumentParser(prog="po validate", description="Validate a Backlog Desk store file.")
    p.add_argument("file")
    p.add_argument("--previous", metavar="SNAPSHOT", help=f"last-valid snapshot (default: {STATE_DIR}/last-valid.json next to FILE)")
    p.add_argument("--json", action="store_true", help="print the issue list as JSON")
    ns = p.parse_args(args)
    path = Path(ns.file)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"po validate: cannot read {path}: {getattr(e, 'strerror', None) or e}", file=sys.stderr)
        return 2
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get("schemaVersion"), str):
            raise StoreError("")  # reuse the readable messages below
        v = data["schemaVersion"]
        if v.split(".")[0] != "2":
            raise StoreError(f"unsupported schemaVersion {v!r}")
    except (ValueError, StoreError) as e:
        try:
            parse_store_text(text, str(path))  # produces the readable message
        except StoreError as e2:
            print(f"po validate: {e2}", file=sys.stderr)
        else:  # pragma: no cover
            print(f"po validate: {e}", file=sys.stderr)
        return 2
    prev_path = Path(ns.previous) if ns.previous else path.parent / STATE_DIR / "last-valid.json"
    previous = None
    try:
        previous = json.loads(prev_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        if ns.previous:
            print(f"po validate: cannot read snapshot {prev_path}", file=sys.stderr)
            return 2
    issues = validator.validate(data, previous if isinstance(previous, dict) else None)
    if ns.json:
        print(json.dumps(issues, indent=2))
    else:
        for i in issues:
            where = " ".join(x for x in (i["itemId"], i["field"]) if x)
            print(f"{i['level']} {i['rule']:<6} {where}: {i['message']}")
        c = validator.counts(issues)
        print(f"{c['errors']} error(s), {c['warnings']} warning(s)")
    return 1 if validator.counts(issues)["errors"] else 0
