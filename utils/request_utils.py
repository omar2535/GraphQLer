from typing import Callable
import requests
import json


def send_graphql_request(url: str, query: str, next: Callable[[dict], dict] = None) -> dict:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        query (str): Query string to hit the server with
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        dict: _description_
    """
    body = {"query": query}

    x = requests.post(url=url, json=body)

    if next:
        return next(json.loads(x.text))

    return json.loads(x.text)
