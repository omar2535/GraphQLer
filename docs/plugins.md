# Plugins

To use plugins in GraphQLer, you can use the `--plugins-path` flag. A general use case would be to do token refreshing, for example
on the [Saleor](https://docs.saleor.io/api-reference/) API. In this case, the authentication token expires very quickly, requiring the a custom refresh token -> access token checker on each request. We can override the requests sent like so:

```py
# my-output-dir/request_utils.py
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from typing import Callable
from graphqler import config

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
    if config.CUSTOM_HEADERS:
        headers.update(config.CUSTOM_HEADERS)

    if config.AUTHORIZATION:
        headers["Authorization"] = f"{config.AUTHORIZATION}"

    return headers


def send_graphql_request(url: str, payload: str | dict | list, next: Callable[[dict], dict] | None = None) -> tuple[dict, requests.Response]:
    """Send GraphQL request to the specified endpoint

    Args:
        url (str): URL of the graphql server
        payload (str | dict | list): The payload to send to the GraphQL API. If dict or string, must provide the query and variables keys
        next (Callable[[dict], dict], optional): Callback function in case there is action to be done after. Defaults to None.

    Returns:
        tuple[dict, requests.Response]: Dictionary of the graphql response, and the request's response
    """
    global last_request_time

    # Make the body (if it's a string, add the key, if it's dict or list, assume the creator of the request knows what they are doing
    # (ie. added the query / variable keys themselves))
    if isinstance(payload, str):
        body = {"query": payload}
    else:
        body = payload

    # If the last request was made recently, wait for a bit
    time_since_last_request = time.time() - last_request_time
    if time_since_last_request < config.TIME_BETWEEN_REQUESTS:
        time.sleep(config.TIME_BETWEEN_REQUESTS - time_since_last_request)

    # Make the request and set the last request time
    session = get_or_create_session()
    response = session.post(
        url=url,
        json=body,
        timeout=config.REQUEST_TIMEOUT,
    )
    last_request_time = time.time()

    if response.status_code != 200:
        return parse_response(response.text), response

    parsed_response = parse_response(response.text)
    if 'errors' in parsed_response and 'Signature has expired' in parsed_response['errors'][0]['message']:
        print("(!) Signature has expired, getting a new token")
        refresh_token_payload = {
            "query": """
            mutation {
              tokenRefresh(refreshToken: "%s") {
                token
              }
            }
            """ % config.CUSTOM_HEADERS['Cookie'].split('=')[-1]
        }

        refresh_response = session.post(
            url=url,
            json=refresh_token_payload,
            timeout=config.REQUEST_TIMEOUT,
        )

        if refresh_response.status_code == 200:
            new_token = parse_response(refresh_response.text)['data']['tokenRefresh']['token']
            config.AUTHORIZATION = f"Bearer {new_token}"
            session.headers.update(get_headers())
            response = session.post(
                url=url,
                json=body,
                timeout=config.REQUEST_TIMEOUT,
            )

    # if next:
    #     return next(json.loads(response.text))

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
        return {"errors": [response_text]}


def get_or_create_session() -> requests.Session:
    """Gets an existing session or creates a new one

    Returns:
        requests.Session: The session
    """
    global session

    if session and isinstance(session, requests.Session):
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
    if config.PROXY:
        session.proxies.update(get_proxies())
        disable_warnings(InsecureRequestWarning)
        session.verify = False
    return session

```
