from typing import Callable

import time
import requests
import json


# The last time a request was made so that we can wait between requests
last_request_time = time.time()
session = None


def get_headers() -> dict:
    """Mocked get_headers function

    Returns:
        dict: A mocked dictionary of headers
    """
    mocked_headers = {
        "Content-Type": "application/json",
        "Mocked-Header": "MockedValue"
    }
    return mocked_headers


def send_graphql_request(url: str, payload: str | dict | list, next: Callable[[dict], dict] | None = None) -> tuple[dict, requests.Response]:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        payload (str | dict | list): The payload to send to the GraphQL API. If dict or string, must provide the query and variables keys
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        tuple[dict, requests.Response]: Dictionary of the graphql response, and the request's response
    """
    # Mocked response to always return a success response
    mocked_response = {
        "data": {
            "message": "Success"
        }
    }
    mocked_response_object = requests.Response()
    mocked_response_object.status_code = 200
    mocked_response_object._content = json.dumps(mocked_response).encode('utf-8')
    mocked_response_object.url = url
    return mocked_response, mocked_response_object


def parse_response(response_text: str) -> dict:
    """Mocked parse_response function

    Args:
        response_text (str): The response text

    Returns:
        dict: A mocked dictionary of the response
    """
    return {"mocked": "response"}


def get_or_create_session() -> requests.Session:
    """Mocked get_or_create_session function

    Returns:
        requests.Session: A mocked session
    """
    mocked_session = requests.Session()
    mocked_session.headers.update({"Mocked-Header": "MockedValue"})
    return mocked_session


def create_new_session() -> requests.Session:
    """Mocked create_new_session function

    Returns:
        requests.Session: A mocked session
    """
    mocked_session = requests.Session()
    mocked_session.headers.update({"Mocked-Header": "MockedValue"})
    return mocked_session
