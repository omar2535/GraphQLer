"""Unit tests for Chain (IDOR fields) and heuristic IDOR classifier."""

import unittest

from graphqler.chains.chain import Chain
from graphqler.graph.node import Node
from graphqler.chains.idor import heuristic_idor_classifier


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_node(graphql_type: str, name: str, mutation_type: str | None = None, body: dict | None = None) -> Node:
    node = Node(graphql_type=graphql_type, name=name, body=body or {})
    if mutation_type:
        node.set_mutation_type(mutation_type)
    return node


def _make_chain(nodes: list[Node], name: str = "test-chain") -> Chain:
    return Chain(nodes=nodes, name=name)


# ── Chain IDOR field tests ────────────────────────────────────────────────────

class TestChainIDORFields(unittest.TestCase):
    def test_split_index_partitions_nodes(self):
        create_node = _make_node("Mutation", "createUser", "CREATE")
        get_node = _make_node("Query", "getUser")
        chain = Chain(nodes=[create_node, get_node], name="c", split_index=1)

        self.assertEqual(chain.nodes[:chain.split_index], [create_node])
        self.assertEqual(chain.nodes[chain.split_index:], [get_node])

    def test_split_index_zero_means_all_test(self):
        node = _make_node("Query", "getUser")
        chain = Chain(nodes=[node], name="c", split_index=0)
        self.assertEqual(chain.nodes[:chain.split_index], [])
        self.assertEqual(chain.nodes[chain.split_index:], [node])

    def test_repr_shows_split_when_set(self):
        create_node = _make_node("Mutation", "createUser", "CREATE")
        get_node = _make_node("Query", "getUser")
        chain = Chain(nodes=[create_node, get_node], name="c", split_index=1, confidence=0.9)
        r = repr(chain)
        self.assertIn("createUser", r)
        self.assertIn("getUser", r)
        self.assertIn("0.90", r)

    def test_repr_no_split_is_simple(self):
        node = _make_node("Query", "getUser")
        chain = Chain(nodes=[node], name="c")
        self.assertNotIn("||", repr(chain))
        self.assertIn("getUser", repr(chain))

    def test_no_split_index_default(self):
        chain = Chain(nodes=[_make_node("Query", "getUser")])
        self.assertIsNone(chain.split_index)


# ── Heuristic classifier tests ────────────────────────────────────────────────

class TestHeuristicIDORClassifier(unittest.TestCase):
    # ── Single-node chains ────────────────────────────────────────────────────

    def test_single_node_chain_returns_zero(self):
        chain = _make_chain([_make_node("Mutation", "createUser", "CREATE")])
        confidence, split, reason = heuristic_idor_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(split, 0)

    # ── No CREATE mutation ────────────────────────────────────────────────────

    def test_no_create_mutation_returns_zero(self):
        chain = _make_chain([
            _make_node("Query", "listItems"),
            _make_node("Query", "getItem"),
        ])
        confidence, _, reason = heuristic_idor_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("CREATE", reason)

    # ── CREATE is the last node ───────────────────────────────────────────────

    def test_create_as_last_node_returns_zero(self):
        chain = _make_chain([
            _make_node("Query", "listUsers"),
            _make_node("Mutation", "createUser", "CREATE"),
        ])
        confidence, _, reason = heuristic_idor_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("last node", reason)

    # ── ID param signal ───────────────────────────────────────────────────────

    def test_id_param_signal_adds_confidence(self):
        id_input = {
            "userId": {
                "kind": "SCALAR",
                "name": "userId",
                "type": "ID",
                "ofType": None,
            }
        }
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        get_node = _make_node("Query", "getItem", body={"inputs": id_input})
        chain = _make_chain([create_node, get_node])
        confidence, split, _ = heuristic_idor_classifier.classify(chain)
        self.assertGreater(confidence, 0.0)
        self.assertEqual(split, 1)

    # ── Type-match signal ─────────────────────────────────────────────────────

    def test_type_match_adds_high_confidence(self):
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        get_node = _make_node("Query", "getUser", body={
            "inputs": {
                "userId": {
                    "kind": "INPUT_OBJECT",
                    "name": "userId",
                    "type": "User",
                    "ofType": None,
                }
            }
        })
        chain = _make_chain([create_node, get_node])
        confidence, split, reason = heuristic_idor_classifier.classify(chain)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertEqual(split, 1)
        self.assertIn("type-match", reason)

    # ── Private name heuristic ────────────────────────────────────────────────

    def test_private_name_adds_confidence(self):
        create_node = _make_node("Mutation", "createOrder", "CREATE")
        get_node = _make_node("Query", "getUserOrder")
        chain = _make_chain([create_node, get_node])
        confidence, _, reason = heuristic_idor_classifier.classify(chain)
        self.assertGreater(confidence, 0.0)
        self.assertIn("name-heuristic", reason)

    # ── Public name penalty ───────────────────────────────────────────────────

    def test_public_name_penalises_confidence(self):
        id_input = {
            "id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}
        }
        create_node = _make_node("Mutation", "createProduct", "CREATE")
        get_node = _make_node("Query", "listAllPublicProducts", body={"inputs": id_input})
        chain = _make_chain([create_node, get_node])
        confidence_penalised, _, _ = heuristic_idor_classifier.classify(chain)

        get_node_private = _make_node("Query", "getUserOrder", body={"inputs": id_input})
        chain_private = _make_chain([create_node, get_node_private])
        confidence_private, _, _ = heuristic_idor_classifier.classify(chain_private)

        self.assertLessEqual(confidence_penalised, confidence_private)

    # ── High-confidence end-to-end ────────────────────────────────────────────

    def test_high_confidence_for_create_then_get_user(self):
        id_input = {
            "userId": {
                "kind": "NON_NULL",
                "name": "userId",
                "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None},
                "type": None,
            }
        }
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        get_node = _make_node("Query", "getUser", body={"inputs": id_input})
        chain = _make_chain([create_node, get_node])
        confidence, split, reason = heuristic_idor_classifier.classify(chain)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertEqual(split, 1)


if __name__ == "__main__":
    unittest.main()
