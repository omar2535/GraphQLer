"""FEngine: Responsible for getting the materialized query, running it against the API, and returning if it succeeds
            and storing any new objects that were returned to the objects_bucket (if any were updated).
   Note: The run_regular_mutation and run_regular_query functions are very similar, but they are kept separate for clarity purposes
"""

import bdb
import re
import traceback
from pathlib import Path
from requests import Response

from graphqler import constants
from graphqler.fuzzer.utils import put_in_object_bucket, remove_from_object_bucket
from graphqler.utils.logging_utils import Logger
from graphqler.utils.parser_utils import get_output_type
from graphqler.utils.request_utils import send_graphql_request
from graphqler.utils.singleton import singleton
from graphqler.utils.stats import Stats

from .exceptions import HardDependencyNotMetException
from .materializers import Materializer
from .materializers import RegularPayloadMaterializer, DOSPayloadMaterializer
from .retrier import Retrier
from .utils import check_is_data_empty
from .types import Result


@singleton
class FEngine(object):
    def __init__(self, queries: dict, objects: dict, mutations: dict, input_objects: dict, enums: dict, url: str, save_path: str):
        """The intiialization of the FEnginer

        Args:
            queries (dict): The possible queries
            objects (dict): The possible objects
            mutations (dict): The possible mutations
            input_objects (dict): The possible input_objects
            enums (dict): The possible enums
            url (str): The string of the URL
            save_path (str): The path the user is currently working with
        """
        self.queries = queries
        self.objects = objects
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums
        self.url = url
        self.logger = Logger().get_fuzzer_logger()

    def run_regular_payload(self, name: str, objects_bucket: dict, graphql_type: str, check_hard_depends_on: bool = True) -> tuple[dict, Response, Result]:
        """Runs the regular payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the query or mutation
            objects_bucket (dict): The objects bucket
            graphql_type (str): The GraphQL type (either query or mutation)
            check_hard_depends_on (bool): Whether to check the hard depends on of the query's input - if it's not met, we fail. Defaults to True

        Returns:
            tuple[dict, Response, Result]: The new objects bucket, the response object, and the result of the query
        """
        materializer = RegularPayloadMaterializer(
            self.objects,
            self.queries,
            self.mutations,
            self.input_objects,
            self.enums,
            fail_on_hard_dependency_not_met=check_hard_depends_on
        )
        return self.__run_payload(name, objects_bucket, materializer, graphql_type)

    def run_dos_payload(self, name: str, objects_bucket: dict, graphql_type: str, max_depth: int = 20) -> tuple[dict, Response, Result]:
        """Runs the DOS payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the node
            objects_bucket (dict): The objects bucket
            graphql_type (str): The GraphQL type (either query or mutation)
            max_depth (int, optional): The maximum recursion depth. Defaults to 20.

        Returns:
            tuple[dict, Response, Result]: The new objects bucket, the response object, and the result of the query
        """
        materializer = DOSPayloadMaterializer(
            self.objects,
            self.queries,
            self.mutations,
            self.input_objects,
            self.enums,
            fail_on_hard_dependency_not_met=False,
            max_depth=max_depth
        )
        return self.__run_payload(name, objects_bucket, materializer, graphql_type)

    def __run_payload(self, name: str, objects_bucket: dict, materializer: Materializer, graphql_type: str) -> tuple[dict, Response, Result]:
        """Runs the payload (either Query or Mutation), and returns a new objects bucket

        Args:
            name (str): The name of the query or mutation
            objects_bucket (dict): The objects bucket
            materializer (QueryMaterializer | MutationMaterializer): The materializer to use
            graphql_type (str): The GraphQL type (either query or mutation)

        Returns:
            tuple[dict, Response, Result]: The new objects bucket, the response object, and the result of the query
        """
        if graphql_type == "Query":
            return self.__run_query(name, objects_bucket, materializer)
        elif graphql_type == "Mutation":
            return self.__run_mutation(name, objects_bucket, materializer)
        else:
            self.logger.warning(f"Unknown GraphQL type: {graphql_type} for {name}")
            return (objects_bucket, None, Result.INTERNAL_FAILURE)

    def __run_mutation(self, mutation_name: str, objects_bucket: dict, materializer: Materializer) -> tuple[dict, Response, Result]:
        """Runs the mutation, and returns a new objects bucket. Performs a few things:
           1. Materializes the mutation with its parameters (resolving any dependencies from the object_bucket)
           2. Send the mutation against the server and gets the parses the object from the response
           3. Process the result in the objects_bucket if it's an object with an ID
              - if we have a delete operation, remove it from the bucket
              - if we have a create operation, add it to the bucket
              - if we have an update operation, update it in the bucket
              - if we have an unknown, don't do anything

        Args:
            mutation_name (str): Name of the mutation
            objects_bucket (dict): The current objects bucket

        Returns:
            tuple[dict, Response, Result]: The new objects bucket, the response object, and the result of the mutation,
        """
        try:
            # Step 1
            self.logger.info(f"[{mutation_name}] Running mutation: {mutation_name}")
            self.logger.info(f"[{mutation_name}] Objects bucket: {objects_bucket}")
            mutation_payload_string, used_objects = materializer.get_payload(mutation_name, objects_bucket, 'Mutation')

            # Step 2: Send the request & handle response
            self.logger.info(f"[{mutation_name}] Sending mutation payload string:\n {mutation_payload_string}")
            graphql_response, request_response = send_graphql_request(self.url, mutation_payload_string)
            status_code = request_response.status_code

            # Stats tracking stuff
            self.logger.info(f"Request Response code: {status_code}")
            Stats().add_http_status_code(mutation_name, status_code)

            # For the GraphQL reponse
            if not graphql_response:
                return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if "errors" in graphql_response:
                self.logger.info(f"[{mutation_name}] Mutation failed: {graphql_response['errors'][0]}")
                self.logger.info("[{mutation_name}] Retrying ---")
                graphql_response, retry_success = Retrier(self.logger).retry(self.url, mutation_payload_string, graphql_response, 0)
                if not retry_success:
                    return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if "data" not in graphql_response:
                self.logger.error(f"[{mutation_name}] No data in response: {graphql_response}")
                return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if graphql_response["data"][mutation_name] is None or check_is_data_empty(graphql_response["data"]):
                # Special case, this could indicate a failure or could also not, based on how GraphQLer is configured
                self.logger.info(f"[{mutation_name}] Mutation returned no data: {graphql_response} -- returning early")
                return (objects_bucket, graphql_response, Result.NO_DATA_SUCCESS)

            # Step 3
            self.logger.info(f"Response: {graphql_response}")

            # If there is information in the response, we need to process it
            # TODO: Store more things in the objects bucket (ie. names seen, other things seen, etc.)
            if type(graphql_response["data"][mutation_name]) is dict:
                mutation_output_type = get_output_type(mutation_name, self.mutations)
                if "id" in graphql_response["data"][mutation_name]:
                    returned_id = graphql_response["data"][mutation_name]["id"]
                    mutation_type = self.mutations[mutation_name]["mutationType"]

                    if mutation_type == "CREATE":
                        if returned_id is not None:
                            objects_bucket = put_in_object_bucket(objects_bucket, mutation_output_type, returned_id)
                    elif mutation_type == "UPDATE":
                        pass  # updates don't generally do anything to the objects bucket
                    elif mutation_type == "DELETE" and constants.ALLOW_DELETION_OF_OBJECTS:
                        if mutation_output_type in used_objects:
                            used_object_value = used_objects[mutation_output_type]
                            remove_from_object_bucket(objects_bucket, mutation_output_type, used_object_value)
                    else:
                        pass  # The UNKNOWN mutation type, we don't know what to do with it so just don't do anything
            else:
                pass

            return (objects_bucket, graphql_response, Result.GENERAL_SUCCESS)
        except HardDependencyNotMetException as e:
            self.logger.info(f"[{mutation_name}] Hard dependency not met: {e}")
            return (objects_bucket, None, Result.INTERNAL_FAILURE)
        except bdb.BdbQuit as exc:
            raise exc
        except Exception as e:
            # print(f"Exception when running: {mutation_name}: {e}, {traceback.print_exc()}")
            self.logger.info(f"[{mutation_name}] Exception when running: {mutation_name}: {e}, {traceback.format_exc()}")
            return (objects_bucket, None, Result.INTERNAL_FAILURE)

    def __run_query(self, query_name: str, objects_bucket: dict, materializer: Materializer) -> tuple[dict, Response, Result]:
        """Runs the query, and returns a new objects bucket

        Args:
            query_name (str): The name of the query
            objects_bucket (dict): The objects bucket
            materializer (QueryMaterializer): The materializer to use

        Returns:
            tuple[dict, Response, Result]: The new objects bucket, the graphql response, and the result of the query
        """
        try:
            # Step 1
            self.logger.info(f"[{query_name}] Running query: {query_name}")
            self.logger.info(f"[{query_name}] Objects bucket: {objects_bucket}")
            query_payload_string, used_objects = materializer.get_payload(query_name, objects_bucket, 'Query')

            # Step 2
            self.logger.info(f"[{query_name}] Sending query payload string:\n {query_payload_string}")
            graphql_response, request_response = send_graphql_request(self.url, query_payload_string)
            status_code = request_response.status_code

            # Stats tracking stuff
            self.logger.info(f"Request Response code: {status_code}")
            Stats().add_http_status_code(query_name, status_code)

            # For the GraphQL response
            if not graphql_response:
                return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if "errors" in graphql_response:
                self.logger.info(f"[{query_name}] Query failed: {graphql_response['errors'][0]}")
                self.logger.info("[{query_name}] Retrying ---")
                graphql_response, retry_success = Retrier(self.logger).retry(self.url, query_payload_string, graphql_response, 0)
                if not retry_success:
                    return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if "data" not in graphql_response:
                self.logger.error(f"[{query_name}] No data in response: {graphql_response}")
                return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)
            if graphql_response["data"][query_name] is None or check_is_data_empty(graphql_response["data"]):
                # Special case, this could indicate a failure or could also not, we mark it as fail
                self.logger.info(f"[{query_name}] No data in response: {graphql_response} -- returning early")
                if constants.NO_DATA_COUNT_AS_SUCCESS:
                    return (objects_bucket, graphql_response, Result.NO_DATA_SUCCESS)
                else:
                    return (objects_bucket, graphql_response, Result.EXTERNAL_FAILURE)

            # Step 3
            self.logger.info(f"Response: {graphql_response}")

            if type(graphql_response["data"][query_name]) is dict:
                query_output_type = get_output_type(query_name, self.queries)
                if "id" in graphql_response["data"][query_name]:
                    returned_id = graphql_response["data"][query_name]["id"]
                    if returned_id is not None:
                        objects_bucket = put_in_object_bucket(objects_bucket, query_output_type, returned_id)
            else:
                pass

            return (objects_bucket, graphql_response, Result.HAS_DATA_SUCCESS)
        except bdb.BdbQuit as exc:
            raise exc
        except Exception as e:
            self.logger.info(f"[{query_name}]Exception when running: {query_name}: {e}, {traceback.format_exc()}")
            return (objects_bucket, None, Result.INTERNAL_FAILURE)
