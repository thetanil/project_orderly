import json

from project_orderly.api import open_store

from conftest import errors, item, rules, write_store


def fixed(api, rule, iid, **kw):
    r = api.quick_fix(rule, iid, **kw)
    assert r["ok"], r
    return r


def gone(api, rule, iid):
    return (rule, iid) not in rules(api) and not errors(api)


def test_only_listed_rules_carry_a_fix(make_api):
    api = make_api(lambda d: d["items"]["ado-301"].update(parent="ado-100", iteration="nope"))
    by_rule = {i["rule"]: i for i in api.snapshot()["issues"]}
    assert by_rule["R4"]["fix"] == "pick-parent" and "fix" not in by_rule["R6"]


def test_r4_wrong_level_parent_via_picker(make_api):
    api = make_api(lambda d: d["items"]["ado-301"].update(parent="ado-100"))
    r = fixed(api, "R4", "ado-301")
    assert r["ui"] == "pick-parent" and {c["id"] for c in r["candidates"]} == {"ado-300"}
    fixed(api, "R4", "ado-301", args={"parent": "ado-300"})
    assert gone(api, "R4", "ado-301")


def test_r5_orphan_pick_parent(make_api):
    api = make_api(lambda d: d["items"]["ado-301"].update(parent=None))
    fixed(api, "R5", "ado-301", args={"parent": "ado-300"})
    assert gone(api, "R5", "ado-301")


def test_r4_epic_with_a_parent_clears_it(make_api):
    api = make_api(lambda d: d["items"]["ado-100"].update(parent="ado-200"))
    fixed(api, "R4", "ado-100")
    assert gone(api, "R4", "ado-100")


def test_r7_clear_points(make_api):
    api = make_api(lambda d: d["items"]["ado-303"].update(storyPoints=5))
    fixed(api, "R7", "ado-303")
    assert gone(api, "R7", "ado-303") and "storyPoints" not in item(api, "ado-303")


def test_r8_r9_focus_the_field(make_api):
    api = make_api(lambda d: (d["items"]["ado-301"].pop("storyPoints"), d["items"]["ado-303"].pop("priority")))
    assert fixed(api, "R8", "ado-301")["field"] == "storyPoints"
    assert fixed(api, "R9", "ado-303")["field"] == "priority"


def test_r21_renumber(make_api):
    api = make_api(lambda d: d["items"]["ado-302"].update(rank=2))
    fixed(api, "R21", "ado-302")
    assert gone(api, "R21", "ado-302")


def test_r22_html_to_markdown(make_api):
    html = "<p>Pay with <b>one</b> click</p><ul><li>fast</li><li>safe</li></ul><a href='https://x.io'>docs</a>"
    api = make_api(lambda d: d["items"]["ado-300"].update(description=html))
    fixed(api, "R22", "ado-300")
    assert gone(api, "R22", "ado-300")
    text = item(api, "ado-300")["description"]
    assert "**one**" in text and "- fast" in text and "[docs](https://x.io)" in text


def test_r24_restore_deleted_synced_item_as_removed(tmp_path, sample):
    from project_orderly.store import Store

    data = Store(sample).data()
    (tmp_path / ".backlogdesk").mkdir()
    write_store(tmp_path / ".backlogdesk" / "last-valid.json", data)
    del data["items"]["ado-302"]
    api = open_store(str(write_store(tmp_path / "b.json", data)))
    assert ("R24", "ado-302") in rules(api)
    fixed(api, "R24", "ado-302")
    assert gone(api, "R24", "ado-302") and item(api, "ado-302")["state"] == "Removed"
    assert api.snapshot()["status"]["state"] == "saved"


def test_each_fix_is_one_undo_step_and_stale_fix_is_refused(make_api):
    api = make_api(lambda d: d["items"]["ado-303"].update(storyPoints=5))
    fixed(api, "R7", "ado-303")
    api.undo()
    assert ("R7", "ado-303") in rules(api)
    fixed(api, "R7", "ado-303")
    assert api.quick_fix("R7", "ado-303")["ok"] is False
