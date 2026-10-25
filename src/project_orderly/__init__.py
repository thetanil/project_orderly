"""Project Orderly: a pure-Python library and CLI (`po`)."""

from .core import Command, register, get_command, commands, run_command, test, run

__version__ = "0.1.0"

__all__ = [
    "Command",
    "register",
    "get_command",
    "commands",
    "run_command",
    "test",
    "run",
    "__version__",
]
