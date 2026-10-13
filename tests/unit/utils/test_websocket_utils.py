import asyncio
import json
from unittest.mock import AsyncMock

from graphqler.utils.websocket_utils import _send_graphql_ws, _send_subscriptions_transport_ws


def test_modern_protocol_sends_auth_in_connection_init():
    websocket = AsyncMock()
    websocket.recv.side_effect = [
        json.dumps({"type": "connection_ack"}),
        json.dumps({"type": "next", "payload": {"data": {"privateUpdates": {"id": "1"}}}}),
        json.dumps({"type": "complete"}),
    ]

    events = asyncio.run(
        _send_graphql_ws(
            websocket,
            {"query": "subscription { privateUpdates { id } }"},
            1,
            {"Authorization": "Bearer token-a", "X-Tenant": "a"},
        )
    )

    first_message = json.loads(websocket.send.await_args_list[0].args[0])
    assert first_message == {
        "type": "connection_init",
        "payload": {"Authorization": "Bearer token-a", "X-Tenant": "a"},
    }
    assert events == [{"data": {"privateUpdates": {"id": "1"}}}]


def test_legacy_protocol_sends_auth_in_connection_init():
    websocket = AsyncMock()
    websocket.recv.side_effect = [
        json.dumps({"type": "connection_ack"}),
        json.dumps({"type": "data", "payload": {"data": {"privateUpdates": {"id": "1"}}}}),
        json.dumps({"type": "complete"}),
    ]

    events = asyncio.run(
        _send_subscriptions_transport_ws(
            websocket,
            {"query": "subscription { privateUpdates { id } }"},
            1,
            {"Authorization": "Bearer token-b"},
        )
    )

    first_message = json.loads(websocket.send.await_args_list[0].args[0])
    assert first_message["payload"]["Authorization"] == "Bearer token-b"
    assert events == [{"data": {"privateUpdates": {"id": "1"}}}]
