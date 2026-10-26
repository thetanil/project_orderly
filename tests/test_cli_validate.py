import json

from project_orderly.cli import main
from project_orderly.store import Store

from conftest import write_store


def run(capsys, *args):
    code = main(["validate", *map(str, args)])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_clean_store_exits_zero(backlog, capsys):
    code, out, _ = run(capsys, backlog)
    assert code == 0 and "0 error(s)" in out


def test_error_exits_one_and_is_listed(tmp_path, sample, capsys):
    data = Store(sample).data()
    data["items"]["ado-301"]["iteration"] = "nope"
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data))
    assert code == 1 and "R6" in out and "ado-301" in out


def test_hand_edited_rollup_reports_r10(tmp_path, sample, capsys):
    data = Store(sample).data()
    data["items"]["ado-300"]["rollup"]["storyPoints"] = 99
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data), "--json")
    issues = json.loads(out)
    assert code == 1 and any(i["rule"] == "R10" and i["itemId"] == "ado-300" for i in issues)


def test_previous_snapshot_reports_deleted_synced_item(tmp_path, sample, capsys):
    data = Store(sample).data()
    snap = write_store(tmp_path / "snap.json", data)
    del data["items"]["ado-302"]
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data), "--previous", snap, "--json")
    assert code == 1 and any(i["rule"] == "R24" for i in json.loads(out))


def test_default_snapshot_next_to_file(tmp_path, sample, capsys):
    data = Store(sample).data()
    (tmp_path / ".backlogdesk").mkdir()
    write_store(tmp_path / ".backlogdesk" / "last-valid.json", data)
    data["items"]["ado-301"]["remotes"]["ado"]["rev"] = 5
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data))
    assert code == 1 and "R25" in out


def test_json_output_shape(tmp_path, sample, capsys):
    data = Store(sample).data()
    data["items"]["ado-302"]["rank"] = 2
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data), "--json")
    issue = json.loads(out)[0]
    assert code == 0 and set(issue) >= {"rule", "level", "itemId", "field", "message"}


def test_unreadable_file_exits_two(tmp_path, capsys):
    assert run(capsys, tmp_path / "missing.json")[0] == 2
    bad = tmp_path / "bad.json"
    bad.write_text("nope")
    code, _, err = run(capsys, bad)
    assert code == 2 and "not valid JSON" in err
    no_version = write_store(tmp_path / "nv.json", {"model": {"types": {}}, "items": {}})
    assert run(capsys, no_version)[0] == 2


def test_structural_errors_exit_one(tmp_path, sample, capsys):
    data = Store(sample).data()
    data["items"]["ado-301"]["storypoints"] = 3
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data))
    assert code == 1 and "SCHEMA" in out


def test_structurally_broken_model_reports_schema_issues_not_a_traceback(tmp_path, sample, capsys):
    data = Store(sample).data()
    del data["model"]["types"]["story"]["estimation"]
    data["items"]["ado-300"]["parent"] = ["x"]
    code, out, _ = run(capsys, write_store(tmp_path / "b.json", data))
    assert code == 1 and "SCHEMA" in out
