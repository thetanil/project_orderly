# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "project-orderly @ https://github.com/thetanil/project_orderly/releases/download/v0.1.0/project_orderly-0.1.0-py3-none-any.whl",
# ]
# ///
"""Run with: uv run examples/hello.py

Consumes the wheel attached to the GitHub release. After PyPI publishing is
enabled, the dependency can simply be "project-orderly".
"""

import project_orderly as po

raise SystemExit(po.run_command("test"))
