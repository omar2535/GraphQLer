from graphqler_types.graphql_data_type import GraphqlDataType
from graphqler_types.graphql_request import GraphqlRequest
import requests
import json

spaceID = "mt0pmhki5db7"
accessToken = "8c7dbd270cb98e83f9d8d57fb8a2ab7bac9d7501905fb013c69995ebf1b2a719"

# endpoint = f"https://graphql.contentful.com/content/v1/spaces/{spaceID}"
headers = {"Authorization": f"Bearer {accessToken}"}
endpoint = "http://localhost:3000"


def dataToString(data):
    if type(data) == bool:
        if data:
            return "true"
        else:
            return "false"
    return str(data)


def generate_query(request: GraphqlRequest):
    # for param in request.params:
    para_body = ""
    for param in request.params:
        if request.params[param] is None:
            para_body += (str(param)) + ","
            print(para_body)
        else:
            para_body += (str(param)) + "=" + str(dataToString(request.params[param]))

    string = f"""{request.type} {{
      {request.name} {{
          {para_body}
      }}
    }}"""
    return string


request_test = GraphqlRequest("query", "allTodos", "", [], res={"id": None, "title": None, "completed": None})

# Todo = GraphqlDataType("Todo",
# [{GraphqlDataType(("ID"), {"type": "ID", "required": True}): None},
# {GraphqlDataType(("title"), {"type": "String", "required": True}): None},
# {GraphqlDataType(("completed"), {"type": "Boolean", "required": True}): None}]
# )
# Liss = GraphqlDataType(
# name = "Todo",
# params = {
#   "id": string,
#   "title": string,
#   "completed": boolean
# })


# Todo = GraphqlDataType(
# name = "Todo",
# params = {
#   "id": ,
#   "title": Liss,
#   "completed": bool
# })

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
