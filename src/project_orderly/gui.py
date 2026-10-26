"""pywebview desktop shell for Backlog Desk."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from .api import open_store

UI_DIR = Path(__file__).parent / "ui"
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def build_frontend() -> bool:
    """In a repo checkout, (re)build the frontend if its sources are newer than the build."""
    if not (FRONTEND_DIR / "package.json").exists():
        return (UI_DIR / "index.html").exists()
    built = UI_DIR / "index.html"
    srcs = [p for p in FRONTEND_DIR.rglob("*") if p.is_file() and "node_modules" not in p.parts]
    if built.exists() and all(p.stat().st_mtime <= built.stat().st_mtime for p in srcs):
        return True
    npm = shutil.which("npm")
    if npm is None:
        print("Node/npm is needed to build the frontend in a repo checkout (dev only).", file=sys.stderr)
        return built.exists()
    if not (FRONTEND_DIR / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)
    return built.exists()


def main(args: List[str]) -> int:
    p = argparse.ArgumentParser(prog="po gui", description="Open the Backlog Desk window")
    p.add_argument("file", nargs="?", help="backlog JSON file (default: built-in sample)")
    p.add_argument("--stress", type=int, default=0, metavar="N", help="generate exactly N items to test performance")
    p.add_argument("--debug", action="store_true", help="open web inspector")
    ns = p.parse_args(args)
    try:
        import webview
    except ImportError:
        print('pywebview is not installed. Install the GUI extra: pip install "project-orderly[gui]"', file=sys.stderr)
        return 1
    if not build_frontend():
        print("The frontend is not built. Run `npm install && npm run build` in frontend/.", file=sys.stderr)
        return 1
    api = open_store(ns.file, ns.stress)
    webview.create_window("Backlog Desk", str(UI_DIR / "index.html"), js_api=api, width=1280, height=800)
    webview.start(debug=ns.debug)
    return 0
