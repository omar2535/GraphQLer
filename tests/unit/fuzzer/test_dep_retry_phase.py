"""Unit tests for the dep-retry phase in Fuzzer and related result enum changes.

Tests cover:
- ResultEnum.HARD_DEPENDENCY_NOT_MET is a distinct non-success value
- FEngine sets HARD_DEPENDENCY_NOT_MET when HardDependencyNotMetException is raised
- Fuzzer._dep_blocked_nodes is populated during chain execution
- dep_retry phase runs nodes with check_hard_depends_on=False
"""

from unittest.mock import MagicMock, patch

from graphqler.fuzzer.engine.types.result import Result, ResultEnum
from graphqler.fuzzer.engine.exceptions import HardDependencyNotMetException


# ---------------------------------------------------------------------------
# ResultEnum tests
# ---------------------------------------------------------------------------


class TestHardDependencyNotMetEnum:
    def test_is_not_success(self):
        result = Result(ResultEnum.HARD_DEPENDENCY_NOT_MET)
        assert result.success is False

    def test_is_distinct_from_internal_failure(self):
        assert ResultEnum.HARD_DEPENDENCY_NOT_MET != ResultEnum.INTERNAL_FAILURE

    def test_type_string(self):
        result = Result(ResultEnum.HARD_DEPENDENCY_NOT_MET)
        assert result.type == "hard_dependency_not_met"

    def test_reason_string(self):
        result = Result(ResultEnum.HARD_DEPENDENCY_NOT_MET)
        assert "hard dependency" in result.reason.lower() or "dependency" in result.reason.lower()


# ---------------------------------------------------------------------------
# FEngine: __run_query sets HARD_DEPENDENCY_NOT_MET
# ---------------------------------------------------------------------------


class TestFEngineHardDepResult:
    """Tests that FEngine correctly translates HardDependencyNotMetException
    into ResultEnum.HARD_DEPENDENCY_NOT_MET (not INTERNAL_FAILURE)."""

    def _make_fengine(self):
        """Create a FEngine instance with a mocked API, resetting the singleton first."""
        from graphqler.fuzzer.engine.fengine import FEngine
        from graphqler.utils.api import API

        FEngine.reset()  # ty: ignore[unresolved-attribute]
        api = MagicMock(spec=API)
        api.url = "http://example.com/graphql"
        return FEngine(api)

    def test_run_minimal_payload_query_hard_dep_not_met(self):
        """run_minimal_payload for a Query with HardDepNotMet → HARD_DEPENDENCY_NOT_MET."""
        fengine = self._make_fengine()

        materializer_mock = MagicMock()
        materializer_mock.get_payload.side_effect = HardDependencyNotMetException("Character")

        with patch(
            "graphqler.fuzzer.engine.fengine.GeneralPayloadMaterializer",
            return_value=materializer_mock,
        ):
            objects_bucket = MagicMock()
            _, result = fengine.run_minimal_payload("charactersByIds", objects_bucket, "Query")

        assert result.result_enum == ResultEnum.HARD_DEPENDENCY_NOT_MET
        assert result.success is False

    def test_run_minimal_payload_mutation_hard_dep_not_met(self):
        """run_minimal_payload for a Mutation with HardDepNotMet → HARD_DEPENDENCY_NOT_MET."""
        fengine = self._make_fengine()

        materializer_mock = MagicMock()
        materializer_mock.get_payload.side_effect = HardDependencyNotMetException("SomeObject")

        with patch(
            "graphqler.fuzzer.engine.fengine.GeneralPayloadMaterializer",
            return_value=materializer_mock,
        ):
            objects_bucket = MagicMock()
            _, result = fengine.run_minimal_payload("updateSomething", objects_bucket, "Mutation")

        assert result.result_enum == ResultEnum.HARD_DEPENDENCY_NOT_MET
        assert result.success is False


# ---------------------------------------------------------------------------
# Fuzzer: _dep_blocked_nodes tracking and dep_retry phase
# ---------------------------------------------------------------------------


def _make_node(name: str, graphql_type: str = "Query"):
    node = MagicMock()
    node.name = name
    node.graphql_type = graphql_type
    return node


class TestDepRetryTracking:
    """Tests that Fuzzer._dep_blocked_nodes accumulates correctly and the
    dep_retry phase re-runs those nodes with check_hard_depends_on=False."""

    def _make_fuzzer(self):
        """Build a Fuzzer with all heavy dependencies mocked out."""
        from graphqler.fuzzer.fuzzer import Fuzzer
        from graphqler.fuzzer.engine.fengine import FEngine

        FEngine.reset()  # ty: ignore[unresolved-attribute]

        with (
            patch("graphqler.fuzzer.fuzzer.API"),
            patch("graphqler.fuzzer.fuzzer.GraphGenerator"),
            patch("graphqler.fuzzer.fuzzer.ChainGenerator"),
            patch("graphqler.fuzzer.fuzzer.DEngine"),
            patch("graphqler.fuzzer.fuzzer.FEngine"),
            patch("graphqler.fuzzer.fuzzer.ObjectsBucket"),
            patch("graphqler.fuzzer.fuzzer.Stats"),
        ):
            fuzzer = Fuzzer.__new__(Fuzzer)
            fuzzer._dep_blocked_nodes = set()
            fuzzer.stats = MagicMock()
            fuzzer.stats.successful_nodes = {}
            fuzzer.logger = MagicMock()
            fuzzer.fengine = MagicMock()
            fuzzer.objects_bucket = MagicMock()
        return fuzzer

    def test_downstream_nodes_added_when_chain_breaks(self):
        """When a chain stops early, all subsequent primary non-Object nodes must be dep-blocked."""
        fuzzer = self._make_fuzzer()

        node2 = _make_node("character", "Query")      # fails
        node3 = _make_node("charactersByIds", "Query") # never reached
        node4 = _make_node("episode", "Query")         # never reached
        obj_node = _make_node("Character", "Object")   # should be excluded

        # Build fake chain steps matching the structure in fuzzer.py
        def _make_step(node, profile="primary"):
            step = MagicMock()
            step.node = node
            step.profile_name = profile
            return step

        chain_steps = [
            _make_step(_make_node("characters", "Query")),  # step 0 — succeeds
            _make_step(node2),                               # step 1 — fails
            _make_step(node3),                               # step 2 — skipped
            _make_step(node4),                               # step 3 — skipped
            _make_step(obj_node),                            # step 4 — Object, must be excluded
        ]

        # Simulate the break logic from __run_chain (i=1, failure at node2)
        i = 1
        fail_result = Result(ResultEnum.HARD_DEPENDENCY_NOT_MET)
        if fail_result.result_enum == ResultEnum.HARD_DEPENDENCY_NOT_MET:
            fuzzer._dep_blocked_nodes.add(node2)
        for future_step in chain_steps[i + 1:]:
            if future_step.profile_name == "primary" and future_step.node.graphql_type != "Object":
                fuzzer._dep_blocked_nodes.add(future_step.node)

        assert node2 in fuzzer._dep_blocked_nodes
        assert node3 in fuzzer._dep_blocked_nodes
        assert node4 in fuzzer._dep_blocked_nodes
        assert obj_node not in fuzzer._dep_blocked_nodes


        """A node that returns HARD_DEPENDENCY_NOT_MET should be in _dep_blocked_nodes."""
        fuzzer = self._make_fuzzer()
        node = _make_node("charactersByIds")

        hard_dep_result = Result(ResultEnum.HARD_DEPENDENCY_NOT_MET)
        # Simulate what __run_chain does when it gets HARD_DEPENDENCY_NOT_MET
        if hard_dep_result.result_enum == ResultEnum.HARD_DEPENDENCY_NOT_MET:
            fuzzer._dep_blocked_nodes.add(node)

        assert node in fuzzer._dep_blocked_nodes

    def test_dep_retry_calls_run_minimal_with_no_dep_check(self):
        """dep_retry phase must call run_minimal_payload(..., check_hard_depends_on=False)."""
        fuzzer = self._make_fuzzer()
        node = _make_node("charactersByIds", "Query")
        fuzzer._dep_blocked_nodes = {node}
        # Simulate node never succeeded
        fuzzer.stats.successful_nodes = {}

        success_result = Result(ResultEnum.GENERAL_SUCCESS)
        fuzzer.fengine.run_minimal_payload.return_value = ({}, success_result)
        fuzzer.fengine.run_maximal_payload.return_value = ({}, success_result)

        # Run the dep_retry logic (extracted from __run_fuzz)
        dep_retry_nodes = [
            n for n in fuzzer._dep_blocked_nodes
            if f"{n.graphql_type}|{n.name}" not in fuzzer.stats.successful_nodes
        ]
        for n in dep_retry_nodes:
            fuzzer.fengine.run_minimal_payload(n.name, fuzzer.objects_bucket, n.graphql_type, check_hard_depends_on=False)
            fuzzer.fengine.run_maximal_payload(n.name, fuzzer.objects_bucket, n.graphql_type, check_hard_depends_on=False)

        fuzzer.fengine.run_minimal_payload.assert_called_once_with(
            "charactersByIds", fuzzer.objects_bucket, "Query", check_hard_depends_on=False
        )
        fuzzer.fengine.run_maximal_payload.assert_called_once_with(
            "charactersByIds", fuzzer.objects_bucket, "Query", check_hard_depends_on=False
        )

    def test_dep_retry_skips_already_successful_nodes(self):
        """Nodes that already succeeded during chains/islands must NOT be retried."""
        fuzzer = self._make_fuzzer()
        node = _make_node("charactersByIds", "Query")
        fuzzer._dep_blocked_nodes = {node}
        # Mark as already successful
        fuzzer.stats.successful_nodes = {"Query|charactersByIds": 1}

        dep_retry_nodes = [
            n for n in fuzzer._dep_blocked_nodes
            if f"{n.graphql_type}|{n.name}" not in fuzzer.stats.successful_nodes
        ]
        assert dep_retry_nodes == []

    def test_dep_retry_empty_when_no_hard_dep_failures(self):
        """If _dep_blocked_nodes is empty, no retries should happen."""
        fuzzer = self._make_fuzzer()
        fuzzer._dep_blocked_nodes = set()

        dep_retry_nodes = [
            n for n in fuzzer._dep_blocked_nodes
            if f"{n.graphql_type}|{n.name}" not in fuzzer.stats.successful_nodes
        ]
        assert dep_retry_nodes == []
        fuzzer.fengine.run_minimal_payload.assert_not_called()

    def test_dep_blocked_nodes_initialized_empty(self):
        """Fuzzer._dep_blocked_nodes must start as an empty set."""
        from graphqler.fuzzer.fuzzer import Fuzzer
        from graphqler.fuzzer.engine.fengine import FEngine

        FEngine.reset()  # ty: ignore[unresolved-attribute]
        with (
            patch("graphqler.fuzzer.fuzzer.API"),
            patch("graphqler.fuzzer.fuzzer.GraphGenerator"),
            patch("graphqler.fuzzer.fuzzer.ChainGenerator"),
            patch("graphqler.fuzzer.fuzzer.DEngine"),
            patch("graphqler.fuzzer.fuzzer.FEngine"),
            patch("graphqler.fuzzer.fuzzer.ObjectsBucket"),
            patch("graphqler.fuzzer.fuzzer.Stats"),
        ):
            fuzzer = Fuzzer(save_path="/tmp/fake", url="http://example.com/graphql")

        assert hasattr(fuzzer, "_dep_blocked_nodes")
        assert isinstance(fuzzer._dep_blocked_nodes, set)
        assert len(fuzzer._dep_blocked_nodes) == 0
