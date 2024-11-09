"""Retrier
This moule will retry any immediate errors that arise during the query. This is not responsible for running the same query / mutation again,
rather, it's responsible for modifying the query / mutation to make it work. Scenarios:
- We have a NON-NULL column that is selected for in the output, but the server is responding with NULL, you will get the following error:
  {'message': 'Cannot return null for non-nullable field Transaction.payer.'}.
  In this scenario, we will need to remove the payer key from the mutation / query output fields
"""

from graphqler.fuzzer.engine.retrier.utils import find_block_end, remove_lines_within_range
from graphqler.utils import plugins_handler
import logging


class Retrier:
    def __init__(self, logger: logging.Logger):
        self.logger = logger.getChild(__name__)
        self.max_retries = 3

    def retry(self, url: str, payload: str | dict | list, gql_response: dict, retry_count) -> tuple[dict, bool]:
        """Retries the payload based on the error

        Args:
            url (str): The url of the endpoint
            payload (str): The payload (either a query or mutation)
            gql_response (dict): The GraphQL response containing the error
            retry_count (int): The number of times we've retried

        Returns:
            tuple[dict, bool]: The response, and whether the retry succeeded or not
        """
        error = gql_response["errors"][0]

        if isinstance(payload, dict) or isinstance(payload, list):
            return (gql_response, False)

        # If the error doesn't have a message, we can't do anything to fix it
        if "message" not in error:
            return (gql_response, False)

        if "Cannot return null for non-nullable field" in error["message"] or "Field must have selections" in error["message"]:
            if "locations" not in error:
                return (gql_response, False)
            locations = error["locations"]
            for location in locations:
                payload = self.get_new_payload_for_retry_non_null(payload, location)
            self.logger.debug(f"Retrying with new payload:\n {payload}")
            gql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(url, payload)
            self.logger.info(f"Response: {gql_response}")
            if "errors" in gql_response:
                if retry_count < self.max_retries:
                    return self.retry(url, payload, gql_response, retry_count + 1)
                else:
                    return (gql_response, False)
            else:
                return (gql_response, True)
        else:
            return (gql_response, False)

    def get_new_payload_for_retry_non_null(self, payload: str, location: dict) -> str:
        """Gets a new payload from the original payload, and the location of the error

        Args:
            payload (str): The payload
            error (dict): The error

        Returns:
            str: A string of the new payload
        """
        line_number = location["line"]
        block_end = find_block_end(payload, line_number - 1)
        new_payload = remove_lines_within_range(payload, line_number - 1, block_end)
        return new_payload
