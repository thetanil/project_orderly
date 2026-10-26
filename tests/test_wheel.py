"""Issue 01: the wheel contains the built frontend and runs without Node (what `uvx` does).

Builds the wheel from the working tree (the frontend must be built), installs it in a clean venv and
runs it with a PATH that has no node/npm.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _need(cond, msg):
    if not cond:
        pytest.fail(msg) if os.environ.get("CI") else pytest.skip(msg)


def test_wheel_runs_without_node_and_serves_the_built_ui(tmp_path):
    uv = shutil.which("uv")
    _need(uv, "uv not installed")
    _need((ROOT / "src" / "project_orderly" / "ui" / "index.html").exists(), "frontend is not built")
    out = tmp_path / "dist"
    subprocess.run([uv, "build", "--wheel", "-o", str(out)], cwd=ROOT, check=True, capture_output=True)
    whl = next(out.glob("*.whl"))
    venv = tmp_path / "venv"
    subprocess.run([uv, "venv", str(venv), "--python", sys.executable], check=True, capture_output=True)
    py = venv / "bin" / "python"
    subprocess.run([uv, "pip", "install", "--python", str(py), str(whl)], check=True, capture_output=True)

    # a PATH with only the venv on it: no node/npm anywhere
    env = {"PATH": str(venv / "bin"), "HOME": str(tmp_path)}
    assert shutil.which("node", path=env["PATH"]) is None, "node must not be reachable for this test"
    code = (
        "from project_orderly import gui\n"
        "assert gui.build_frontend(), 'no built frontend inside the wheel'\n"
        "p = gui.UI_DIR / 'index.html'\n"
        "assert 'site-packages' in str(p), p\n"
        "assert p.stat().st_size > 100_000\n"
    )
    r = subprocess.run([str(py), "-c", code], env=env, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr

    store = tmp_path / "b.json"
    r = subprocess.run([str(venv / "bin" / "po"), "validate", str(store)], env=env, capture_output=True, text=True)
    assert r.returncode == 2  # unreadable file: the command runs from the installed wheel, base install, no gui extra
