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

    if response.status_code != 200:
        return parse_response(response.text), response

    if next:
        return next(json.loads(response.text))

    return parse_response(response.text), response


def parse_response(response_text: str) -> dict:
    """Parse the response and try to jsonify it

    Args:
        response_text (str): The response text

    Returns:
        dict: A dictionary of the response
    """
    try:
        json_text = json.loads(response_text)
        return json_text
    except Exception:
        return {"error": json_text}
