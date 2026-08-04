from multiprocessing import Queue
from unittest.mock import MagicMock

from graphqler import config
from graphqler.fuzzer.fuzzer import Fuzzer
from graphqler.utils.stats import Stats


def test_resume_skips_completed_chains(tmp_path):
    settings = config.snapshot(
        {
            "RESUME": True,
            "DEBUG": True,
            "MAX_FUZZING_ITERATIONS": 1,
            "SKIP_INJECTION_ATTACKS": True,
            "SKIP_MISC_ATTACKS": True,
            "SKIP_DOS_ATTACKS": True,
            "SKIP_ENUMERATION_ATTACKS": True,
            "LLM_ENABLE_REPORTER": False,
        }
    )
    stats = Stats()
    stats.set_file_paths(str(tmp_path))
    stats.phase = "chains"
    stats.current_iteration = 1
    stats.chains_completed = 1

    first_chain = MagicMock(nodes=[])
    second_chain = MagicMock(nodes=[])
    fuzzer = Fuzzer.__new__(Fuzzer)
    fuzzer.settings = settings
    fuzzer.stats = stats
    fuzzer.chains = [first_chain, second_chain]
    fuzzer.dependency_graph = MagicMock(nodes=[])
    fuzzer.logger = MagicMock()
    fuzzer.objects_bucket = MagicMock()
    fuzzer.dengine = MagicMock()
    fuzzer.fengine = MagicMock()
    fuzzer._dep_blocked_nodes = set()
    fuzzer.save_path = str(tmp_path)
    fuzzer.url = "https://example.test/graphql"
    fuzzer._Fuzzer__run_chain = MagicMock()

    with config.activate(settings):
        fuzzer._Fuzzer__run_fuzz(Queue())

    fuzzer._Fuzzer__run_chain.assert_called_once_with(second_chain)
    assert stats.phase == "completed"
    assert stats.chains_completed == 2


def test_resume_of_completed_run_is_noop(tmp_path):
    settings = config.snapshot({"RESUME": True, "DEBUG": True})
    fuzzer = Fuzzer.__new__(Fuzzer)
    fuzzer.settings = settings
    fuzzer.stats = Stats()
    fuzzer.stats.set_file_paths(str(tmp_path))
    fuzzer.stats.phase = "completed"
    fuzzer.logger = MagicMock()

    with config.activate(settings):
        fuzzer._Fuzzer__run_fuzz(Queue())

    fuzzer.logger.info.assert_called_once_with("Run checkpoint is already complete; nothing to resume")
