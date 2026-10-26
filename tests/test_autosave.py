import json
import os

from project_orderly.api import open_store
from project_orderly.store import Store, sample_data

from conftest import item, write_store


def test_valid_edit_autosaves_and_writes_last_valid(api, backlog):
    r = api.set_field("ado-301", "title", "Store card token")
    assert r["ok"] and r["status"]["state"] == "saved" and not r["dirty"]
    assert json.loads(backlog.read_text())["items"]["ado-301"]["title"] == "Store card token"
    snap = backlog.parent / ".backlogdesk" / "last-valid.json"
    assert json.loads(snap.read_text())["items"]["ado-301"]["title"] == "Store card token"


def test_error_pauses_autosave_and_fix_resumes(api, backlog):
    before = backlog.read_bytes()
    r = api.set_field("ado-303", "priority", "")  # priority is required for problems -> R9
    assert r["status"]["state"] == "errors" and r["status"]["errors"] == 1 and r["dirty"]
    assert backlog.read_bytes() == before
    assert item(api, "ado-303").get("priority") is None  # in-memory edit kept
    r = api.set_field("ado-303", "priority", 2)
    assert r["status"]["state"] == "saved"
    assert json.loads(backlog.read_text())["items"]["ado-303"]["priority"] == 2


def test_backlog_json_contains_no_app_state(api, backlog):
    api.set_field("ado-301", "title", "x")
    api.set_setting("theme", "light")
    assert set(json.loads(backlog.read_text())) <= {"schemaVersion", "project", "model", "people", "iterations", "items"}
    assert (backlog.parent / ".backlogdesk" / "settings.json").exists()


def test_stale_rollups_are_corrected_and_written_on_load(tmp_path, sample):
    data = Store(sample).data()
    data["items"]["ado-100"]["rollup"]["storyPoints"] = 999
    path = write_store(tmp_path / "stale.json", data)
    api = open_store(str(path))
    assert json.loads(path.read_text())["items"]["ado-100"]["rollup"]["storyPoints"] == 8
    assert api.snapshot()["status"]["state"] == "saved"
    assert api.undo()["ok"] is False  # correction is not an undo step


def test_crash_between_temp_write_and_rename_keeps_old_file(api, backlog, monkeypatch):
    before = backlog.read_bytes()

    def boom(*a):
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", boom)
    r = api.set_field("ado-301", "title", "never lands")
    assert backlog.read_bytes() == before
    assert r["status"]["state"] == "save-failed"
    monkeypatch.undo()
    assert api.poll()["status"]["state"] == "saved"  # poll retries the save
    assert "never lands" in backlog.read_text()


def test_missing_file_starts_from_sample_and_first_change_creates_it(tmp_path):
    path = tmp_path / "new.json"
    api = open_store(str(path))
    assert not path.exists() and len(api.snapshot()["items"]) == len(sample_data()["items"])
    api.set_field("ado-301", "title", "hello")
    assert path.exists() and Store.open(path).items["ado-301"]["title"] == "hello"


def test_sample_without_file_stays_in_memory():
    api = open_store(None)
    r = api.set_field("ado-301", "title", "hello")
    assert r["ok"] and r["status"]["state"] == "memory"


def test_stress_flag_gives_exact_count_and_no_errors():
    snap = open_store(None, 3000).snapshot()
    assert len(snap["items"]) == 3000 and snap["status"]["errors"] == 0
