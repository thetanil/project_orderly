"""Command registry and default placeholder implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

Handler = Callable[[List[str]], int]


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    handler: Handler


_REGISTRY: Dict[str, Command] = {}


def register(name: str, help: str = "") -> Callable[[Handler], Handler]:
    """Decorator registering a handler; replaces any existing command of that name."""

    def deco(fn: Handler) -> Handler:
        _REGISTRY[name] = Command(name, help, fn)
        return fn

    return deco


def get_command(name: str) -> Optional[Command]:
    return _REGISTRY.get(name)


def commands() -> Dict[str, Command]:
    return dict(_REGISTRY)


def run_command(name: str, args: Optional[List[str]] = None) -> int:
    cmd = _REGISTRY.get(name)
    if cmd is None:
        raise KeyError(f"unknown command: {name}")
    return cmd.handler(list(args or []))


@register("test", help="Run project tests (placeholder).")
def test(args: List[str]) -> int:
    print("po test: no tests configured (placeholder)")
    return 0


@register("run", help="Run the project (placeholder).")
def run(args: List[str]) -> int:
    print("po run: nothing to run (placeholder)")
    return 0


@register("gui", help="Open the Backlog Desk desktop window (needs the `gui` extra).")
def gui(args: List[str]) -> int:
    from .gui import main

    return main(args)


@register("validate", help="Validate a backlog store file (for agents): po validate FILE [--previous SNAPSHOT] [--json].")
def validate(args: List[str]) -> int:
    from .validate_cmd import main

    return main(args)
