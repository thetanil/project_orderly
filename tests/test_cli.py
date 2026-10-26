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


def test_command_options_pass_through(monkeypatch):
    from project_orderly import core

    seen = []
    monkeypatch.setitem(core._REGISTRY, "gui", core.Command("gui", "", lambda a: seen.append(a) or 0))
    assert main(["gui", "--stress", "3000", "--debug"]) == 0
    assert seen == [["--stress", "3000", "--debug"]]
