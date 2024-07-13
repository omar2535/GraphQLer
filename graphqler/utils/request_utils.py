from typing import Callable
from graphqler import constants

import pprint
import time
import requests
import json


# The last time a request was made so that we can wait between requests
last_request_time = time.time()
session = None


def get_headers() -> dict:
    """Get the headers for the request

    Returns:
        dict: The headers for the request
    """
    headers = {"Content-Type": "application/json"}
    if constants.AUTHORIZATION:
        headers["Authorization"] = f"{constants.AUTHORIZATION}"

    if constants.CUSTOM_HEADERS:
        headers.update(constants.CUSTOM_HEADERS)
    return headers


def get_proxies() -> dict:
    """Get the proxies for the request

    Returns:
        dict: The proxies for the request
    """
    if constants.PROXY and 'http:' in constants.PROXY:
        return {"http": constants.PROXY}
    elif constants.PROXY and 'https:' in constants.PROXY:
        return {"https": constants.PROXY}
    elif constants.PROXY:
        return {"http": constants.PROXY, "https": constants.PROXY}
    else:
        return {}


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

    # Make the body
    body = {"query": payload}

    # If the last request was made recently, wait for a bit
    time_since_last_request = time.time() - last_request_time
    if time_since_last_request < constants.TIME_BETWEEN_REQUESTS:
        time.sleep(constants.TIME_BETWEEN_REQUESTS - time_since_last_request)

    # Make the request and set the last request time
    session = get_or_create_session()
    response = session.post(
        url=url,
        json=body,
        timeout=constants.REQUEST_TIMEOUT,
    )
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
    json_text = ""
    try:
        json_text = json.loads(response_text)
        return json_text
    except Exception:
        return {"errors": json_text}


def get_or_create_session() -> requests.Session:
    """Gets an existing session or creates a new one

    Returns:
        requests.Session: The session
    """
    global session

    if session and type(session) is requests.Session:
        return session
    else:
        session = create_new_session()
        return session


def create_new_session() -> requests.Session:
    """Create a new session

    Returns:
        requests.Session: The session
    """
    session = requests.Session()
    session.headers.update(get_headers())

    # Set proxy if available
    if constants.PROXY:
        session.proxies.update(get_proxies())
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        session.verify = False
    return session
