"""Issue 01: the Api the prototype screen used (snapshot, update) keeps working; later issues only added methods."""
from conftest import item


def test_prototype_calls_still_work(api):
    snap = api.snapshot()
    assert {"items", "model", "issues"} <= set(snap)
    r = api.update("ado-302", "title", "Renamed through the prototype name")
    assert r["ok"] is not False
    assert item(api, "ado-302")["title"] == "Renamed through the prototype name"


def test_every_public_api_method_returns_a_json_serialisable_dict(api):
    import json

    for r in (api.snapshot(), api.get_settings(), api.poll(), api.undo(), api.redo(), api.suggest_key("A title")):
        json.dumps(r)
        assert isinstance(r, dict)
    json.dumps(api.suggest("item", "ado"))
