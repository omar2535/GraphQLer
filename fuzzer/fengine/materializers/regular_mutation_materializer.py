"""Regular mutation materializer:
Materializes a mutation that is ready to be sent off
"""

from .regular_materializer import RegularMaterializer
from .utils import prettify_graphql_payload
import logging


class RegularMutationMaterializer(RegularMaterializer):
    def __init__(self, objects: dict, mutations: dict, input_objects: dict, enums: dict, logger: logging.Logger):
        super().__init__(objects, mutations, input_objects, enums, logger)
        self.objects = objects
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums
        self.logger = self.logger  # use the base class' logger instead

    def get_payload(self, mutation_name: str, objects_bucket: dict) -> tuple[str, dict]:
        """Materializes the mutation with parameters filled in
           1. Make sure all dependencies are satisfied (hardDependsOn)
           2. Fill in the inputs ()

        Args:
            mutation_name (str): The mutation name
            objects_bucket (dict): The bucket of objects that have already been created

        Returns:
            tuple[str, dict]: The string of the mutation, and the used objects list
        """
        self.used_objects = {}  # Reset the used_objects list per run (from parent class)
        mutation_info = self.mutations[mutation_name]
        mutation_inputs = self.materialize_inputs(mutation_info, mutation_info["inputs"], objects_bucket)
        mutation_output = self.materialize_output(mutation_info["output"], [], False)
        mutation_payload = f"""
        mutation {{
            {mutation_name} (
                {mutation_inputs}
            )
            {mutation_output}
        }}
        """
        return prettify_graphql_payload(mutation_payload), self.used_objects
