# /// script
# requires-python = ">=3.9"
# dependencies = ["project-orderly"]
# ///
"""Run with: uv run examples/hello.py"""

import project_orderly as po

raise SystemExit(po.run_command("test"))
