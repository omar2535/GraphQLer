from unittest.mock import MagicMock, patch

from graphqler import config
from graphqler.fuzzer.engine.types import Result, ResultEnum
from graphqler.fuzzer.engine.types.profile import RuntimeProfile
from graphqler.fuzzer.fuzzer import Fuzzer
from graphqler.graph.node import Node
from graphqler.utils.stats import Stats


def _fuzzer():
    fuzzer = Fuzzer.__new__(Fuzzer)
    fuzzer.api = MagicMock()
    fuzzer.api.queries = {
        "viewer": {
            "output": {"kind": "OBJECT", "name": "User", "ofType": None},
        }
    }
    fuzzer.api.mutations = {
        "updateProfile": {
            "output": {"kind": "OBJECT", "name": "User", "ofType": None},
        }
    }
    fuzzer.api.subscriptions = {}
    fuzzer.api.objects = {"User": {"fields": [{"name": "id"}, {"name": "email"}]}}
    fuzzer.profiles = {
        "primary": RuntimeProfile(name="primary", auth_token="token-a"),
        "secondary": RuntimeProfile(name="secondary", auth_token="token-b"),
        "post_delete": RuntimeProfile(name="post_delete", auth_token="token-a"),
    }
    fuzzer.fengine = MagicMock()
    alternate = Result(
        ResultEnum.HAS_DATA_SUCCESS,
        payload="query { viewer { id email } }",
        graphql_response={"data": {"viewer": {"id": "1"}}},
    )
    fuzzer.fengine.run_payload_with_profile.return_value = (alternate.graphql_response, alternate)
    fuzzer.authorization_detector = MagicMock()
    fuzzer.stats = Stats()
    fuzzer._authorization_tested_nodes = set()
    return fuzzer


def test_private_query_replays_exact_payload_for_anonymous_and_alternate_profiles():
    fuzzer = _fuzzer()
    node = Node("Query", "viewer", {})
    primary = Result(
        ResultEnum.HAS_DATA_SUCCESS,
        payload="query { viewer { id email } }",
        graphql_response={"data": {"viewer": {"id": "1", "email": "a@example.test"}}},
    )
    settings = config.snapshot({"AUTHORIZATION_DIFFERENTIAL": True})

    with (
        config.activate(settings),
        patch(
            "graphqler.fuzzer.fuzzer.EndpointPrivacyClassifier.classify",
            return_value="private",
        ),
    ):
        fuzzer._Fuzzer__run_authorization_differential(node, primary)

    calls = fuzzer.fengine.run_payload_with_profile.call_args_list
    assert [call.args[2].name for call in calls] == ["anonymous", "secondary"]
    assert all(call.args[1] == primary.payload for call in calls)
    fuzzer.authorization_detector.detect.assert_called_once()


def test_public_query_is_not_replayed():
    fuzzer = _fuzzer()
    node = Node("Query", "viewer", {})
    primary = Result(ResultEnum.HAS_DATA_SUCCESS, payload="query { viewer { id } }")
    settings = config.snapshot({"AUTHORIZATION_DIFFERENTIAL": True})

    with (
        config.activate(settings),
        patch(
            "graphqler.fuzzer.fuzzer.EndpointPrivacyClassifier.classify",
            return_value="public",
        ),
    ):
        fuzzer._Fuzzer__run_authorization_differential(node, primary)

    fuzzer.fengine.run_payload_with_profile.assert_not_called()


def test_private_mutation_is_replayed_under_each_profile():
    fuzzer = _fuzzer()
    node = Node("Mutation", "updateProfile", {})
    primary = Result(
        ResultEnum.HAS_DATA_SUCCESS,
        payload='mutation { updateProfile(name: "new") { id email } }',
        graphql_response={"data": {"updateProfile": {"id": "1", "email": "a@example.test"}}},
    )
    settings = config.snapshot({"AUTHORIZATION_DIFFERENTIAL": True})

    with (
        config.activate(settings),
        patch(
            "graphqler.fuzzer.fuzzer.EndpointPrivacyClassifier.classify",
            return_value="private",
        ),
    ):
        fuzzer._Fuzzer__run_authorization_differential(node, primary)

    assert fuzzer.fengine.run_payload_with_profile.call_count == 2
    assert all(call.args[1] == primary.payload for call in fuzzer.fengine.run_payload_with_profile.call_args_list)
