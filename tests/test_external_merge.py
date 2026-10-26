import json

from project_orderly.api import open_store

from conftest import errors, item


def edit_on_disk(path, fn):
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data, indent=2))


def test_no_external_change_means_nothing_happens(api):
    assert api.poll()["changed"] is False


def test_external_edit_with_no_local_changes_is_a_plain_reload(api, backlog):
    edit_on_disk(backlog, lambda d: d["items"]["ado-301"].update(title="By agent"))
    r = api.poll()
    assert r["changed"] and item(api, "ado-301")["title"] == "By agent"
    assert r["snapshot"]["status"]["state"] == "saved"
    assert api.poll()["changed"] is False


def test_external_and_local_edits_to_different_items_and_fields_both_survive(api, backlog):
    api._store.autosave()
    # local edit that cannot be saved right now (an error pauses autosave), so it stays unsaved
    api.set_field("ado-303", "priority", "")
    api.set_field("ado-302", "title", "Mine")
    assert api._store.dirty
    edit_on_disk(backlog, lambda d: (d["items"]["ado-301"].update(title="Theirs"), d["items"]["ado-302"].update(assignedTo="grace")))
    r = api.poll()
    assert r["changed"] and r["conflicts"] == []
    assert item(api, "ado-301")["title"] == "Theirs"
    assert item(api, "ado-302")["title"] == "Mine" and item(api, "ado-302")["assignedTo"] == "grace"
    assert item(api, "ado-303").get("priority") is None
    api.set_field("ado-303", "priority", 2)  # fix the error: merged state is written
    on_disk = json.loads(backlog.read_text())["items"]
    assert on_disk["ado-301"]["title"] == "Theirs" and on_disk["ado-302"]["title"] == "Mine"


def test_same_field_on_both_sides_is_a_conflict_and_blocks_writes(api, backlog):
    api.set_field("ado-303", "priority", "")  # keep local edits unsaved
    api.set_field("ado-301", "title", "Mine")
    edit_on_disk(backlog, lambda d: d["items"]["ado-301"].update(title="Theirs"))
    r = api.poll()
    assert r["status"]["state"] == "conflicts" and r["conflicts"] == [dict(itemId="ado-301", field="title", mine="Mine", theirs="Theirs")]
    assert item(api, "ado-301")["title"] == "Mine"
    api.set_field("ado-303", "priority", 2)  # would normally save
    assert json.loads(backlog.read_text())["items"]["ado-301"]["title"] == "Theirs"  # file untouched
    r = api.resolve_conflict("ado-301", "title", "theirs")
    assert r["status"]["state"] == "saved" and item(api, "ado-301")["title"] == "Theirs"
    assert json.loads(backlog.read_text())["items"]["ado-303"]["priority"] == 2


def test_keep_mine_resolution(api, backlog):
    api.set_field("ado-303", "priority", "")
    api.set_field("ado-301", "title", "Mine")
    edit_on_disk(backlog, lambda d: d["items"]["ado-301"].update(title="Theirs"))
    api.poll()
    api.set_field("ado-303", "priority", 2)
    r = api.resolve_conflict("ado-301", "title", "mine")
    assert r["status"]["state"] == "saved"
    assert json.loads(backlog.read_text())["items"]["ado-301"]["title"] == "Mine"


def test_deleted_on_one_side_edited_on_the_other_is_a_conflict(api, backlog):
    api.set_field("ado-303", "priority", "")
    api.set_field("new-refund-flow", "title", "Edited locally")
    edit_on_disk(backlog, lambda d: d["items"].pop("new-refund-flow"))
    r = api.poll()
    assert [(c["itemId"], c["field"]) for c in r["conflicts"]] == [("new-refund-flow", None)]
    api.resolve_conflict("new-refund-flow", None, "theirs")
    assert "new-refund-flow" not in {i["id"] for i in api.snapshot()["items"]}


def test_merge_is_one_undo_step_and_recomputes_rollups(api, backlog):
    api.set_field("ado-303", "priority", "")
    before = api._store.serialize()

    def agent_adds_story(d):
        d["items"]["new-agent-story"] = dict(id="new-agent-story", type="story", title="From agent", state="New",
                                             parent="ado-300", rank=9, storyPoints=4)
        d["items"]["ado-301"]["title"] = "Renamed"

    edit_on_disk(backlog, agent_adds_story)
    api.poll()
    assert item(api, "ado-300")["rollup"]["storyPoints"] == 12
    assert item(api, "ado-100")["rollup"]["storyPoints"] == 12
    api.undo()
    assert api._store.serialize() == before


def test_external_edit_is_merged_before_autosave_overwrites_it(api, backlog):
    edit_on_disk(backlog, lambda d: d["items"]["ado-301"].update(title="Agent was here"))
    r = api.set_field("ado-302", "title", "Local")  # autosave must merge first, not clobber
    assert "snapshot" in r
    disk = json.loads(backlog.read_text())["items"]
    assert disk["ado-301"]["title"] == "Agent was here" and disk["ado-302"]["title"] == "Local"


def test_unreadable_external_file_pauses_autosave_without_clobbering(api, backlog):
    backlog.write_text("{ half written")
    r = api.set_field("ado-302", "title", "Local")
    assert r["status"]["state"] == "external-error" and backlog.read_text() == "{ half written"
    edit_on_disk_valid = json.loads(api._store.serialize())
    backlog.write_text(json.dumps(edit_on_disk_valid))
    assert api.poll()["status"]["state"] == "saved"


def test_agent_deleting_a_synced_item_surfaces_r24(api, backlog):
    api.set_field("ado-301", "title", "x")  # ensures last-valid exists
    edit_on_disk(backlog, lambda d: d["items"].pop("ado-302"))
    r = api.poll()
    assert any(i["rule"] == "R24" for i in r["issues"]) and r["status"]["state"] == "errors"
    api.quick_fix("R24", "ado-302")
    assert item(api, "ado-302")["state"] == "Removed" and not errors(api)
