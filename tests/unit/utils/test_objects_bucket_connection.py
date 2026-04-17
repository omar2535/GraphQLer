"""Unit tests for ObjectsBucket connection-wrapper unpacking."""

from unittest.mock import MagicMock

from graphqler.utils.objects_bucket import ObjectsBucket


def _build_bucket(connection_fields=None):
    """Create an ObjectsBucket with a mocked API containing a CountryConnection type."""
    # Build a mock API
    api = MagicMock()
    api.is_operation_in_api.return_value = True

    # Describe the CountryConnection wrapper object
    if connection_fields is None:
        connection_fields = [
            {
                "name": "items",
                "kind": "LIST",
                "type": None,
                "inputs": {},
                "ofType": {
                    "kind": "LIST",
                    "name": None,
                    "type": None,
                    "ofType": {
                        "kind": "OBJECT",
                        "name": "Country",
                        "type": "Country",
                        "ofType": None,
                    },
                },
            }
        ]
    api.objects = {
        "CountryConnection": {
            "kind": "OBJECT",
            "name": "CountryConnection",
            "fields": connection_fields,
        },
        "Country": {"kind": "OBJECT", "name": "Country", "fields": []},
    }

    # configure get_operation to return a CountryConnection output
    api.get_operation.return_value = {
        "output": {
            "kind": "OBJECT",
            "name": "CountryConnection",
            "type": "CountryConnection",
            "ofType": None,
        }
    }

    # Access the underlying class to bypass the singleton decorator for isolated testing.
    # ObjectsBucket.__wrapped__ is the original undecorated class set by the @singleton decorator.
    real_cls = ObjectsBucket.__wrapped__
    bucket = real_cls.__new__(real_cls)
    bucket.api = api
    bucket.objects = {}
    bucket.scalars = {}
    return bucket


class TestUnpackConnectionWrapper:
    def test_items_list_unpacked_into_country(self):
        """Inner Country items from an `items` list field are stored under 'Country'."""
        bucket = _build_bucket()
        data = {"items": [{"id": "1", "name": "France"}, {"id": "2", "name": "Germany"}]}
        bucket._unpack_connection_wrapper("CountryConnection", data)
        assert "Country" in bucket.objects
        assert {"id": "1", "name": "France"} in bucket.objects["Country"]
        assert {"id": "2", "name": "Germany"} in bucket.objects["Country"]

    def test_nodes_list_unpacked(self):
        """Inner objects from a `nodes` list field are stored under the correct type."""
        nodes_field = [
            {
                "name": "nodes",
                "kind": "LIST",
                "type": None,
                "inputs": {},
                "ofType": {
                    "kind": "LIST",
                    "name": None,
                    "type": None,
                    "ofType": {
                        "kind": "OBJECT",
                        "name": "Country",
                        "type": "Country",
                        "ofType": None,
                    },
                },
            }
        ]
        bucket = _build_bucket(connection_fields=nodes_field)
        bucket.api.objects["CountryConnection"]["fields"] = nodes_field
        data = {"nodes": [{"id": "3", "name": "Spain"}]}
        bucket._unpack_connection_wrapper("CountryConnection", data)
        assert {"id": "3", "name": "Spain"} in bucket.objects.get("Country", [])

    def test_edges_node_unpacked(self):
        """Inner objects from Relay-style `edges.node` are stored under the node's type (Country), not the edge type."""
        edges_field = [
            {
                "name": "edges",
                "kind": "LIST",
                "type": None,
                "inputs": {},
                "ofType": {
                    "kind": "LIST",
                    "name": None,
                    "type": None,
                    "ofType": {
                        "kind": "OBJECT",
                        "name": "CountryEdge",
                        "type": "CountryEdge",
                        "ofType": None,
                    },
                },
            }
        ]
        # CountryEdge has a `node: Country` field
        country_edge_node_field = {
            "name": "node",
            "kind": "OBJECT",
            "type": "Country",
            "inputs": {},
            "ofType": None,
        }
        bucket = _build_bucket(connection_fields=edges_field)
        bucket.api.objects["CountryConnection"]["fields"] = edges_field
        bucket.api.objects["CountryEdge"] = {
            "kind": "OBJECT",
            "name": "CountryEdge",
            "fields": [country_edge_node_field],
        }
        data = {"edges": [{"node": {"id": "4", "name": "Italy"}}, {"node": {"id": "5", "name": "Greece"}}]}
        bucket._unpack_connection_wrapper("CountryConnection", data)
        # Nodes must be stored under 'Country', the inner node type
        assert {"id": "4", "name": "Italy"} in bucket.objects.get("Country", [])
        assert {"id": "5", "name": "Greece"} in bucket.objects.get("Country", [])

    def test_non_list_value_skipped(self):
        """A connection field value that is not a list is silently ignored."""
        bucket = _build_bucket()
        data = {"items": "not-a-list"}
        bucket._unpack_connection_wrapper("CountryConnection", data)
        assert bucket.objects == {}

    def test_unknown_outer_type_skipped(self):
        """If the outer type is not in api.objects the wrapper is silently ignored."""
        bucket = _build_bucket()
        bucket._unpack_connection_wrapper("UnknownType", {"items": [{"id": "9"}]})
        assert bucket.objects == {}

    def test_no_connection_key_in_data(self):
        """Data without items/nodes/edges does not add anything."""
        bucket = _build_bucket()
        data = {"pageInfo": {"hasNextPage": False}}
        bucket._unpack_connection_wrapper("CountryConnection", data)
        assert bucket.objects == {}


class TestParseAsObjectConnectionUnpacking:
    def test_parse_as_object_stores_outer_and_inner(self):
        """parse_as_object stores both the wrapper (CountryConnection) and inner Country items."""
        bucket = _build_bucket()
        inner_items = [{"id": "1", "name": "France"}]
        data = {"items": inner_items}
        bucket.parse_as_object("countries", data)
        # Outer wrapper stored
        assert "CountryConnection" in bucket.objects
        assert data in bucket.objects["CountryConnection"]
        # Inner items also stored
        assert "Country" in bucket.objects
        assert {"id": "1", "name": "France"} in bucket.objects["Country"]
