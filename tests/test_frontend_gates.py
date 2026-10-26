"""Issue 01: a TypeScript error fails the type-check, and CI runs that check before the wheel is built.

Needs Node and `frontend/node_modules` (npm ci); locally the test skips without them, in CI it fails.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()


def _need_node():
    if shutil.which("npm") and (FRONTEND / "node_modules").exists():
        return
    msg = "Node/npm or frontend/node_modules missing (cd frontend && npm ci)"
    pytest.fail(msg) if os.environ.get("CI") else pytest.skip(msg)


def _check(tree: Path):
    return subprocess.run(["npm", "run", "check"], cwd=tree / "frontend", capture_output=True, text=True)


@pytest.fixture
def copy(tmp_path):
    """A throw-away copy of the frontend sources (node_modules linked, not copied)."""
    _need_node()
    dst = tmp_path / "frontend"
    shutil.copytree(FRONTEND, dst, ignore=shutil.ignore_patterns("node_modules", "dist"))
    (dst / "node_modules").symlink_to(FRONTEND / "node_modules")
    return tmp_path


def test_clean_frontend_passes_the_type_check(copy):
    r = _check(copy)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_deliberate_typescript_error_fails_the_type_check(copy):
    (copy / "frontend" / "src" / "broken.ts").write_text("export const n: number = 'not a number';\n")
    r = _check(copy)
    assert r.returncode != 0
    assert "broken.ts" in r.stdout + r.stderr


def test_a_deliberate_error_inside_a_svelte_component_fails_it_too(copy):
    comp = copy / "frontend" / "src" / "Palette.svelte"
    comp.write_text(comp.read_text().replace("let q = $state(\"\");", "let q: number = $state(\"\");", 1))
    assert _check(copy).returncode != 0


def _job(name):
    m = re.search(rf"^  {name}:\n(.*?)(?=^  \w[\w-]*:\n|\Z)", CI, re.M | re.S)
    assert m, f"job {name} not found in ci.yml"
    return m.group(1)


def test_ci_runs_the_check_and_build_before_building_the_wheel():
    assert "npm run check" in _job("frontend")
    for job in ("build", "snapshot"):
        body = _job(job)
        assert re.search(r"needs: \[.*frontend.*\]", body), f"{job} must wait for the frontend job"
        assert body.index("npm run check") < body.index("npm run build") < body.index("uv build"), job


def test_ci_runs_the_python_and_browser_tests():
    assert "pytest" in _job("test")
    assert "tests/ui" in _job("ui") or "playwright" in _job("ui")
