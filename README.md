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
