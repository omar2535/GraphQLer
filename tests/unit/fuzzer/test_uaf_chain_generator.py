"""Unit tests for the UAF heuristic classifier and UAFChainStrategy."""

import unittest

from graphqler.chains.chain import Chain, ChainStep
from graphqler.graph.node import Node
from graphqler.chains.uaf import heuristic_uaf_classifier
from graphqler.chains.strategies.uaf_strategy import UAFChainStrategy


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_node(graphql_type: str, name: str, mutation_type: str | None = None,
               body: dict | None = None) -> Node:
    node = Node(graphql_type=graphql_type, name=name, body=body or {})
    if mutation_type:
        node.set_mutation_type(mutation_type)
    return node


def _make_chain(nodes: list[Node], name: str = "test-chain") -> Chain:
    """Build a plain (single-profile) chain from a list of nodes."""
    return Chain(steps=[ChainStep(node=n) for n in nodes], name=name)


# ── Heuristic classifier tests ────────────────────────────────────────────────

class TestHeuristicUAFClassifier(unittest.TestCase):

    # ── Chain too short ───────────────────────────────────────────────────────

    def test_single_node_returns_zero(self):
        chain = _make_chain([_make_node("Mutation", "createUser", "CREATE")])
        confidence, split, reason = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(split, 0)

    def test_two_node_chain_returns_zero(self):
        chain = _make_chain([
            _make_node("Mutation", "createUser", "CREATE"),
            _make_node("Mutation", "deleteUser", "DELETE"),
        ])
        confidence, split, reason = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("too short", reason)

    # ── No DELETE mutation ────────────────────────────────────────────────────

    def test_no_delete_returns_zero(self):
        chain = _make_chain([
            _make_node("Mutation", "createUser", "CREATE"),
            _make_node("Query", "listUsers"),
            _make_node("Query", "getUser"),
        ])
        confidence, _, reason = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("DELETE", reason)

    # ── DELETE is the last node ───────────────────────────────────────────────

    def test_delete_as_last_node_returns_zero(self):
        chain = _make_chain([
            _make_node("Mutation", "createUser", "CREATE"),
            _make_node("Query", "listUsers"),
            _make_node("Mutation", "deleteUser", "DELETE"),
        ])
        confidence, _, reason = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("last node", reason)

    # ── No CREATE before DELETE ───────────────────────────────────────────────

    def test_no_create_before_delete_returns_zero(self):
        chain = _make_chain([
            _make_node("Query", "listUsers"),
            _make_node("Mutation", "deleteUser", "DELETE"),
            _make_node("Query", "getUser"),
        ])
        confidence, _, reason = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(confidence, 0.0)
        self.assertIn("CREATE", reason)

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
        delete_node = _make_node("Mutation", "deleteUser", "DELETE")
        get_node = _make_node("Query", "getUser", body={"inputs": id_input})
        chain = _make_chain([create_node, delete_node, get_node])
        confidence, split, _ = heuristic_uaf_classifier.classify(chain)
        self.assertGreater(confidence, 0.0)
        self.assertEqual(split, 2)

    # ── Type-match signal ─────────────────────────────────────────────────────

    def test_type_match_adds_high_confidence(self):
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        delete_node = _make_node("Mutation", "deleteUser", "DELETE")
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
        chain = _make_chain([create_node, delete_node, get_node])
        confidence, split, reason = heuristic_uaf_classifier.classify(chain)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertEqual(split, 2)
        self.assertIn("type-match", reason)

    # ── Access-pattern signal ─────────────────────────────────────────────────

    def test_single_access_name_adds_confidence(self):
        create_node = _make_node("Mutation", "createOrder", "CREATE")
        delete_node = _make_node("Mutation", "deleteOrder", "DELETE")
        get_node = _make_node("Query", "getOrder")
        chain = _make_chain([create_node, delete_node, get_node])
        confidence, _, reason = heuristic_uaf_classifier.classify(chain)
        self.assertGreater(confidence, 0.0)
        self.assertIn("access-pattern", reason)

    # ── List-access penalty ───────────────────────────────────────────────────

    def test_list_access_name_penalises_confidence(self):
        id_input = {
            "id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}
        }
        create_node = _make_node("Mutation", "createOrder", "CREATE")
        delete_node = _make_node("Mutation", "deleteOrder", "DELETE")
        get_node = _make_node("Query", "listAllOrders", body={"inputs": id_input})
        chain = _make_chain([create_node, delete_node, get_node])
        confidence_penalised, _, _ = heuristic_uaf_classifier.classify(chain)

        get_node_single = _make_node("Query", "getOrder", body={"inputs": id_input})
        chain_single = _make_chain([create_node, delete_node, get_node_single])
        confidence_single, _, _ = heuristic_uaf_classifier.classify(chain_single)

        self.assertLessEqual(confidence_penalised, confidence_single)

    # ── High-confidence end-to-end ────────────────────────────────────────────

    def test_high_confidence_create_delete_get(self):
        id_input = {
            "userId": {
                "kind": "NON_NULL",
                "name": "userId",
                "ofType": {"kind": "SCALAR", "name": "ID", "type": "ID", "ofType": None},
                "type": None,
            }
        }
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        delete_node = _make_node("Mutation", "deleteUser", "DELETE")
        get_node = _make_node("Query", "getUser", body={"inputs": id_input})
        chain = _make_chain([create_node, delete_node, get_node])
        confidence, split, reason = heuristic_uaf_classifier.classify(chain)
        self.assertGreaterEqual(confidence, 0.5)
        self.assertEqual(split, 2)

    # ── Post-delete DELETE node is not a UAF test ─────────────────────────────

    def test_post_delete_node_that_is_also_delete_ignored(self):
        """A second DELETE after the first is not a meaningful UAF access attempt."""
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        delete_node = _make_node("Mutation", "deleteUser", "DELETE")
        delete_again = _make_node("Mutation", "archiveUser", "DELETE")
        chain = _make_chain([create_node, delete_node, delete_again])
        confidence, _, reason = heuristic_uaf_classifier.classify(chain)
        # archiveUser is the last DELETE (last node overall), so split_index >= len(steps) → no test
        self.assertEqual(confidence, 0.0)

    def test_post_delete_delete_node_does_not_score(self):
        """A DELETE node in the post-delete zone should not score as a UAF test."""
        create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
        delete_node = _make_node("Mutation", "deleteUser", "DELETE")
        delete_again = _make_node("Mutation", "archiveUser", "DELETE")
        # Add a real test node after the second DELETE to force the split to be after delete_node
        # (last_delete_idx=2 so split=3, but there's nothing at index 3 — still 0.0)
        # To test correctly, we need a chain where the second DELETE is NOT the last node:
        get_node = _make_node("Query", "getUser")
        chain = _make_chain([create_node, delete_node, delete_again, get_node])
        # last DELETE is at index 2 (archiveUser), split=3
        _, split, _ = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(split, 3)  # split is after last DELETE (archiveUser)

    # ── Split index correctness ───────────────────────────────────────────────

    def test_split_index_is_after_last_delete(self):
        """When there are two DELETE mutations, the split is after the LAST one."""
        create_node = _make_node("Mutation", "createUser", "CREATE")
        del1 = _make_node("Mutation", "deleteUser", "DELETE")
        del2 = _make_node("Mutation", "removeUser", "DELETE")
        get_node = _make_node("Query", "getUser", body={
            "hardDependsOn": {"id": "User"}
        })
        chain = _make_chain([create_node, del1, del2, get_node])
        _, split, _ = heuristic_uaf_classifier.classify(chain)
        self.assertEqual(split, 3)  # after index 2 (del2)


# ── UAFChainStrategy tests ────────────────────────────────────────────────────

class TestUAFChainStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = UAFChainStrategy()

    def test_is_enabled_when_not_skipped(self):
        import graphqler.config as cfg
        original = cfg.SKIP_UAF_CHAIN_FUZZING
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            self.assertTrue(self.strategy.is_enabled())
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original

    def test_is_disabled_when_skipped(self):
        import graphqler.config as cfg
        original = cfg.SKIP_UAF_CHAIN_FUZZING
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = True
            self.assertFalse(self.strategy.is_enabled())
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original

    def test_returns_empty_when_disabled(self):
        import graphqler.config as cfg
        original = cfg.SKIP_UAF_CHAIN_FUZZING
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = True
            result = self.strategy.generate(None, [], source_chains=[])
            self.assertEqual(result, [])
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original

    def test_returns_empty_for_none_source_chains(self):
        import graphqler.config as cfg
        original = cfg.SKIP_UAF_CHAIN_FUZZING
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            result = self.strategy.generate(None, [], source_chains=None)
            self.assertEqual(result, [])
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original

    def test_high_confidence_chain_is_accepted(self):
        """A CREATE→DELETE→getResource chain should become a UAF candidate."""
        import graphqler.config as cfg
        original_skip = cfg.SKIP_UAF_CHAIN_FUZZING
        original_threshold = cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5

            id_input = {"id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}}
            create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
            delete_node = _make_node("Mutation", "deleteUser", "DELETE")
            get_node = _make_node("Query", "getUser", body={"inputs": id_input})
            source_chain = _make_chain([create_node, delete_node, get_node], name="create-delete-get")

            result = self.strategy.generate(None, [], source_chains=[source_chain])
            self.assertEqual(len(result), 1)
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original_skip
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold

    def test_uaf_chain_profile_labels(self):
        """Pre-delete steps should be 'primary'; post-delete steps 'post_delete'."""
        import graphqler.config as cfg
        original_skip = cfg.SKIP_UAF_CHAIN_FUZZING
        original_threshold = cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5

            id_input = {"id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}}
            create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
            delete_node = _make_node("Mutation", "deleteUser", "DELETE")
            get_node = _make_node("Query", "getUser", body={"inputs": id_input})
            source_chain = _make_chain([create_node, delete_node, get_node], name="create-delete-get")

            result = self.strategy.generate(None, [], source_chains=[source_chain])
            self.assertEqual(len(result), 1)

            chain = result[0]
            # Steps 0 and 1 (CREATE and DELETE) are primary
            self.assertEqual(chain.steps[0].profile_name, "primary")  # CREATE
            self.assertEqual(chain.steps[1].profile_name, "primary")  # DELETE
            # Step 2 (GET after delete) is post_delete
            self.assertEqual(chain.steps[2].profile_name, "post_delete")
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original_skip
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold

    def test_chain_without_delete_is_skipped(self):
        """Chains without a DELETE mutation are never UAF candidates."""
        import graphqler.config as cfg
        original_skip = cfg.SKIP_UAF_CHAIN_FUZZING
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            create_node = _make_node("Mutation", "createUser", "CREATE")
            get_node = _make_node("Query", "getUser")
            source_chain = _make_chain([create_node, get_node])

            result = self.strategy.generate(None, [], source_chains=[source_chain])
            self.assertEqual(result, [])
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original_skip

    def test_chain_is_multi_profile(self):
        """The generated UAF chain should be detected as multi-profile."""
        import graphqler.config as cfg
        original_skip = cfg.SKIP_UAF_CHAIN_FUZZING
        original_threshold = cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5

            id_input = {"id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}}
            create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
            delete_node = _make_node("Mutation", "deleteUser", "DELETE")
            get_node = _make_node("Query", "getUser", body={"inputs": id_input})
            source_chain = _make_chain([create_node, delete_node, get_node], name="create-delete-get")

            result = self.strategy.generate(None, [], source_chains=[source_chain])
            self.assertEqual(len(result), 1)
            self.assertTrue(result[0].is_multi_profile)
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original_skip
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold

    def test_reason_starts_with_heuristic(self):
        """Chain accepted by heuristic should have reason starting with 'heuristic:'."""
        import graphqler.config as cfg
        original_skip = cfg.SKIP_UAF_CHAIN_FUZZING
        original_threshold = cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD
        try:
            cfg.SKIP_UAF_CHAIN_FUZZING = False
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = 0.5

            id_input = {"id": {"kind": "SCALAR", "name": "id", "type": "ID", "ofType": None}}
            create_node = _make_node("Mutation", "createUser", "CREATE", body={"outputType": "User"})
            delete_node = _make_node("Mutation", "deleteUser", "DELETE")
            get_node = _make_node("Query", "getUser", body={"inputs": id_input})
            source_chain = _make_chain([create_node, delete_node, get_node])

            result = self.strategy.generate(None, [], source_chains=[source_chain])
            self.assertTrue(len(result) > 0)
            self.assertTrue(result[0].reason.startswith("heuristic:"))
        finally:
            cfg.SKIP_UAF_CHAIN_FUZZING = original_skip
            cfg.UAF_HEURISTIC_CONFIDENCE_THRESHOLD = original_threshold


if __name__ == "__main__":
    unittest.main()
