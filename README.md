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
original spec). Try it from source:

```
uv run --extra gui po gui                 # built-in sample
uv run --extra gui po gui --stress 5000   # ~5000 generated items, to judge performance
uv run --extra gui po gui my.json --debug # your file, with web inspector
```

On Linux, pywebview also needs a GTK or Qt backend (e.g. `--extra gui --with "pywebview[qt]"`).

### Run the latest main on your desktop

Each push to `main` (incl. merged PRs) replaces the `latest` prerelease with a fresh wheel:

```
gh release download latest -R thetanil/project_orderly -p '*.whl' -D "$TMPDIR/po" --clobber
uvx --from "$(ls $TMPDIR/po/*.whl)[gui]" po gui --stress 3000
```
