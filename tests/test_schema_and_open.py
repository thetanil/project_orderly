import json

import jsonschema
import pytest

from project_orderly import validator
from project_orderly.api import open_store
from project_orderly.store import Store, StoreError, sample_data, stress_data

from conftest import errors, write_store


def schema_errors(data):
    return list(jsonschema.Draft202012Validator(validator.load_schema()).iter_errors(data))


def test_schema_itself_is_valid():
    jsonschema.Draft202012Validator.check_schema(validator.load_schema())


def test_sample_validates_against_schema():
    assert schema_errors(sample_data()) == []


@pytest.mark.parametrize("n", [1, 5, 123, 3000])
def test_stress_data_validates_and_is_exact(n):
    data = stress_data(sample_data(), n)
    assert len(data["items"]) == n
    assert schema_errors(data) == []
    store = Store(data)
    assert [i for i in store.issues() if i["level"] == "E"] == []


def test_schema_document_example_in_v2_shape_is_valid(sample):
    # the schema document's example: epic > objective > feature with story, problem and a removed story
    d = Store(sample).data()
    assert d["items"]["ado-300"]["rollup"] == dict(storyPoints=8, estimatedCount=2, unestimatedCount=0, notEstimableCount=1)
    assert schema_errors(d) == []
    assert Store(d).issues() == []


def test_missing_or_unknown_schema_version_is_rejected(tmp_path, sample):
    del sample["schemaVersion"]
    api = open_store(str(write_store(tmp_path / "a.json", sample)))
    snap = api.snapshot()
    assert "schemaVersion" in snap["error"] and "items" not in snap
    sample["schemaVersion"] = "9.0.0"
    assert "unsupported schemaVersion" in open_store(str(write_store(tmp_path / "b.json", sample))).snapshot()["error"]


def test_corrupt_and_unreadable_files_give_a_readable_message(tmp_path, sample):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    snap = open_store(str(bad)).snapshot()
    assert "not valid JSON" in snap["error"] and "Traceback" not in snap["error"]
    sample["items"]["ado-301"]["storyPoints"] = -3
    snap = open_store(str(write_store(tmp_path / "neg.json", sample))).snapshot()
    assert "ado-301" in snap["error"] and "storyPoints" in snap["error"]
    api = open_store(str(bad))
    assert api.set_field("x", "title", "y")["ok"] is False
    with pytest.raises(StoreError):
        Store.open(tmp_path / "missing.json")


def test_structural_errors_map_to_item_and_field(sample):
    sample["items"]["ado-301"]["storypoints"] = 3
    sample["items"]["ado-302"].pop("title")
    issues = validator.structure_issues(sample)
    pairs = {(i["itemId"], i["field"]) for i in issues}
    assert ("ado-301", "storypoints") in pairs and ("ado-302", "title") in pairs
    assert all(i["rule"] == "SCHEMA" and i["level"] == "E" for i in issues)
