"""The `po` command line interface."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .core import commands, run_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="po", description="Project Orderly CLI")
    parser.add_argument("--version", action="version", version=f"po {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, cmd in sorted(commands().items()):
        p = sub.add_parser(name, help=cmd.help, description=cmd.help)
        p.add_argument("args", nargs=argparse.REMAINDER, help="arguments passed through")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not ns.command:
        parser.print_help()
        return 0
    return run_command(ns.command, ns.args)


if __name__ == "__main__":
    raise SystemExit(main())
