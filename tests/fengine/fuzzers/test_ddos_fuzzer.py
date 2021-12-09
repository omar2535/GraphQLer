from fengine.fuzzers.ddos_fuzzer import DDOSFuzzer
from graphqler_types.graphql_request import GraphqlRequest
import re


def test_fuzzer():
    test_request = GraphqlRequest(
        graphqlQueryType="mutation",
        name="createTodo",
        body=None,
        params=[{"name": "title", "type": "String"}, {"name": "completed", "type": "Boolean"}],
        res=[{"name": "todo", "type": "Todo"}],
    )
    datatypes = {
        "Todo": {"params": {"id": {"type": "ID"}, "title": {"type": "String"}, "completed": {"type": "Boolean"}}}
    }
    ddos_fuzzer = DDOSFuzzer(test_request, datatypes=datatypes)
    queries = ddos_fuzzer.create_fuzzed_queries(1)
    query_string = re.sub("\\s+", " ", queries[0])

    assert 1 == len(queries)
    assert (
        query_string == 'mutation { zero:createTodo(title: "some_string", completed: false){ id, title, completed } }'
    )
