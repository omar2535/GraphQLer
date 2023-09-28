from typing import Callable

import requests
import constants
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


def write_json_to_file(contents: dict, output_file: str):
    """Write JSON to a file

    Args:
        contents (dict): Contents of the JSON
        output_file (str): Output file path
    """
    with open(output_file, "w") as file_handle:
        json.dump(contents, file_handle, indent=4)
