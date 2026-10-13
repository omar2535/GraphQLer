from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

from graphqler import config
from graphqler.fuzzer.engine.fengine import FEngine
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats


def test_runtime_settings_are_isolated_between_threads():
    default_output = config.OUTPUT_DIRECTORY

    def active_output(path: str) -> str:
        settings = config.snapshot({"OUTPUT_DIRECTORY": path})
        with config.activate(settings):
            return config.OUTPUT_DIRECTORY

    with ThreadPoolExecutor(max_workers=2) as executor:
        outputs = list(executor.map(active_output, ["output-a", "output-b"]))

    assert outputs == ["output-a", "output-b"]
    assert config.OUTPUT_DIRECTORY == default_output


def test_snapshot_rejects_unknown_configuration_key():
    try:
        config.snapshot({"DOES_NOT_EXIST": True})
    except KeyError as exc:
        assert "DOES_NOT_EXIST" in str(exc)
    else:
        raise AssertionError("unknown configuration key was accepted")


def test_mutable_run_services_are_not_singletons():
    api = MagicMock()

    first_stats = Stats()
    second_stats = Stats()
    first_bucket = ObjectsBucket(api)
    second_bucket = ObjectsBucket(api)
    first_engine = FEngine(api, first_stats)
    second_engine = FEngine(api, second_stats)

    assert first_stats is not second_stats
    assert first_bucket is not second_bucket
    assert first_engine is not second_engine
    assert first_engine.stats is first_stats
    assert second_engine.stats is second_stats


def test_logger_paths_follow_active_run_settings(tmp_path):
    first = config.snapshot({"OUTPUT_DIRECTORY": str(tmp_path / "first")})
    second = config.snapshot({"OUTPUT_DIRECTORY": str(tmp_path / "second")})

    with config.activate(first):
        first_logger = Logger()
    with config.activate(second):
        second_logger = Logger()

    assert first_logger.fuzzer_log_path.parent.parent == tmp_path / "first"
    assert second_logger.fuzzer_log_path.parent.parent == tmp_path / "second"
