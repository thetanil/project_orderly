import pytest

from project_orderly import run_command
from project_orderly.cli import main


def test_default_commands(capsys):
    assert main(["test"]) == 0
    assert "placeholder" in capsys.readouterr().out
    assert main(["run"]) == 0


def test_no_command_prints_help(capsys):
    assert main([]) == 0
    assert "po" in capsys.readouterr().out


def test_unknown_command():
    with pytest.raises(KeyError):
        run_command("nope")
