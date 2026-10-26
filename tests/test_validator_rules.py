"""Each implemented rule: one failing and one passing case, through the Api."""
import pytest

from conftest import errors, rules, item


def test_valid_sample_has_no_issues(make_api):
    assert make_api().snapshot()["issues"] == []


def test_r1_key_equals_id(make_api):
    def bad(d):
        d["items"]["ado-301"]["id"] = "ado-999"
        d["iterations"]["pi26-4-s1"]["id"] = "other"

    r = rules(make_api(bad))
    assert ("R1", "ado-301") in r and ("R1", "pi26-4-s1") in r


def test_r2_unknown_type(make_api):
    assert ("R2", "ado-301") in rules(make_api(lambda d: d["items"]["ado-301"].update(type="saga")))


def test_r3_state_of_type(make_api):
    assert ("R3", "ado-300") in rules(make_api(lambda d: d["items"]["ado-300"].update(state="Nope")))


def test_r4_parent_exists_and_one_level_above(make_api):
    assert ("R4", "ado-301") in rules(make_api(lambda d: d["items"]["ado-301"].update(parent="ado-100")))
    assert ("R4", "ado-301") in rules(make_api(lambda d: d["items"]["ado-301"].update(parent="gone")))
    assert ("R4", "ado-100") in rules(make_api(lambda d: d["items"]["ado-100"].update(parent="ado-100")))


def test_r5_orphan_is_a_warning(make_api):
    api = make_api(lambda d: d["items"]["ado-301"].update(parent=None))
    issue = next(i for i in api.snapshot()["issues"] if i["rule"] == "R5")
    assert issue["level"] == "W" and issue["itemId"] == "ado-301"


def test_r6_iteration_exists(make_api):
    assert ("R6", "ado-301") in rules(make_api(lambda d: d["items"]["ado-301"].update(iteration="nope")))


def test_r7_forbidden_estimate(make_api):
    api = make_api(lambda d: d["items"]["ado-303"].update(storyPoints=3))
    assert ("R7", "ado-303") in rules(api)


def test_r8_missing_estimate_warns_unless_removed(make_api):
    def bad(d):
        d["items"]["ado-301"].pop("storyPoints")
        d["items"]["new-refund-flow"].pop("storyPoints")

    r = rules(make_api(bad))
    assert ("R8", "ado-301") in r and ("R8", "new-refund-flow") not in r


def test_r9_required_priority(make_api):
    api = make_api(lambda d: d["items"]["ado-303"].pop("priority"))
    assert ("R9", "ado-303") in rules(api) and errors(api)


def test_r10_rollup_must_match(make_api):
    api = make_api(lambda d: d["items"]["ado-300"]["rollup"].update(storyPoints=99))
    # the GUI recomputes on load, so the stale value never surfaces there ...
    assert ("R10", "ado-300") not in rules(api)
    # ... but the headless validator catches hand edits (see test_cli_validate)


def test_r11_unique_ado_id(make_api):
    api = make_api(lambda d: d["items"]["ado-302"]["remotes"]["ado"].update(id=301))
    assert ("R11", "ado-302") in rules(api)


def test_r12_iterations(make_api):
    def bad(d):
        d["iterations"]["pi26-4-s1"]["finishDate"] = "2026-01-01"
        d["iterations"]["pi26-4-s2"]["path"] = d["iterations"]["pi26-4-s1"]["path"]

    r = rules(make_api(bad))
    assert ("R12", "pi26-4-s1") in r and ("R12", "pi26-4-s2") in r


def test_r13_custom_fields_must_be_declared(make_api):
    api = make_api(lambda d: d["items"]["ado-301"].update(custom={"mystery": 1}))
    assert ("R13", "ado-301") in rules(api)
    api = make_api(lambda d: (d["model"].update(customFields={"team": {"label": "Team"}}), d["items"]["ado-301"].update(custom={"team": "x"})))
    assert ("R13", "ado-301") not in rules(api)


def test_r21_duplicate_rank_warns(make_api):
    api = make_api(lambda d: d["items"]["ado-302"].update(rank=2))
    assert ("R21", "ado-302") in rules(api)


@pytest.mark.parametrize("text,flag", [
    ("plain **markdown** with a <https://example.com> autolink", False),
    ("code `<b>` and\n```\n<div>x</div>\n```", False),
    ("a <b>bold</b> claim", True),
    ("line<br/>break", True),
    ("<!-- hidden -->", True),
])
def test_r22_raw_html_in_markdown(make_api, text, flag):
    api = make_api(lambda d: d["items"]["ado-300"].update(description=text))
    assert (("R22", "ado-300") in rules(api)) is flag


def test_r23_sync_conflicts_warn(make_api):
    api = make_api(lambda d: d["items"]["ado-301"]["remotes"]["ado"].update(conflicts=[{"field": "title"}]))
    issue = next(i for i in api.snapshot()["issues"] if i["rule"] == "R23")
    assert issue["level"] == "W"


def test_r24_r25_skip_cleanly_without_snapshot_and_fire_with_one(tmp_path, sample):
    from project_orderly.api import open_store
    from project_orderly.store import Store

    from conftest import write_store

    data = Store(sample).data()
    # no snapshot: nothing to compare against
    path = write_store(tmp_path / "b.json", data)
    assert not {r for r, _ in rules(open_store(str(path)))} & {"R24", "R25"}
    # snapshot = what the app last saved
    (tmp_path / ".backlogdesk").mkdir()
    write_store(tmp_path / ".backlogdesk" / "last-valid.json", data)
    assert not {r for r, _ in rules(open_store(str(path)))} & {"R24", "R25"}
    # an agent deletes a synced item and edits remotes of another
    del data["items"]["ado-302"]
    data["items"]["ado-301"]["remotes"]["ado"]["rev"] = 7
    path = write_store(tmp_path / "b.json", data)
    r = rules(open_store(str(path)))
    assert ("R24", "ado-302") in r and ("R25", "ado-301") in r
