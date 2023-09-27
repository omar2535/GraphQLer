import requests
import json


def send_graphql_request(url, query, next=None):
    body = {"query": query}

    x = requests.post(url=url, json=body)

    if next:
        return next(json.loads(x.text))

    return json.loads(x.text)
