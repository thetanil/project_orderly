import json
import time

from project_orderly.api import open_store

from conftest import errors, item


def test_bulk_edit_is_one_undo_step_with_one_response(api):
    store = api._store
    base = store.serialize()
    r = api.bulk_set(["ado-301", "ado-302", "ado-303"], "iteration", "pi26-4-s2")
    assert r["ok"] and {i["id"] for i in r["items"]} >= {"ado-301", "ado-302", "ado-303", "ado-300", "ado-100"}
    assert all(item(api, i)["iteration"] == "pi26-4-s2" for i in ("ado-301", "ado-302", "ado-303"))
    api.undo()
    assert store.serialize() == base and not api.undo()["ok"]


def test_bulk_skips_and_reports_items_that_cannot_take_the_value(api):
    r = api.bulk_set(["ado-301", "ado-303", "ado-300", "ghost"], "state", "Resolved")
    # problems have no Resolved state, features do
    skipped = {s["id"] for s in r["skipped"]}
    assert skipped == {"ado-303", "ghost"}
    assert item(api, "ado-301")["state"] == "Resolved" and item(api, "ado-303")["state"] == "Active"
    assert not errors(api)


def test_bulk_tags_modes_and_priority_and_assignee(api):
    api.bulk_set(["ado-301", "ado-302"], "tags", ["x", "y"])
    api.bulk_set(["ado-301"], "tags", ["y"], mode="remove")
    assert item(api, "ado-301")["tags"] == ["payments", "tokens", "x"] and item(api, "ado-302")["tags"] == ["x", "y"]
    api.bulk_set(["ado-301", "ado-302"], "priority", 1)
    api.bulk_set(["ado-301", "ado-302"], "assignedTo", "grace")
    assert item(api, "ado-302")["priority"] == 1 and item(api, "ado-302")["assignedTo"] == "grace"
    assert api.bulk_set(["ado-301"], "title", "x")["ok"] is False


def test_current_user_persists_and_never_enters_the_store(backlog):
    api = open_store(str(backlog))
    assert api.get_settings()["currentUser"] is None
    assert api.set_setting("currentUser", "nick")["ok"]
    assert api.set_setting("currentUser", "stranger")["ok"] is False
    api.set_setting("theme", "light")
    api.set_setting("density", "comfortable")
    api.set_field("ado-301", "title", "x")
    again = open_store(str(backlog)).get_settings()
    assert again == dict(currentUser="nick", theme="light", density="comfortable")
    assert "currentUser" not in backlog.read_text()
    assert api.set_setting("theme", "pink")["ok"] is False


def test_suggest_each_kind_ranked(api):
    assert api.suggest("item", "ado-30")[0]["id"].startswith("ado-30")
    assert api.suggest("item", "stored")[0]["id"] in {"ado-302", "ado-301", "new-refund-flow"}
    assert [s["id"] for s in api.suggest("item", "", for_type="story")] == ["ado-300"]  # only features, never removed
    assert api.suggest("item", "", for_type="businessEpic") == []
    assert api.suggest("iteration", "sprint 2")[0]["id"] == "pi26-4-s2"
    assert {s["tag"] for s in api.suggest("tag", "pay")} == {"payments"}
    people = [p["id"] for p in api.suggest("person", "")]
    assert set(people) == {"nick", "ada", "grace"}
    api.set_setting("currentUser", "grace")
    assert api.suggest("person", "")[0]["id"] == "grace"
    assert api.suggest("person", "ada")[0]["id"] == "ada"


def test_fuzzy_subsequence_match(api):
    assert api.suggest("item", "tkncrd")[0]["id"] == "ado-301"  # "Store tokenized card"
    assert api.suggest("item", "zzzz") == []


def test_index_follows_mutations(api):
    api.create("story", "Quantum refunds", "ado-300")
    assert api.suggest("item", "quantum")[0]["id"] == "new-quantum-refunds"
    api.set_field("new-quantum-refunds", "tags", ["zeta"])
    assert api.suggest("tag", "zet")[0]["count"] == 1
    api.set_field("new-quantum-refunds", "tags", [])
    assert api.suggest("tag", "zet") == []
    api.undo()
    api.undo()
    api.undo()
    assert api.suggest("item", "quantum") == []


def test_suggest_is_fast_for_3000_items():
    api = open_store(None, 3000)
    api.suggest("item", "story")
    t = time.perf_counter()
    for q in ("story 1.2", "feat", "e3", "zz"):
        api.suggest("item", q)
    assert (time.perf_counter() - t) / 4 < 0.1  # generous bound; target is ~20 ms
