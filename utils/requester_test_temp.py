from types.graphql_data_type import GraphqlDataType
from types.graphql_request import GraphqlRequest
import requests
import json

spaceID = "mt0pmhki5db7"
accessToken = "8c7dbd270cb98e83f9d8d57fb8a2ab7bac9d7501905fb013c69995ebf1b2a719"

# endpoint = f"https://graphql.contentful.com/content/v1/spaces/{spaceID}"
headers = {"Authorization": f"Bearer {accessToken}"}
endpoint = "http://localhost:3000"


def generate_query(request: GraphqlRequest):
    # for param in request.params:
    string = f"""{request.type} {{\n {request.name}{{}}}}"""
    return string


request_test = GraphqlRequest("query", "allTodos", "", [], {"id": "", "title": "", "completed": False})
print(generate_query(request_test))
query = """query {
  allTodos {
    id,
    title,
    completed,
  }
}
"""
print(query)

r = requests.post(endpoint, json={"query": query}, headers=headers)
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2))
else:
    raise Exception(f"Query failed to run with a {r.status_code}.")
