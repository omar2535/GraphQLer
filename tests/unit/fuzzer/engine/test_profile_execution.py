from unittest.mock import MagicMock, patch

from graphqler.fuzzer.engine.fengine import FEngine
from graphqler.fuzzer.engine.types.profile import RuntimeProfile
from graphqler.utils.stats import Stats


def test_exact_query_payload_uses_profile_headers():
    api = MagicMock(url="https://example.test/graphql")
    response = MagicMock(status_code=200, text='{"data":{"viewer":{"id":"1"}}}')
    graphql_response = {"data": {"viewer": {"id": "1"}}}
    profile = RuntimeProfile(name="user-b", auth_token="token-b", headers={"X-Tenant": "b"})

    with patch(
        "graphqler.fuzzer.engine.fengine._request_utils.send_graphql_request_with_headers",
        return_value=(graphql_response, response),
    ) as send:
        returned, result = FEngine(api, Stats()).run_payload_with_profile(
            "viewer",
            "query { viewer { id } }",
            profile,
        )

    assert returned == graphql_response
    assert result.success is True
    assert result.payload == "query { viewer { id } }"
    send.assert_called_once_with(
        api.url,
        "query { viewer { id } }",
        {"X-Tenant": "b", "Authorization": "Bearer token-b"},
    )


def test_exact_subscription_payload_uses_profile_headers_and_records_events():
    api = MagicMock(url="https://example.test/graphql")
    profile = RuntimeProfile(name="anonymous", headers={"X-Tenant": "public"})
    events = [{"data": {"privateUpdates": {"id": "1"}}}]

    with patch("graphqler.utils.websocket_utils.send_graphql_subscription", return_value=events) as send:
        returned, result = FEngine(api, Stats()).run_subscription_with_profile(
            "privateUpdates",
            "subscription { privateUpdates { id } }",
            profile,
        )

    assert returned == events
    assert result.success is True
    assert result.payload == "subscription { privateUpdates { id } }"
    assert result.graphql_response == events
    send.assert_called_once_with(
        url=api.url,
        payload={"query": "subscription { privateUpdates { id } }"},
        headers={"X-Tenant": "public"},
    )
