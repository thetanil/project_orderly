# project_orderly

Pure-Python library and `po` CLI, publishable to PyPI.

```
uvx --from project-orderly po test
uvx --from project-orderly po run
```

Use from a PEP 723 script (see `examples/hello.py`):

```
uv run examples/hello.py
```

Build/publish: `uv build && uv publish`.
Develop: `pip install -e . pytest && pytest`.
