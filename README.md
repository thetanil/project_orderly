# project_orderly

Pure-Python library and `po` CLI, publishable to PyPI.

```
uvx --from "project-orderly @ https://github.com/thetanil/project_orderly/releases/download/v0.1.0/project_orderly-0.1.0-py3-none-any.whl" po test
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

## Backlog Desk (desktop GUI prototype)

pywebview shell + plain HTML/JS frontend over a Python store (see `docs/deprecated/` for the
original spec). Run the local dev version from the repo root (edits to `src/` and `ui/` apply on relaunch):

```
uv run --extra gui po gui                 # built-in sample
uv run --extra gui po gui --stress 5000   # ~5000 generated items, to judge performance
uv run --extra gui po gui my.json --debug # your file (created from the sample on Save if missing), with web inspector
```

On Linux the `gui` extra installs the Qt backend from pip (no system packages needed).

Run the tests:

```
uv run --with pytest pytest -q
```

### Run the latest main on your desktop

Each push to `main` (incl. merged PRs) replaces the `latest` prerelease with a fresh wheel:

```
d=$(mktemp -d) && gh release download latest -R thetanil/project_orderly -p '*.whl' -D "$d" \
  && uvx --from "project-orderly[gui] @ file://$(ls -t "$d"/*.whl | head -1)" po gui --stress 3000
```
