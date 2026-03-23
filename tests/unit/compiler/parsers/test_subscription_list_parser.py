"""Unit tests for SubscriptionListParser."""

import pytest
from graphqler.compiler.parsers.subscription_list_parser import SubscriptionListParser


def _make_introspection(subscriptions: list[dict] | None, subscription_type_name: str = "Subscription") -> dict:
    """Build a minimal introspection result dict."""
    types = []
    if subscriptions is not None:
        types.append({
            "kind": "OBJECT",
            "name": subscription_type_name,
            "fields": subscriptions,
        })
    return {
        "data": {
            "__schema": {
                "subscriptionType": {"name": subscription_type_name} if subscriptions is not None else None,
                "types": types,
            }
        }
    }


def _make_subscription_field(name: str, args: list[dict] | None = None, return_type_name: str = "Order") -> dict:
    return {
        "name": name,
        "args": args or [],
        "type": {"kind": "OBJECT", "name": return_type_name, "ofType": None},
    }


class TestSubscriptionListParserNoSubscriptions:
    def test_returns_empty_when_subscription_type_is_null(self):
        data = _make_introspection(None)
        result = SubscriptionListParser().parse(data)
        assert result == {}

    def test_returns_empty_when_schema_has_no_subscription_type_key(self):
        data = {"data": {"__schema": {"types": []}}}
        result = SubscriptionListParser().parse(data)
        assert result == {}


class TestSubscriptionListParserWithSubscriptions:
    def test_parses_single_subscription_no_args(self):
        data = _make_introspection([_make_subscription_field("onOrderCreated")])
        result = SubscriptionListParser().parse(data)

        assert "onOrderCreated" in result
        sub = result["onOrderCreated"]
        assert sub["name"] == "onOrderCreated"
        assert sub["inputs"] == {}
        assert sub["output"]["name"] == "Order"

    def test_parses_subscription_with_input_arg(self):
        args = [{"name": "orderId", "type": {"name": "ID", "kind": "SCALAR", "ofType": None}}]
        data = _make_introspection([_make_subscription_field("onOrderUpdated", args=args)])
        result = SubscriptionListParser().parse(data)

        sub = result["onOrderUpdated"]
        assert "orderId" in sub["inputs"]
        assert sub["inputs"]["orderId"]["name"] == "orderId"

    def test_parses_multiple_subscriptions(self):
        fields = [
            _make_subscription_field("onOrderCreated"),
            _make_subscription_field("onOrderCancelled", return_type_name="Order"),
            _make_subscription_field("onUserRegistered", return_type_name="User"),
        ]
        result = SubscriptionListParser().parse(_make_introspection(fields))

        assert set(result.keys()) == {"onOrderCreated", "onOrderCancelled", "onUserRegistered"}

    def test_custom_subscription_type_name(self):
        """APIs can name their subscription root type anything (e.g. 'RootSubscription')."""
        fields = [_make_subscription_field("onPing", return_type_name="Ping")]
        data = _make_introspection(fields, subscription_type_name="RootSubscription")
        result = SubscriptionListParser().parse(data)
        assert "onPing" in result
