import pytest

from conftest import errors, item


def children(api, parent):
    snap = api.snapshot()["items"]
    return [i["id"] for i in sorted((i for i in snap if i.get("parent") == parent), key=lambda i: i["rank"])]


def test_key_generation_and_deduplication(api):
    assert api.suggest_key("Refund to stored card")["key"] == "new-refund-to-stored-card"
    a = api.create("story", "Same title", "ado-300")
    b = api.create("story", "Same title", "ado-300")
    assert (a["created"], b["created"]) == ("new-same-title", "new-same-title-2")
    assert api.create("story", "Other", "ado-300", key="new-custom")["created"] == "new-custom"
    assert api.create("story", "Other", "ado-300", key="new-custom")["ok"] is False
    assert api.create("story", "Other", "ado-300", key="ado-1")["ok"] is False


def test_created_item_has_valid_defaults_is_selected_and_undoable(api):
    r = api.create("problem", "Checkout hangs", "ado-300")
    new = item(api, r["created"])
    assert r["selectId"] == new["id"] and new["state"] == "New" and new["priority"] == 2
    assert new["rank"] > max(item(api, i)["rank"] for i in ("ado-301", "ado-302"))
    assert not errors(api)
    api.undo()
    assert r["created"] not in {i["id"] for i in api.snapshot()["items"]}


def test_create_with_wrong_level_parent_or_no_parent_is_refused(api):
    assert api.create("story", "x", "ado-100")["ok"] is False  # epic is two levels up
    assert api.create("story", "x", "ado-302")["ok"] is False  # story is not a parent
    assert api.create("story", "x", None)["ok"] is False  # no orphans
    assert api.create("businessEpic", "x", "ado-100")["ok"] is False
    assert api.create("businessEpic", "Top", None)["ok"] is True
    assert api.create("saga", "x", None)["ok"] is False
    assert api.create("story", "  ", "ado-300")["ok"] is False


def test_remove_synced_sets_removed_and_delete_is_refused(api):
    r = api.delete("ado-302")
    assert r["ok"] and r["deletedForReal"] is False
    assert item(api, "ado-302")["state"] == "Removed"
    assert item(api, "ado-100")["rollup"]["storyPoints"] == 5  # removed story no longer counts
    api.undo()
    assert item(api, "ado-302")["state"] == "New" and item(api, "ado-100")["rollup"]["storyPoints"] == 8


def test_delete_never_synced_item_and_undo(api):
    created = api.create("story", "Temp", "ado-300")["created"]
    api.set_field(created, "storyPoints", 5)
    assert item(api, "ado-300")["rollup"]["storyPoints"] == 13
    r = api.delete(created)
    assert r["deletedForReal"] and r["deleted"] == [created]
    assert item(api, "ado-300")["rollup"]["storyPoints"] == 8
    api.undo()
    assert item(api, created)["storyPoints"] == 5 and item(api, "ado-300")["rollup"]["storyPoints"] == 13


def test_delete_item_with_children_is_refused(api):
    epic = api.create("businessEpic", "Top", None)["created"]
    obj = api.create("programObjective", "Obj", epic)["created"]
    assert api.delete(epic)["ok"] is False
    assert api.delete(obj)["ok"] and api.delete(epic)["ok"]


def test_midpoint_rank_and_single_undo_step(api):
    assert children(api, "ado-300") == ["ado-303", "ado-301", "ado-302", "new-refund-flow"]
    r = api.move("ado-302", "ado-300", 1)  # between 303 (1) and 301 (2)
    assert item(api, "ado-302")["rank"] == 1.5 and [i["id"] for i in r["items"]][0] == "ado-302"
    assert children(api, "ado-300") == ["ado-303", "ado-302", "ado-301", "new-refund-flow"]
    api.undo()
    assert children(api, "ado-300") == ["ado-303", "ado-301", "ado-302", "new-refund-flow"]
    assert item(api, "ado-302")["rank"] == 3


def test_renumber_when_gap_gets_too_small(api):
    for _ in range(40):  # keep halving the gap between the first two siblings
        order = children(api, "ado-300")
        last = order[-1]
        api.move(last, "ado-300", 1)
    ranks = [item(api, i)["rank"] for i in children(api, "ado-300")]
    assert len(set(ranks)) == len(ranks) and all(b - a >= 1e-6 for a, b in zip(ranks, ranks[1:]))
    assert not any(i["rule"] == "R21" for i in api.snapshot()["issues"])


def test_reparent_to_correct_level_and_refuse_wrong_level(api):
    other = api.create("feature", "Other feature", "ado-200")["created"]
    assert api.move("ado-302", other)["ok"]
    assert item(api, "ado-302")["parent"] == other
    assert item(api, other)["rollup"]["storyPoints"] == 3 and item(api, "ado-300")["rollup"]["storyPoints"] == 5
    assert api.move("ado-302", "ado-200")["ok"] is False
    assert api.move("ado-302", "ado-301")["ok"] is False
    assert api.move("ado-300", "ado-300")["ok"] is False
    assert api.move("ado-302", None)["ok"] is False
    assert api.move("ado-100", None, 0)["ok"] is True  # already first: no change, no undo step
    api.undo()
    assert item(api, "ado-302")["parent"] == "ado-300"
