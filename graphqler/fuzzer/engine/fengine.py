"""FEngine: Responsible for getting the materialized query, running it against the API, and returning if it succeeds
         and storing any new objects that were returned to the objects_bucket (if any were updated).
Note: The run_regular_mutation and run_regular_query functions are very similar, but they are kept separate for clarity purposes
"""

import bdb
import traceback

from graphqler import config
from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.parser_utils import get_output_type
from graphqler.utils import plugins_handler
from graphqler.utils.singleton import singleton
from graphqler.utils.stats import Stats
from graphqler.utils import request_utils as _request_utils

from .exceptions import HardDependencyNotMetException
from .materializers import Materializer, RegularPayloadMaterializer, MaximalPayloadMaterializer, dos_materializers
from .retrier import Retrier
from .types import Result, ResultEnum
from .types.profile import RuntimeProfile
from .utils import check_is_data_empty


@singleton
class FEngine(object):
    def __init__(self, api: API):
        """The intiialization of the FEngine

        Args:
            api (API): The API object
        """
        self.api = api
        self.logger = Logger().get_fuzzer_logger()

    def run_minimal_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str, check_hard_depends_on: bool = True) -> tuple[dict, Result]:
        """Runs the regular payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the query or mutation
            objects_bucket (dict): The objects bucket
            graphql_type (str): The GraphQL type (either query or mutation)
            check_hard_depends_on (bool): Whether to check the hard depends on of the query's input - if it's not met, we fail. Defaults to True

        Returns:
            tuple[Response, Result]: The response dict, and the result of the query
        """
        self.logger.info(f"Running minimal payload: {name}")
        materializer = RegularPayloadMaterializer(self.api, fail_on_hard_dependency_not_met=check_hard_depends_on)
        return self.__run_payload(name, objects_bucket, materializer, graphql_type)

    def run_minimal_payload_with_profile(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str, profile: RuntimeProfile) -> tuple[dict, "Result"]:
        """Materializes a regular payload and sends it using a specific runtime profile.

        Used for cross-user access testing (IDOR) and other multi-context scenarios.
        The payload is built from the shared ``objects_bucket``, but the HTTP request
        is sent using the specified profile (carrying its auth token and variables).

        Args:
            name (str): The name of the query or mutation.
            objects_bucket (ObjectsBucket): Object bucket from the primary-token setup run.
            graphql_type (str): "Query" or "Mutation".
            profile (RuntimeProfile): The runtime profile to use for this execution.

        Returns:
            tuple[dict, Result]: The GraphQL response dict and the result.
        """
        self.logger.info(f"Running minimal payload with profile '{profile.name}': {name}")
        materializer = RegularPayloadMaterializer(self.api, fail_on_hard_dependency_not_met=False)
        return self.__run_payload_with_profile(name, objects_bucket, materializer, graphql_type, profile)

    def run_minimal_payload_with_auth(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str, auth_override: str) -> tuple[dict, "Result"]:
        """Backward-compatible wrapper for run_minimal_payload_with_profile."""
        profile = RuntimeProfile(name="legacy_override", auth_token=auth_override)
        return self.run_minimal_payload_with_profile(name, objects_bucket, graphql_type, profile)

    def run_maximal_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str, check_hard_depends_on: bool = True) -> tuple[dict, Result]:
        """Runs the maximal payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the query or mutation
            objects_bucket (dict): The objects bucket
            graphql_type (str): The GraphQL type (either query or mutation)
            check_hard_depends_on (bool): Whether to check the hard depends on of the query's input - if it's not met, we fail. Defaults to True

        Returns:
            tuple[Response, Result]: The response dict, and the result of the query
        """
        self.logger.info(f"Running maximal payload: {name}")
        materializer = MaximalPayloadMaterializer(self.api, fail_on_hard_dependency_not_met=check_hard_depends_on)
        return self.__run_payload(name, objects_bucket, materializer, graphql_type)

    def run_dos_payloads(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str, max_depth: int = 20) -> list[tuple[dict, Result]]:
        """Runs all DOS payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the node
            objects_bucket (dict): The objects bucket
            graphql_type (str): The GraphQL type (either query or mutation)
            max_depth (int, optional): The maximum recursion depth. Defaults to 20.

        Returns:
            list[tuple[Response, Result]]: A list of results of (The response dict, and the result of the query)
        """
        results = []
        for dos_materializer in dos_materializers:
            self.logger.info(f"Running DOS materializer: {dos_materializer.__name__} on {name}")
            materializer = dos_materializer(self.api, fail_on_hard_dependency_not_met=False, max_depth=max_depth)
            results += [self.__run_payload(name, objects_bucket, materializer, graphql_type)]
        return results

    def __run_payload(self, name: str, objects_bucket: ObjectsBucket, materializer: Materializer, graphql_type: str) -> tuple[dict, Result]:
        """Runs the payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the query or mutation
            objects_bucket (ObjectsBucket): The objects bucket
            materializer (QueryMaterializer | MutationMaterializer): The materializer to use
            graphql_type (str): The GraphQL type (either query or mutation)

        Returns:
            tuple[Response, Result]: The GraphQL response dict, and the result of the query
        """
        if graphql_type == "Query":
            return self.__run_query(name, objects_bucket, materializer)
        elif graphql_type == "Mutation":
            return self.__run_mutation(name, objects_bucket, materializer)
        else:
            self.logger.warning(f"Unknown GraphQL type: {graphql_type} for {name}")
            return ({}, Result(ResultEnum.INTERNAL_FAILURE))

    def __run_payload_with_profile(self, name: str, objects_bucket: ObjectsBucket, materializer: Materializer, graphql_type: str, profile: RuntimeProfile) -> tuple[dict, Result]:
        """Materialize a payload and send it with an explicit runtime profile.

        Used for cross-user access testing — the payload is built normally (using the
        shared ObjectsBucket) but the HTTP request is signed with the profile's token.
        The ObjectsBucket is intentionally *not* updated here to avoid polluting the
        primary-user state.

        Args:
            name (str): The name of the query or mutation.
            objects_bucket (ObjectsBucket): Bucket populated by the primary-user setup run.
            materializer (Materializer): Materializer to use for payload generation.
            graphql_type (str): "Query" or "Mutation".
            profile (RuntimeProfile): The runtime profile to use.

        Returns:
            tuple[dict, Result]: The GraphQL response dict and the result.
        """
        if graphql_type == "Object":
            return ({}, Result(ResultEnum.GENERAL_SUCCESS))

        result = Result()
        try:
            payload_string, _ = materializer.get_payload(name, objects_bucket, graphql_type)
            result.payload = payload_string
            self.logger.info(f"[{profile.name}/{name}] Sending payload with profile '{profile.name}':\n {payload_string}")
            
            # Use profile headers
            headers = profile.get_headers()
            auth_token = headers.get("Authorization", "")
            
            graphql_response, request_response = _request_utils.send_graphql_request_with_auth(self.api.url, payload_string, auth_token)
            result.status_code = request_response.status_code
            result.graphql_response = graphql_response
            result.raw_response_text = request_response.text
            if not graphql_response or result.has_errors:
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            if not result.has_data or result.data.get(name) is None:
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            result.result_enum = ResultEnum.HAS_DATA_SUCCESS
            return (graphql_response, result)
        except HardDependencyNotMetException as e:
            self.logger.info(f"[{profile.name}/{name}] Hard dependency not met: {e}")
            result.result_enum = ResultEnum.INTERNAL_FAILURE
            return ({}, result)
        except Exception as e:
            self.logger.info(f"[{profile.name}/{name}] Exception: {e}")
            self.logger.debug(traceback.format_exc())
            result.result_enum = ResultEnum.INTERNAL_FAILURE
            return ({}, result)


    def __run_mutation(self, endpoint_name: str, objects_bucket: ObjectsBucket, materializer: Materializer) -> tuple[dict, Result]:
        """Runs the mutation, and returns a new objects bucket. Performs a few things:
           1. Materializes the mutation with its parameters (resolving any dependencies from the object_bucket)
           2. Send the mutation against the server and gets the parses the object from the response
           3. Process the result in the objects_bucket if it's an object with an ID
              - if we have a delete operation, remove it from the bucket
              - if we have a create operation, add it to the bucket
              - if we have an update operation, update it in the bucket
              - if we have an unknown, don't do anything

        Args:
            endpoint_name(str): Name of the mutation
            objects_bucket (dict): The current objects bucket

        Returns:
            tuple[dict, Result]: The graphql response dict, and the result of the mutation,
        """
        result = Result()
        try:
            # Step 1
            self.logger.info(f"[{endpoint_name}] Running mutation: {endpoint_name}")
            self.logger.debug(f"[{endpoint_name}] Objects bucket: {objects_bucket}")
            payload_string, used_objects = materializer.get_payload(endpoint_name, objects_bucket, "Mutation")
            result.payload = payload_string

            # Step 2: Send the request & handle response
            self.logger.info(f"[{endpoint_name}] Sending mutation payload string:\n {payload_string}")
            request_utils = plugins_handler.get_request_utils()
            graphql_response, request_response = request_utils.send_graphql_request(self.api.url, payload_string)
            status_code = request_response.status_code

            # Stats tracking stuff, results
            self.logger.info(f"Request Response code: {status_code}")
            Stats().add_http_status_code(endpoint_name, status_code)
            result.status_code = status_code
            result.graphql_response = graphql_response
            result.raw_response_text = request_response.text

            # For the GraphQL reponse
            if not graphql_response:
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            if result.has_errors:
                self.logger.info(f"[{endpoint_name}] Mutation failed: {graphql_response['errors'][0]}")
                self.logger.info(f"[{endpoint_name}] Retrying ---")
                graphql_response, retry_success = Retrier(self.logger).retry(self.api.url, payload_string, graphql_response, 0)
                if not retry_success:
                    result.result_enum = ResultEnum.EXTERNAL_FAILURE
                    return (graphql_response, result)
            if not result.has_data:
                self.logger.error(f"[{endpoint_name}] No data in response: {graphql_response}")
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            if result.data[endpoint_name] is None or check_is_data_empty(result.data):
                # Special case, this could indicate a failure or could also not, based on how GraphQLer is configured
                self.logger.info(f"[{endpoint_name}] Mutation returned no data: {graphql_response} -- returning early")
                if config.NO_DATA_COUNT_AS_SUCCESS:
                    result.result_enum = ResultEnum.NO_DATA_SUCCESS
                    return (graphql_response, result)
                else:
                    result.result_enum = ResultEnum.EXTERNAL_FAILURE
                    return (graphql_response, result)

            # Step 3
            self.logger.info(f"Response: {graphql_response}")

            # Process the response into the objects bucket
            if type(result.data[endpoint_name]) is dict:
                mutation_output_type = get_output_type(endpoint_name, self.api.mutations)
                mutation_type = self.api.mutations[endpoint_name]["mutationType"]
                if mutation_type == "CREATE":
                    objects_bucket.put_in_bucket(result.data)
                elif mutation_type == "UPDATE":
                    objects_bucket.update_object_in_bucket(result.data)
                elif mutation_type == "DELETE" and config.ALLOW_DELETION_OF_OBJECTS:
                    if mutation_output_type in used_objects:
                        used_object_value = used_objects[mutation_output_type]
                        objects_bucket.delete_object_from_bucket(mutation_output_type, used_object_value)
                else:
                    pass  # UNKNOWN mutation type — nothing to do
            else:
                # For non-dict responses (scalars, lists), still capture any data into the bucket
                objects_bucket.put_in_bucket(result.data)

            result.result_enum = ResultEnum.GENERAL_SUCCESS
            return (graphql_response, result)
        except HardDependencyNotMetException as e:
            self.logger.info(f"[{endpoint_name}] Hard dependency not met: {e}")
            result.result_enum = ResultEnum.INTERNAL_FAILURE
            return ({}, result)
        except bdb.BdbQuit as exc:
            raise exc
        except Exception as e:
            # print(f"Exception when running: {mutation_name}: {e}, {traceback.print_exc()}")
            self.logger.info(f"[{endpoint_name}] Exception when running: {endpoint_name}")
            self.logger.info(f"[{endpoint_name}] {e}")
            self.logger.debug(f"[{endpoint_name}] {traceback.format_exc()}")
            result.result_enum = ResultEnum.INTERNAL_FAILURE
            return ({}, result)

    def __run_query(self, endpoint_name: str, objects_bucket: ObjectsBucket, materializer: Materializer) -> tuple[dict, Result]:
        """Runs the query, and returns a new objects bucket

        Args:
            endpoint_name (str): The name of the query
            objects_bucket (ObjectsBucket): The objects bucket
            materializer (QueryMaterializer): The materializer to use

        Returns:
            tuple[dict, Result]: The graphql response as a dict, and the result of the query
        """
        result = Result()
        try:
            # Step 1
            self.logger.info(f"[{endpoint_name}] Running query: {endpoint_name}")
            self.logger.debug(f"[{endpoint_name}] Objects bucket: {objects_bucket}")
            payload_string, used_objects = materializer.get_payload(endpoint_name, objects_bucket, "Query")
            result.payload = payload_string

            # Step 2
            self.logger.info(f"[{endpoint_name}] Sending query payload string:\n {payload_string}")
            request_utils = plugins_handler.get_request_utils()
            graphql_response, request_response = request_utils.send_graphql_request(self.api.url, payload_string)
            status_code = request_response.status_code

            # Stats tracking stuff
            self.logger.info(f"Request Response code: {status_code}")
            Stats().add_http_status_code(endpoint_name, status_code)
            result.status_code = status_code
            result.graphql_response = graphql_response
            result.raw_response_text = request_response.text

            # For the GraphQL reponse
            if not graphql_response:
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            if result.has_errors:
                self.logger.info(f"[{endpoint_name}] Query failed: {graphql_response['errors'][0]}")
                self.logger.info(f"[{endpoint_name}] Retrying ---")
                graphql_response, retry_success = Retrier(self.logger).retry(self.api.url, payload_string, graphql_response, 0)
                if not retry_success:
                    result.result_enum = ResultEnum.EXTERNAL_FAILURE
                    return (graphql_response, result)
            if not result.has_data:
                self.logger.error(f"[{endpoint_name}] No data in response: {graphql_response}")
                result.result_enum = ResultEnum.EXTERNAL_FAILURE
                return (graphql_response, result)
            if endpoint_name not in result.data or result.data[endpoint_name] is None or check_is_data_empty(result.data):
                # Special case, this could indicate a failure or could also not, based on how GraphQLer is configured
                self.logger.info(f"[{endpoint_name}] Query returned no data: {graphql_response} -- returning early")
                if config.NO_DATA_COUNT_AS_SUCCESS:
                    result.result_enum = ResultEnum.NO_DATA_SUCCESS
                    return (graphql_response, result)
                else:
                    result.result_enum = ResultEnum.EXTERNAL_FAILURE
                    return (graphql_response, result)

            # Step 3
            self.logger.info(f"Response: {graphql_response}")
            if type(graphql_response["data"][endpoint_name]) is dict:
                objects_bucket.put_in_bucket(graphql_response["data"])

            result.result_enum = ResultEnum.GENERAL_SUCCESS
            return (graphql_response, result)
        except bdb.BdbQuit as exc:
            raise exc
        except Exception as e:
            self.logger.info(f"[{endpoint_name}]Exception when running: {endpoint_name}: {e}, {traceback.format_exc()}")
            result.result_enum = ResultEnum.INTERNAL_FAILURE
            return ({}, result)
