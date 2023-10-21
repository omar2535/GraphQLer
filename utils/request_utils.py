from typing import Callable
import requests
import json


def send_graphql_request(url: str, payload: str, next: Callable[[dict], dict] = None) -> dict:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        payload (str): The payload to hit the server with (query or mutation)
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        dict: Dictionary of the response
    """
    body = {"query": payload}

    x = requests.post(url=url, json=body)

    if next:
        return next(json.loads(x.text))

    return json.loads(x.text)
