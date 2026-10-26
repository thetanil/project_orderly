import pytest

from project_orderly.store import Store

from conftest import errors, item


def test_edit_returns_item_and_ancestors_with_new_rollups(api):
    r = api.set_field("ado-301", "storyPoints", "8")
    assert [i["id"] for i in r["items"]] == ["ado-301", "ado-300", "ado-200", "ado-100"]
    assert next(i for i in r["items"] if i["id"] == "ado-100")["rollup"]["storyPoints"] == 11
    assert "issues" in r and "dirty" in r and r["status"]["state"] == "saved"


@pytest.mark.parametrize("field,value", [
    ("title", "New title"), ("state", "Resolved"), ("priority", 3), ("storyPoints", 13), ("iteration", "pi26-4-s2"),
    ("assignedTo", "grace"), ("tags", ["a", "b"]), ("description", "text"), ("acceptanceCriteria", "- x"),
])
def test_undo_redo_round_trip_is_byte_identical(api, field, value):
    store = api._store
    base = store.serialize()
    assert api.set_field("ado-301", field, value)["ok"]
    changed = store.serialize()
    assert changed != base
    assert api.undo()["ok"] and store.serialize() == base
    assert api.redo()["ok"] and store.serialize() == changed


def test_undo_everything_in_sequence_restores_the_original(api):
    store = api._store
    base = store.serialize()
    api.set_field("ado-301", "storyPoints", 13)
    created = api.create("story", "Brand new", "ado-300")["created"]
    api.move(created, "ado-300", 0)
    api.remove("ado-302")
    api.delete(created)
    while api.undo()["ok"]:
        pass
    assert store.serialize() == base
    while api.redo()["ok"]:
        pass
    assert "new-brand-new" not in store.items


def test_remotes_rollup_and_identity_cannot_be_set(api):
    for f in ("remotes", "rollup", "id", "type", "parent", "rank"):
        r = api.set_field("ado-301", f, {"x": 1})
        assert r["ok"] is False and "not editable" in r["error"]


def test_invalid_values_are_refused_without_changing_anything(api):
    store = api._store
    base = store.serialize()
    for f, v in [("state", "Done"), ("priority", 9), ("storyPoints", -1), ("iteration", "nope"), ("title", "  ")]:
        assert api.set_field("ado-301", f, v)["ok"] is False
    assert api.set_field("ado-303", "storyPoints", 3)["ok"] is False  # forbidden on problems
    assert store.serialize() == base and not api.undo()["ok"]


def test_error_edit_can_be_undone_back_to_a_valid_saved_state(api, backlog):
    api.set_field("ado-303", "priority", "")
    r = api.undo()
    assert r["status"]["state"] == "saved" and not errors(api)


def test_no_op_edit_is_not_an_undo_step(api):
    api.set_field("ado-301", "title", "Store tokenized card")
    assert api.undo()["ok"] is False


def test_json_patch_round_trip(api):
    store = api._store
    api.set_field("ado-301", "title", "patched")
    patch = Store.to_patch(store._undo[-1])
    assert patch[0]["op"] == "replace" and patch[0]["path"] == "/items/ado-301/title"
    api.undo()
    store.apply(Store.ops_from_patch(patch))
    assert item(api, "ado-301")["title"] == "patched"


def test_set_on_missing_item_fails_cleanly(api):
    assert api.set_field("nope", "title", "x")["ok"] is False
