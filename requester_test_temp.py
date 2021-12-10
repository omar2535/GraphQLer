from graphqler_types.graphql_data_type import GraphqlDataType
from graphqler_types.graphql_request import GraphqlRequest
from utils.requester import Requester
import requests
import json
import re

datatypes = {"Todo": {"params": {"id": {"type": "ID"}, "title": {"type": "String"}, "completed": {"type": "Boolean"}}}}

test_request_1 = GraphqlRequest(
    graphqlQueryType="mutation",
    name="createTodo",
    body=None,
    params=[{"name": "title", "type": "String"}, {"name": "completed", "type": "Boolean"}],
    res=[{"name": "todo", "type": "Todo"}],
)

test_request_2 = GraphqlRequest(
    graphqlQueryType="query",
    name="Todo",
    body=None,
    params=[{"name": "id", "type": "ID"}],
    res=[{"name": "todo", "type": "Todo"}],
)

endpoint = "http://localhost:3000"

valid = Requester([test_request_2], "http://localhost:3000", datatypes).render()[0]

for seq in valid:
    print(seq[0].body)
    query_string = re.sub("\\s+", " ", seq[0].body)
    print(query_string)
