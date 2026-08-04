import json
from unittest.mock import MagicMock

import pytest

from graphqler import config
from graphqler.fuzzer.engine.types import Result, ResultEnum
from graphqler.graph.node import Node
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats


def _successful_result() -> Result:
    return Result(
        ResultEnum.HAS_DATA_SUCCESS,
        payload="query { viewer { id } }",
        status_code=200,
        graphql_response={"data": {"viewer": {"id": "1"}}},
        raw_response_text='{"data":{"viewer":{"id":"1"}}}',
    )


def test_stats_mutation_stays_in_memory_until_checkpoint(tmp_path):
    stats = Stats()
    stats.set_file_paths(str(tmp_path))
    node = Node(graphql_type="Query", name="viewer", body={})

    stats.add_http_status_code(node.name, 200)
    stats.update_stats_from_result(node, _successful_result())

    assert not stats.state_save_path.exists()
    assert stats.number_of_successes == 1


def test_stats_save_is_idempotent_and_round_trips(tmp_path):
    stats = Stats()
    stats.set_file_paths(str(tmp_path))
    node = Node(graphql_type="Query", name="viewer", body={})
    result = _successful_result()
    stats.add_http_status_code(node.name, 200)
    stats.update_stats_from_result(node, result)
    stats.dep_retry_nodes = ["Query|viewer"]

    stats.save()
    endpoint_file = tmp_path / "endpoint_results" / "viewer" / "success" / "200"
    first_output = endpoint_file.read_text()
    stats.save()

    restored = Stats()
    restored.state_save_path = tmp_path / config.SERIALIZED_DIR_NAME / config.STATS_STATE_FILE_NAME
    restored.load()

    assert endpoint_file.read_text() == first_output
    assert first_output.count("Payload:") == 1
    assert restored.results == {"viewer": {result}}
    assert restored.number_of_successes == 1
    assert restored.http_status_codes == {"200": {"viewer": 1}}
    assert restored.dep_retry_nodes == ["Query|viewer"]


def test_stats_rejects_unknown_state_version(tmp_path):
    state_path = tmp_path / "stats.json"
    state_path.write_text(json.dumps({"format": "graphqler.stats", "version": 999}))
    stats = Stats()
    stats.state_save_path = state_path

    with pytest.raises(ValueError, match="Unsupported stats state format"):
        stats.load()


def test_objects_bucket_round_trips_json_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIRECTORY", str(tmp_path))
    api = MagicMock()
    bucket = ObjectsBucket(api)
    bucket.objects = {"User": [{"id": "1", "name": "Ada"}]}
    bucket.scalars = {"id": {"type": "ID", "values": {"1", "2"}}}

    bucket.save()
    restored = ObjectsBucket(api).load()

    assert restored.objects == bucket.objects
    assert restored.scalars == bucket.scalars
    state = json.loads((tmp_path / "serialized" / "objects_bucket.json").read_text())
    assert state["format"] == "graphqler.objects_bucket"
    assert state["version"] == 1


def test_objects_bucket_merge_deduplicates_and_copies_values(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIRECTORY", str(tmp_path))
    api = MagicMock()
    target = ObjectsBucket(api)
    target.objects = {"User": [{"id": "1"}]}
    target.scalars = {"id": {"type": "ID", "values": {"1"}}}
    source = ObjectsBucket(api)
    source.objects = {"User": [{"id": "1"}, {"id": "2"}]}
    source.scalars = {"id": {"type": "ID", "values": {"1", "2"}}}

    target.merge(source)
    source.objects["User"][0]["id"] = "changed"
    source.scalars["id"]["values"].add("changed")

    assert target.objects == {"User": [{"id": "1"}, {"id": "2"}]}
    assert target.scalars == {"id": {"type": "ID", "values": {"1", "2"}}}


def test_objects_bucket_rejects_executable_or_invalid_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIRECTORY", str(tmp_path))
    state_path = tmp_path / "serialized" / "objects_bucket.json"
    state_path.parent.mkdir()
    state_path.write_text("not json")

    with pytest.raises(ValueError, match="Unable to read objects bucket state"):
        ObjectsBucket(MagicMock()).load()
