# project_orderly

Pure-Python library and `po` CLI, publishable to PyPI.

Run it straight from a release wheel (no checkout, no Node; the GUI needs the `gui` extra):

```
W=https://github.com/thetanil/project_orderly/releases/download/v0.1.0/project_orderly-0.1.0-py3-none-any.whl
uvx --from "project-orderly[gui] @ $W" po gui backlog.json      # created on the first change if missing
uvx --from "project-orderly @ $W" po validate backlog.json      # headless, base install
```

Use from a PEP 723 script (see `examples/hello.py`):

```
uv run examples/hello.py
```

Releases: pushing a tag `vX.Y.Z` (matching `pyproject.toml` version) runs
`.github/workflows/ci.yml`, which tests, builds, and attaches the wheel and sdist to a
GitHub release. If the repo variable `PUBLISH_TO_PYPI` is `true` (and PyPI trusted
publishing is configured for the `pypi` environment), it also publishes to PyPI.
Develop: `pip install -e . pytest && pytest`.

## Backlog Desk (desktop GUI)

A pywebview window over one Python backend that owns all state and every write to disk. The frontend
(Svelte + TypeScript + CodeMirror 6, built by Vite in `frontend/`) is only a view. Requirements and
decisions: `.scratch/python-backlog-desk-m1-m2/spec.md` and `docs/adr/`.

**Features:** hierarchy tree (Epic → Objective → Feature → Story/Problem/Bug) with rollups, inspector,
inline editing, create / remove / delete, drag and keyboard rerank and reparent, undo/redo for everything,
filters, bulk edit, Problems screen with quick fixes, `Ctrl+K` palette, autocomplete, and automatic
atomic saving (there is no Save button). The status bar shows `saved`, `N warnings` or
`N errors – not saved`. External edits to the file (for example by an agent) are merged in field by
field; only true conflicts ask you.

### Run the dev version (from the repo root)

Node (20.19+ or 22) is needed **for development only**; the wheel ships the built frontend.

```
uv run --extra gui po gui                 # built-in sample (kept in memory)
uv run --extra gui po gui --stress 3000   # exactly 3000 generated valid items, to judge performance
uv run --extra gui po gui backlog.json --debug # your file (created on the first change if missing), with web inspector
```

The command builds the frontend first when `frontend/` sources are newer than the build. To iterate on
the frontend: `cd frontend && npm install && npm run watch` in another terminal, then relaunch the window.
`npm run check` type-checks (CI runs it, then `npm run build`; either failing fails CI).

On Linux the `gui` extra installs the Qt backend from pip (no system packages needed).

Keys: `N` new, `Enter`/`F2` edit title, `Esc` cancel, arrows, `Alt+↑/↓` rerank, `Tab`/`Shift+Tab` move under
the next/previous parent, `Del` remove (`Shift+Del` delete a never-synced item), `Ctrl+Z` / `Ctrl+Shift+Z`,
`F8` next problem, `Ctrl+K` palette, `/` filter. Theme, density and "who am I" are remembered in
`.backlogdesk/settings.json` next to the file (never in the backlog).

### Run the tests

```
uv run --with pytest --with jsonschema --with-editable . pytest -q          # Api, CLI, rules: no browser needed
(cd frontend && npm ci && npm run build)                                      # once, for the browser tests
uv run --with pytest --with playwright --with-editable . pytest -q tests/ui   # the built UI in headless Chromium
```

Backend tests drive the `Api` object (the one seam the frontend uses) against temp files. `tests/ui` serves the
built frontend with a tiny shim that forwards every `pywebview.api` call to the same `Api`, so the real UI code
runs against the real backend with no window. `tests/test_frontend_gates.py` proves a TypeScript error fails the
type-check and `tests/test_wheel.py` installs the wheel in a Node-free venv. Locally the browser tests skip when
Playwright or the build is missing; in CI (`CI=true`) that is a failure.

### Run the latest main on your desktop

Each push to `main` (incl. merged PRs) replaces the `latest` prerelease with a fresh wheel (dev-stamped version):

```
d=$(mktemp -d) && gh release download latest -R thetanil/project_orderly -p '*.whl' -D "$d" \
  && uvx --from "project-orderly[gui] @ file://$(ls -t "$d"/*.whl | head -1)" po gui backlog.json
```

### Validate after every change (for agents)

The store is also edited by agents. After every change to the file run:

```
po validate backlog.json            # human-readable
po validate backlog.json --json     # [{rule, level, itemId, field, message, fix?}]
```

Exit code `0` = no E-level issues (warnings allowed), `1` = errors, `2` = file cannot be read. It runs the JSON
Schema (`src/project_orderly/backlog.schema.json`) and the same rules the GUI uses, and compares with
`.backlogdesk/last-valid.json` next to the file (or `--previous SNAPSHOT`) so that deleting a synced item (R24)
or editing `remotes` (R25) is caught. Work on `rollup` is pointless: it is recomputed. It needs no GUI extra.
