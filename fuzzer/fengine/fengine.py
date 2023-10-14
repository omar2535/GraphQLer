"""FEngine: Responsible for getting the materialized query, running it against the API, and returning if it succeeds
            and the new objects that were returned (if any were updated)
"""

from .materializers import RegularMutationMaterializer, RegularQueryMaterializer
from fuzzer.utils import put_in_object_bucket
from pathlib import Path

from utils.request_utils import send_graphql_request
from utils.parser_utils import get_output_type
from utils.logging_utils import get_logger
from .exceptions import HardDependencyNotMetException
import traceback
import constants


class FEngine:
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
        self.logger = get_logger(__name__, Path(save_path) / constants.FENGINE_LOG_FILE_PATH)

    def run_regular_mutation(self, mutation_name: str, objects_bucket: dict) -> tuple[dict, bool]:
        """Runs the mutation, and returns a new objects bucket. Performs a few things:
           1. Materializes the mutation with its parameters (resolving any dependencies from the object_bucket)
           2. Send the mutation against the server and gets the parses the object from the response
           3. Saves the result in the objects_bucket if it's an object

        Args:
            mutation_name (str): Name of the mutation
            objects_bucket (dict): The current objects bucket

        Returns:
            tuple[dict, bool]: The new objects bucket, and whether the mutation succeeded or not
        """
        try:
            # Step 1
            materializer = RegularMutationMaterializer(self.objects, self.mutations, self.input_objects, self.enums, self.logger)
            mutation_payload_string = materializer.get_payload(mutation_name, objects_bucket)
            self.logger.info(f"[{mutation_name}] Sending mutation payload string: {mutation_payload_string}")

            # Step 2
            response = send_graphql_request(self.url, mutation_payload_string)
            if not response:
                return (objects_bucket, False)
            if "data" not in response:
                self.logger.error(f"[{mutation_name}] No data in response: {response}")
                return (objects_bucket, False)
            if response["data"][mutation_name] is None:
                self.logger.info(f"[{mutation_name}] Mutation failed (returned None)")
                return (objects_bucket, False)

            # Step 3
            mutation_output_type = get_output_type(mutation_name, self.mutations)
            if "id" in response["data"][mutation_name]:
                returned_id = response["data"][mutation_name]["id"]
                objects_bucket = put_in_object_bucket(objects_bucket, mutation_output_type, returned_id)

            # TODO: Check for mutation type, if it's an UPDATE, then we need to update the object in the objects_bucket
            # TODO: Check for mutation type, if it's an DELETE, then we need to remove the object in the objects_bucket

            return (objects_bucket, True)
        except HardDependencyNotMetException as e:
            self.logger.info(f"[{mutation_name}] Hard dependency not met: {e}")
            return (objects_bucket, False)
        except Exception as e:
            self.logger.info(f"[{mutation_name}] Exception when running: {mutation_name}: {e}, {traceback.format_exc()}")
            return (objects_bucket, False)

    def run_regular_query(self, query_name: str, objects_bucket: dict) -> tuple[dict, bool]:
        """Runs the query, and returns a new objects bucket

        Args:
            query_name (str): The name of the query
            objects_bucket (dict): The objects bucket

        Returns:
            tuple[dict, bool]: The new objects bucket, and whether the mutation succeeded or not
        """
        try:
            # Step 1
            materializer = RegularQueryMaterializer(self.objects, self.queries, self.input_objects, self.enums, self.logger)
            query_payload_string = materializer.get_payload(query_name, objects_bucket)
            self.logger.info("[{query_name}] Sending query payload string: {query_payload_string}")

            # Step 2
            response = send_graphql_request(self.url, query_payload_string)
            if not response:
                return (objects_bucket, False)
            if "data" not in response:
                self.logger.error(f"[{query_name}] No data in response: {response}")
                return (objects_bucket, False)
            if response["data"][query_name] is None:
                self.logger.info(f"[{query_name}] Query failed (returned None)")
                return (objects_bucket, False)

            # Step 3
            query_output_type = get_output_type(query_name, self.queries)
            if "id" in response["data"][query_name]:
                returned_id = response["data"][query_name]["id"]
                objects_bucket = put_in_object_bucket(objects_bucket, query_output_type, returned_id)

            return (objects_bucket, True)
        except Exception as e:
            self.logger.info(f"[{query_name}]Exception when running: {query_name}: {e}, {traceback.print_exc()}")
            return (objects_bucket, False)
