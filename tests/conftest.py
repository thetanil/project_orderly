import copy
import json
from pathlib import Path

import pytest

from project_orderly.api import open_store
from project_orderly.store import Store, sample_data


def write_store(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def sample():
    return copy.deepcopy(sample_data())


@pytest.fixture
def backlog(tmp_path, sample):
    """A valid store file (rollups already correct) in a temp dir."""
    return write_store(tmp_path / "backlog.json", Store(sample).data())


@pytest.fixture
def api(backlog):
    return open_store(str(backlog))


@pytest.fixture
def make_api(tmp_path, sample):
    """open an Api on the sample after applying a data mutation: make_api(lambda d: ...)."""

    def make(mutate=None, name="backlog.json"):
        data = Store(sample).data()
        if mutate:
            mutate(data)
        return open_store(str(write_store(tmp_path / name, data)))

    return make


def rules(api):
    return {(i["rule"], i["itemId"]) for i in api.snapshot()["issues"]}


def errors(api):
    return [i for i in api.snapshot()["issues"] if i["level"] == "E"]


def item(api, iid):
    return next(i for i in api.snapshot()["items"] if i["id"] == iid)
