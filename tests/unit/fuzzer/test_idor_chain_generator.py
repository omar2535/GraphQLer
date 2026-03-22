"""Unit tests for Chain (IDOR fields) and heuristic IDOR classifier."""

import unittest

from graphqler.chains.chain import Chain, ChainStep
from graphqler.graph.node import Node
from graphqler.chains.idor import heuristic_idor_classifier


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_node(graphql_type: str, name: str, mutation_type: str | None = None, body: dict | None = None) -> Node:
    node = Node(graphql_type=graphql_type, name=name, body=body or {})
    if mutation_type:
        node.set_mutation_type(mutation_type)
    return node


def _make_chain(nodes: list[Node], name: str = "test-chain") -> Chain:
    """Build a plain (single-profile) chain from a list of nodes."""
    return Chain(steps=[ChainStep(node=n) for n in nodes], name=name)


def _make_idor_chain(setup_nodes: list[Node], test_nodes: list[Node], name: str = "test-chain", confidence: float = 0.0) -> Chain:
    """Build a multi-profile IDOR chain: setup nodes are primary, test nodes are secondary."""
    steps = [ChainStep(node=n, profile_name="primary") for n in setup_nodes]
    steps += [ChainStep(node=n, profile_name="secondary") for n in test_nodes]
    return Chain(steps=steps, name=name, confidence=confidence)


# ── Chain IDOR field tests ────────────────────────────────────────────────────

class TestChainIDORFields(unittest.TestCase):
    def test_primary_steps_come_before_secondary(self):
        create_node = _make_node("Mutation", "createUser", "CREATE")
        get_node = _make_node("Query", "getUser")
        chain = _make_idor_chain([create_node], [get_node], name="c")

        primary_nodes = [s.node for s in chain.steps if s.profile_name == "primary"]
        secondary_nodes = [s.node for s in chain.steps if s.profile_name == "secondary"]
        self.assertEqual(primary_nodes, [create_node])
        self.assertEqual(secondary_nodes, [get_node])

    def test_all_secondary_chain_is_multi_profile(self):
        node = _make_node("Query", "getUser")
        chain = Chain(steps=[ChainStep(node=node, profile_name="secondary")], name="c")
        self.assertTrue(chain.is_multi_profile is False)  # only one profile type — not "multi"

    def test_repr_shows_nodes_and_confidence(self):
        create_node = _make_node("Mutation", "createUser", "CREATE")
        get_node = _make_node("Query", "getUser")
        chain = _make_idor_chain([create_node], [get_node], name="c", confidence=0.9)
        r = repr(chain)
        self.assertIn("createUser", r)
        self.assertIn("getUser", r)

    def test_repr_single_profile_chain(self):
        node = _make_node("Query", "getUser")
        chain = _make_chain([node], name="c")
        self.assertIn("getUser", repr(chain))

    def test_single_profile_chain_is_not_multi_profile(self):
        chain = _make_chain([_make_node("Query", "getUser")])
        self.assertFalse(chain.is_multi_profile)

    def test_multi_profile_chain_is_multi_profile(self):
        create_node = _make_node("Mutation", "createUser", "CREATE")
        get_node = _make_node("Query", "getUser")
        chain = _make_idor_chain([create_node], [get_node])
        self.assertTrue(chain.is_multi_profile)


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
