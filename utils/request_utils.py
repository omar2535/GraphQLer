from typing import Callable
import requests
import constants
import json


def send_graphql_request(url: str, payload: str, next: Callable[[dict], dict] = None) -> tuple[dict, requests.Response]:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        payload (str): The payload to hit the server with (query or mutation)
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        tuple[dict, requests.Response]: Dictionary of the graphql response, and the request's response
    """
    # Make the headers first
    headers = {"content-type": "application/json"}
    if constants.AUTHORIZATION:
        headers["Authorization"] = f"{constants.AUTHORIZATION}"

    # Make the body
    body = {"query": payload}

    response = requests.post(url=url, json=body, headers=headers)

    if next:
        return next(json.loads(response.text))

    return json.loads(response.text), response
