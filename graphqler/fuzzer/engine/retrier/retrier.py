"""Retrier
This moule will retry any immediate errors that arise during the query. This is not responsible for running the same query / mutation again,
rather, it's responsible for modifying the query / mutation to make it work. Scenarios:
- We have a NON-NULL column that is selected for in the output, but the server is responding with NULL, you will get the following error:
  {'message': 'Cannot return null for non-nullable field Transaction.payer.'}.
  In this scenario, we will need to remove the payer key from the mutation / query output fields
- When USE_LLM is enabled, any error not handled by the heuristic strategies above is forwarded to the LLM,
  which rewrites the payload to address the server's error message.
"""

from graphqler import config
from graphqler.fuzzer.engine.retrier.utils import find_block_end, remove_lines_within_range
from graphqler.utils import plugins_handler
import logging


_LLM_FIX_SYSTEM_PROMPT = """\
You are a GraphQL API fuzzer assistant. You will be given a GraphQL query or \
mutation that was rejected by the server, along with the error message(s) \
returned.  Your job is to produce a minimally-modified version of the payload \
that fixes the reported error(s).

Respond with ONLY a JSON object in the following format:
{"payload": "<fixed GraphQL query or mutation string>"}

Rules:
- Fix ONLY what the error message(s) indicate — do not restructure the query \
  beyond what is necessary.
- The fixed payload MUST be syntactically valid GraphQL.
- If the error is "maximum query complexity exceeded", reduce the selection set \
  by removing nested or non-essential fields until the query is simpler.
- If the error is "FieldUndefined", remove the offending field entirely.
- If the error is "SubselectionRequired", add a minimal subselection block \
  (e.g. { id }) for the indicated field.
- If the error is "ValidationError" of another kind, apply the smallest \
  change that satisfies the reported constraint.
- Do NOT include markdown fences or any text outside the JSON object.\
"""


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
            if config.USE_LLM and retry_count < self.max_retries:
                return self._retry_with_llm(url, payload, gql_response, retry_count)
            return (gql_response, False)

    def _retry_with_llm(self, url: str, payload: str, gql_response: dict, retry_count: int) -> tuple[dict, bool]:
        """Uses the LLM to rewrite a failing payload based on the server's error message(s).

        Args:
            url (str): The endpoint URL.
            payload (str): The GraphQL payload that failed.
            gql_response (dict): The GraphQL response containing the errors.
            retry_count (int): Current retry depth (used to cap recursion).

        Returns:
            tuple[dict, bool]: The (possibly updated) response and whether the retry succeeded.
        """
        from graphqler.utils.llm_utils import call_llm

        errors = gql_response.get("errors", [])
        error_summary = "\n".join(f"- {e.get('message', str(e))}" for e in errors)

        user_prompt = (
            f"The following GraphQL payload was rejected by the server:\n\n"
            f"```graphql\n{payload}\n```\n\n"
            f"Server error(s):\n{error_summary}\n\n"
            f"Return a fixed version of the payload that resolves the error(s)."
        )

        try:
            response = call_llm(_LLM_FIX_SYSTEM_PROMPT, user_prompt)
            fixed_payload = response.get("payload", "").strip()
            if not fixed_payload:
                self.logger.debug("LLM retry returned an empty payload — giving up.")
                return (gql_response, False)

            self.logger.debug(f"LLM-fixed payload (attempt {retry_count + 1}):\n{fixed_payload}")
            gql_response, _ = plugins_handler.get_request_utils().send_graphql_request(url, fixed_payload)
            if "errors" not in gql_response:
                return (gql_response, True)
            if retry_count + 1 < self.max_retries:
                return self.retry(url, fixed_payload, gql_response, retry_count + 1)
            return (gql_response, False)
        except Exception as e:
            self.logger.debug(f"LLM retry raised an exception: {e}")
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
