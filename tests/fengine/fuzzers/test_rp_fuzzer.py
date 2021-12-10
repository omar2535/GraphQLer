from fengine.fuzzers.replace_params_fuzzer import ReplaceParamsFuzzer
from graphqler_types.graphql_request import GraphqlRequest
import re


def test_fuzzer():
    datatypes = {
        "Todo": {"params": {"id": {"type": "ID"}, "title": {"type": "String"}, "completed": {"type": "Boolean"}}}
    }

    test_request_1 = GraphqlRequest(
        graphqlQueryType="mutation",
        name="createTodo",
        body=None,
        params=[{"name": "title", "type": "String"}, {"name": "completed", "type": "Boolean"}],
        res=[{"name": "todo", "type": "Todo"}],
    )

    # test_request_2 = GraphqlRequest(
    #     graphqlQueryType="query",
    #     name="Todo",
    #     body=None,
    #     params=[{"name": "id", "type": "ID"}],
    #     res=[{"name": "todo", "type": "Todo"}],
    # )

    # test_request_3 = GraphqlRequest(
    #     graphqlQueryType="mutation",
    #     name="updateTodo",
    #     body=None,
    #     params=[{"name": "id", "type": "ID"}],
    #     res=[{"name": "todo", "type": "Todo"}],
    # )

    rp_fuzzer = ReplaceParamsFuzzer(test_request_1, datatypes=datatypes)
    queries = rp_fuzzer.create_fuzzed_queries()
    sample_queries = [
        'mutation{ createTodo(title: "some_string", completed: false){ id, title, completed } }',
        'mutation{ createTodo(title: "some_string", completed: true){ id, title, completed } }',
        'mutation{ createTodo(title: "", completed: false){ id, title, completed } }',
        'mutation{ createTodo(title: "", completed: true){ id, title, completed } }',
    ]
    assert 4 == len(queries)
    for q in queries:
        query_string = re.sub("\\s+", " ", q)
        assert query_string in sample_queries
