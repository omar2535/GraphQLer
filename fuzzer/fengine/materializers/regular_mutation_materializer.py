"""Regular mutation materializer:
Materializes a mutation that is ready to be sent off
"""

from .utils import get_random_scalar, get_random_enum_value, get_random_id_from_bucket
from utils.parser_utils import get_base_oftype
import random
import constants


class RegularMutationMaterializer:
    def __init__(self, objects: dict, mutations: dict, input_objects: dict, enums: dict):
        self.objects = objects
        self.mutations = mutations
        self.input_objects = input_objects
        self.enums = enums

    def get_payload(self, mutation_name: str, objects_bucket: dict) -> str:
        """Materializes the mutation with parameters filled in
           1. Make sure all dependencies are satisfied (hardDependsOn)
           2. Fill in the inputs ()

        Args:
            mutation_name (str): The mutation name
            objects_bucket (dict): The bucket of objects that have already been created

        Returns:
            str: The string of the mutation
        """
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
        return mutation_payload

    def materialize_output(self, output: dict, used_objects: list[str], include_name: bool) -> str:
        """Materializes the output. Some interesting cases:
           - If we want to stop on an object materializing its fields, we need to not even include the object name
             IE: {id, firstName, user {}} should just be {id, firstName}
           Note: This function should be called on a base output type

        Args:
            output (dict): The output
            used_objects (list[str]): A list of used objects
            include_name (bool): Whether to include the name of the field or not

        Returns:
            str: The built output payload
        """
        built_str = ""
        if output["kind"] == "OBJECT":
            materialized_object_fields = self.materialize_object_fields(output["type"], used_objects)
            if materialized_object_fields != "":
                if include_name:
                    built_str += output["name"]
                built_str += " {"
                built_str += materialized_object_fields
                built_str += "},"
        elif output["kind"] == "NON_NULL" or output["kind"] == "LIST":
            base_oftype = get_base_oftype(output["ofType"])
            if base_oftype["kind"] == "SCALAR":
                built_str += f"{output['name']}, "
            else:
                materialized_output = self.materialize_output(base_oftype, used_objects, False)
                if materialized_output != "":
                    built_str += f"{output['name']}" + materialized_output + ", "
        else:
            built_str += f"{output['name']}, "
        return built_str

    def materialize_object_fields(self, object_name: str, used_objects: list[str]) -> str:
        """Loop through an objects fields, and call materialize_output on each of them

        Args:
            object_information (dict): The object's information
            used_objects (list[str]): A list of used objects

        Returns:
            str: The built output string
        """
        built_str = ""
        # If we've seen this object more than the max object cycles, don't use it again
        if used_objects.count(object_name) >= constants.MAX_OBJECT_CYCLES:
            return built_str

        # Mark that we've used this object
        used_objects.append(object_name)

        # Go through each of the object's fields, materialize
        object_info = self.objects[object_name]
        for field in object_info["fields"]:
            field_output = self.materialize_output(field, used_objects, True)
            if field_output != "" and field_output != "{}":
                built_str += field_output
        return built_str

    def materialize_inputs(self, mutation_info: dict, inputs: dict, objects_bucket: dict) -> str:
        """Goes through the inputs of the mutation

        Args:
            mutation_info (dict): The mutation information dictionary
            inputs (dict): The inputs of to be parsed
            objects_bucket (dict): The dynamically available objects that are currently in circulation

        Returns:
            str: The input parameters as a string
        """
        built_str = ""
        for input_name, input_field in inputs.items():
            built_str += f"{input_name}: " + self.materialize_input_field(mutation_info, input_field, objects_bucket, True) + ","
        return built_str

    def materialize_input_field(self, mutation_info: dict, input_field: dict, objects_bucket: dict, check_deps: bool) -> str:
        """Materializes a single input field
           - if the field is one we already know it depends on, just instantly resolve. Or else going down into
             the oftype will make us lose its name

        Args:
            mutation_info (dict): The mutation information dictionary
            input_field (dict): The field for a mutation (has the)
            objects_bucket (dict): The dynamically available objects that are currently in circulation
            check_deps (bool): Whether to check the dependencies first or not

        Returns:
            str: _description_
        """
        built_str = ""
        hard_dependencies: dict = mutation_info["hardDependsOn"]
        soft_dependencies: dict = mutation_info["softDependsOn"]

        # Must first resolve any dependencies we have access to(since if we go down and resolve ofTypes we lose its name)
        if check_deps and input_field["name"] in hard_dependencies:
            hard_dependency_name = hard_dependencies[input_field["name"]]
            if hard_dependency_name in objects_bucket:
                built_str += f'"{random.choice(objects_bucket[hard_dependency_name])}"'
            elif hard_dependency_name == "UNKNOWN":
                print(f"(F)(RegularMutationMaterializer) Using UNKNOWN input for field: {input_field}")
                built_str += self.materialize_input_field(mutation_info, input_field, objects_bucket, False)
            else:
                raise Exception(f"Hard dependency not found in objects bucket for: {input_field['name']}:{hard_dependency_name}")
        elif check_deps and input_field["name"] in soft_dependencies:
            soft_depedency_name = soft_dependencies[input_field["name"]]
            if soft_depedency_name in objects_bucket:
                built_str += f'"{random.choice(objects_bucket[soft_depedency_name])}"'
            else:
                built_str += self.materialize_input_field(mutation_info, input_field, objects_bucket, False)
        elif input_field["kind"] == "NON_NULL":
            built_str += self.materialize_input_field(mutation_info, input_field["ofType"], objects_bucket, True)
        elif input_field["kind"] == "LIST":
            built_str += f"[{self.materialize_input_field(mutation_info, input_field['ofType'], objects_bucket), True}]"
        elif input_field["kind"] == "INPUT_OBJECT":
            input_object = self.input_objects[input_field["type"]]
            built_str += "{" + self.materialize_inputs(mutation_info, input_object["inputFields"], objects_bucket) + "}"
        elif input_field["kind"] == "SCALAR":
            built_str += get_random_scalar(input_field["name"], input_field["type"])
        else:
            built_str += ""
        return built_str
