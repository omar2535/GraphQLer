"""WebSocket utilities for GraphQL subscriptions.

Supports two sub-protocols:
  - "graphql-ws"                 (modern, RFC-compliant; https://github.com/enisdenjo/graphql-ws)
  - "subscriptions-transport-ws" (legacy Apollo; https://github.com/apollographql/subscriptions-transport-ws)
"""

import asyncio
import json
import logging
from typing import Any, Optional, cast

from graphqler import config

logger = logging.getLogger(__name__)


async def _send_graphql_ws(websocket, payload: dict, timeout: float) -> list[dict]:
    """graphql-ws protocol handler (modern standard)."""
    # 1. Send connection_init
    await websocket.send(json.dumps({"type": "connection_init", "payload": {}}))

    # 2. Wait for connection_ack
    ack_raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
    ack = json.loads(ack_raw)
    if ack.get("type") != "connection_ack":
        return []

    # 3. Send subscribe message
    await websocket.send(json.dumps({"id": "1", "type": "subscribe", "payload": payload}))

    # 4. Collect events until timeout or "complete"
    events: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        msg = json.loads(raw)
        if msg.get("type") == "next":
            events.append(msg.get("payload", {}))
        elif msg.get("type") == "complete":
            break
        elif msg.get("type") == "error":
            break

    return events


async def _send_subscriptions_transport_ws(websocket, payload: dict, timeout: float) -> list[dict]:
    """subscriptions-transport-ws (legacy Apollo) protocol handler."""
    # 1. Send connection_init
    await websocket.send(json.dumps({"type": "connection_init", "payload": {}}))

    # 2. Wait for connection_ack
    ack_raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
    ack = json.loads(ack_raw)
    if ack.get("type") != "connection_ack":
        return []

    # 3. Send start message
    await websocket.send(json.dumps({"id": "1", "type": "start", "payload": payload}))

    # 4. Collect events until timeout or "complete"
    events: list[dict] = []
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        msg = json.loads(raw)
        if msg.get("type") == "data":
            events.append(msg.get("payload", {}))
        elif msg.get("type") == "complete":
            break
        elif msg.get("type") == "error":
            break

    return events


async def _run_subscription(url: str, payload: dict, timeout: float, protocol: str, headers: Optional[dict]) -> list[dict]:
    """Async core: connect via WebSocket and collect subscription events."""
    try:
        import websockets
    except ImportError:
        raise ImportError("The 'websockets' package is required for subscription support. Install it with: pip install websockets")

    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    extra_headers = headers or {}

    async with websockets.connect(ws_url, subprotocols=cast(Any, [protocol]), additional_headers=extra_headers) as websocket:
        if protocol == "graphql-ws":
            return await _send_graphql_ws(websocket, payload, timeout)
        else:
            return await _send_subscriptions_transport_ws(websocket, payload, timeout)


def send_graphql_subscription(
    url: str,
    payload: dict,
    timeout: float = config.SUBSCRIPTION_TIMEOUT,
    protocol: str = config.SUBSCRIPTION_PROTOCOL,
    headers: Optional[dict] = None,
) -> list[dict]:
    """Connect to a GraphQL WebSocket endpoint and collect subscription events.

    Args:
        url (str): The GraphQL endpoint URL (http:// or https:// will be converted to ws://)
        payload (dict): GraphQL payload dict with "query" key (and optionally "variables")
        timeout (float): Seconds to wait for events before returning
        protocol (str): WebSocket sub-protocol to use
        headers (dict, optional): Additional HTTP headers for the WebSocket handshake

    Returns:
        list[dict]: List of event payloads received within the timeout window
    """
    try:
        return asyncio.run(_run_subscription(url, payload, timeout, protocol, headers))
    except Exception as exc:
        logger.warning("Subscription to %s failed (%s: %s); returning empty event list.", url, type(exc).__name__, exc)
        logger.debug("Subscription exception detail:", exc_info=True)
        return []
