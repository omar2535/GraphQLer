from typing import Callable
import time
import requests
import constants
import json


# The last time a request was made so that we can wait between requests
last_request_time = time.time()


def send_graphql_request(url: str, payload: str, next: Callable[[dict], dict] = None) -> tuple[dict, requests.Response]:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        payload (str): The payload to hit the server with (query or mutation)
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        tuple[dict, requests.Response]: Dictionary of the graphql response, and the request's response
    """
    global last_request_time

    # Make the headers first
    headers = {"content-type": "application/json"}
    if constants.AUTHORIZATION:
        headers["Authorization"] = f"{constants.AUTHORIZATION}"

    # Make the body
    body = {"query": payload}

    # If the last request was made recently, wait for a bit
    time_since_last_request = time.time() - last_request_time
    if time_since_last_request < constants.TIME_BETWEEN_REQUESTS:
        time.sleep(constants.TIME_BETWEEN_REQUESTS - time_since_last_request)

    # Make the request and set the last request time
    response = requests.post(url=url, json=body, headers=headers, timeout=constants.REQUEST_TIMEOUT)
    last_request_time = time.time()

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
