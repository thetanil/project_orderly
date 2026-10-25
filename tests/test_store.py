import json
from pathlib import Path

from project_orderly.store import Store, stress_data

UI = Path(__file__).parent.parent / "src" / "project_orderly" / "ui"
SAMPLE = json.loads((UI / "sample_backlog.json").read_text())


def test_rollup_matches_schema_example():
    s = Store(SAMPLE)
    assert s.items["ado-300"]["rollup"] == dict(storyPoints=8, estimatedCount=2, unestimatedCount=0, notEstimableCount=1)
    assert s.items["ado-100"]["rollup"]["storyPoints"] == 8  # removed story excluded


def test_sample_is_valid():
    assert [i for i in Store(SAMPLE).issues() if i["level"] == "E"] == []


def test_update_recomputes_ancestors_and_validates():
    s = Store(json.loads(json.dumps(SAMPLE)))
    changed = s.update("ado-301", "storyPoints", "8")
    assert changed == ["ado-301", "ado-300", "ado-200", "ado-100"]
    assert s.items["ado-100"]["rollup"]["storyPoints"] == 11
    s.update("ado-303", "priority", "")
    assert any(i["rule"] == "R9" for i in s.issues())


def test_stress_data_loads():
    s = Store(stress_data(SAMPLE, 3000))
    assert len(s.items) >= 3000
