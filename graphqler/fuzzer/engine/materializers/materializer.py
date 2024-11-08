"""Materializer:
Base class for a regular materializer
"""

from ..exceptions.hard_dependency_not_met_exception import HardDependencyNotMetException
from .utils.materialization_utils import is_valid_object_materialization, clean_output_selectors
from .getter import Getter
from graphqler.utils.logging_utils import Logger
from graphqler.utils.parser_utils import get_base_oftype, is_simple_scalar
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.api import API
from graphqler import config


class Materializer:
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = True, max_depth: int = 5, getter: Getter = Getter()):
        """Default constructor for a regular materializer

        Args:
            api (API): The API object
            fail_on_hard_dependency_not_met (bool, optional): Whether to fail on hard dependency not met. Defaults to True.
            getter (Getter, optional): The getters object. Defaults to Getter()
        """
        self.api = api
        self.logger = Logger().get_fuzzer_logger().getChild(__name__)  # Get a child logger
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.used_objects = {}
        self.max_depth = max_depth
        self.getter = getter

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        """Materializes the payload with parameters filled in

        Args:
            query_name (str): name of the graphql query or mutation
            objects_bucket (dict): objects bucket
            graphql_type (str, optional): one of Query or Mutation. Defaults to ''.

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        return ("", {})

    def materialize_output(self,
                           operator_info: dict,
                           output: dict,
                           objects_bucket: ObjectsBucket,
                           max_depth: int = 5,
                           minimal_materialization: bool = False) -> str:
        """Materializes the output. If returns empty string,
           then tries to get at least something, bypassing the max depth until the hard cutoff.

        Args:
            operator_info (dict): The operator information
            output_info (dict): The output information
            objects_bucket (dict): List of objects that have been created or found
            max_depth (int, optional): Maximum depth for recursive expansion of objects. Defaults to 2.
                                       If nothing is returned for this max depth, then we try to get at least something
                                       by bypassing the max depth until the hard cutoff.
            minimal_materialization (bool, optional): Whether to materialize only the minimal fields. Defaults to False.

        Returns:
            str: The otput selectors
        """
        output_selectors = ""
        max_depth = max_depth
        while output_selectors == "":
            # The initial call to materialize_output_recursive should not include the name and has no objects used yet
            output_selectors = self.materialize_output_recursive(
                operator_info=operator_info,
                output_field=output,
                used_objects=[],
                objects_bucket=objects_bucket,
                include_name=False,
                minimal_materialization=minimal_materialization,
                max_depth=max_depth,
                current_depth=0
            )
            if max_depth > config.HARD_CUTOFF_DEPTH:
                break
            max_depth += 1
        cleaned_output_selectors = clean_output_selectors(output_selectors)
        return cleaned_output_selectors

    def materialize_output_recursive(self,
                                     operator_info: dict,
                                     output_field: dict,
                                     used_objects: list[str],
                                     objects_bucket: ObjectsBucket,
                                     include_name: bool,
                                     minimal_materialization: bool,
                                     max_depth: int,
                                     current_depth: int = 0) -> str:
        """Materializes the output recursively. Some interesting cases:
           - If we want to stop on an object materializing its fields, we need to not even include the object name
             IE: {id, firstName, user {}} should just be {id, firstName}
           Note: This function should be called on a base output type

        Args:
            operator_info (dict): Information about the operator that we want to materialize
            output_field (dict): The field to be output
            used_objects (list[str]): A list of used objects
            objects_bucket (dict): List of objects that have been created or found
            include_name (bool): Whether to include the name of the field or not
            minimal_materialization (bool): Whether to materialize only the minimal fields
            max_depth (int): The maximum depth to expand outputs for nested objects
            current_depth (int): The current depth of the output

        Returns:
            str: The built output payload
        """
        built_str = ""

        # When we are including names (IE. fields of an object), we need to include the name of the field
        if include_name:
            built_str += output_field["name"]

        # If there are arguments for this, materialize the arguments
        if "inputs" in output_field and len(output_field["inputs"]) != 0:
            inputs = self.materialize_input_fields(operator_info, output_field["inputs"], objects_bucket, max_depth, current_depth)
            if inputs != "":
                built_str += f"({inputs})"

        # Main materialiation logic
        if output_field["kind"] == "OBJECT":
            materialized_object_fields = self.materialize_output_object_fields(operator_info, output_field["type"], used_objects, objects_bucket, minimal_materialization, max_depth, current_depth)
            if materialized_object_fields != "":
                built_str += " {"
                built_str += materialized_object_fields
                built_str += "},"
        elif output_field["kind"] == "UNION":  # For a UNION type, loop through all the UNION types and materialize them into fragments
            union_types = self.api.unions[output_field["type"]]["possibleTypes"]
            built_str += " {"
            for union_type in union_types:
                materialized_fragment = self.materialize_output_recursive(operator_info, union_type, used_objects, objects_bucket, False, minimal_materialization, max_depth, current_depth)
                if materialized_fragment != "":
                    built_str += f"... on {union_type['name']} " + materialized_fragment
            built_str += "},"
        elif output_field["kind"] == "INTERFACE":  # For an INTERFACE type, loop through all the INTERFACE types and materialize them into fragments
            interface_types = self.api.interfaces[output_field["type"]]["possibleTypes"]
            built_str += " {"
            for interface_type in interface_types:
                materialized_fragment = self.materialize_output_recursive(operator_info, interface_type, used_objects, objects_bucket, False, minimal_materialization, max_depth, current_depth)
                if materialized_fragment != "":
                    built_str += f"... on {interface_type['name']} " + materialized_fragment
            built_str += "},"
        elif (output_field["kind"] == "NON_NULL" or output_field["kind"] == "LIST"):  # For a NON_NULL / LIST kind: Don't +1 here because it is an oftype (which doesn't add depth), or else we will double count
            oftype = output_field["ofType"]
            materialized_output = self.materialize_output_recursive(operator_info, oftype, used_objects, objects_bucket, False, minimal_materialization, max_depth, current_depth)
            if materialized_output != "":
                built_str += materialized_output + ", "
        else:
            built_str += ","

        # If it's a non-scalar but we didn't materialize any fields, then we should return an empty string
        # Very important for NON_NULL / LIST / OBJECT types
        chars_to_remove = ",{}. "
        translation_table = str.maketrans("", "", chars_to_remove)
        if get_base_oftype(output_field)["kind"] != "SCALAR" and include_name:
            if built_str == output_field["name"]:
                return ""
            elif built_str.translate(translation_table) == output_field["name"]:
                return ""
            elif not is_valid_object_materialization(built_str):
                return ""

        # A bit of post processing on the built payload
        if include_name and built_str[-1] != ",":
            built_str += ","
        elif not include_name and built_str.strip() == "{}":
            built_str = ""

        return built_str

    def materialize_output_object_fields(self,
                                         operator_info: dict,
                                         object_name: str,
                                         used_objects: list[str],
                                         objects_bucket: ObjectsBucket,
                                         minimal_materialization: bool,
                                         max_depth: int,
                                         current_depth: int) -> str:
        """Loop through an objects fields, and call materialize_output on each of them

        Args:
            operator_info (dict): The operator information
            object_information (dict): The object's information
            used_objects (list[str]): A list of used objects
            objects_bucket (dict): List of objects that have been created or found
            minimal_materialization (bool): Whether to materialize only the minimal fields
            max_depth (int): The maximum depth to expand outputs for nested objects
            current_depth (int): The current depth of the output

        Returns:
            str: The built output string
        """
        built_str = ""
        object_info = self.api.objects[object_name]
        fields_to_materialize = object_info["fields"]

        # If we've seen this object more than the max object cycles, don't use it again
        # But only do this check while we aren't only materializing non-null fields
        if used_objects.count(object_name) >= config.MAX_OBJECT_CYCLES:
            return built_str

        # Check has any scalar at root level, if it does then we can filter out the rest
        # We have to do this because sometimes root level might only be an object that outputs another object
        if minimal_materialization and current_depth == 0:
            has_scalar = False
            for field in fields_to_materialize:
                if is_simple_scalar(field):
                    has_scalar = True
                    break
            if has_scalar:
                fields_to_materialize = [field for field in fields_to_materialize if is_simple_scalar(field)]

        # If we're materializing only minimal fields, then we should only materialize scalar fields as long as we're not at the highest depth
        if minimal_materialization and current_depth != 0:
            fields_to_materialize = [field for field in fields_to_materialize if is_simple_scalar(field)]

        # If we're at max depth, materialize only scalar fields
        if current_depth >= max_depth:
            fields_to_materialize = [field for field in fields_to_materialize if is_simple_scalar(field)]

        # Mark that we've used this object
        used_objects.append(object_name)

        # Loop through the fields to materialize each field
        for field in fields_to_materialize:
            field_output = self.materialize_output_recursive(operator_info, field, used_objects, objects_bucket, True, minimal_materialization, max_depth, current_depth + 1)
            if field_output != "" and field_output != "{}":
                built_str += field_output
        return built_str

    def materialize_inputs(self, operator_info: dict, inputs: dict, objects_bucket: ObjectsBucket, max_depth: int) -> str:
        """Goes through the inputs of the payload

        Args:
            operator_info (dict): All information about the operator (either all QUERYs or all MUTATIONs) that we want to materialize
            inputs (dict): The inputs of to be parsed
            objects_bucket (dict): The dynamically available objects that are currently in circulation
            max_depth (int): The maximum depth to proceed to when unravelling nested input objects

        Returns:
            str: The input parameters as a string
        """
        return self.materialize_input_fields(operator_info, inputs, objects_bucket, max_depth, current_depth=0)

    def materialize_input_fields(self, operator_info: dict, inputs: dict, objects_bucket: ObjectsBucket, max_depth: int, current_depth: int = 0) -> str:
        """Goes through the inputs of the payload

        Args:
            operator_info (dict): All information about the operator (either all QUERYs or all MUTATIONs) that we want to materialize
            inputs (dict): The inputs of to be parsed
            objects_bucket (dict): The dynamically available objects that are currently in circulation

        Returns:
            str: The input parameters as a string
        """
        built_str = ""

        # Return early if there are no inputs
        if inputs is None or len(inputs) == 0 or type(inputs) is not dict:
            return built_str

        # Return early if we exceed the max depth
        if current_depth >= max_depth:
            return built_str

        # Go through each input field and materialize it
        for input_name, input_field in inputs.items():
            built_str += f"{input_name}: " + self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, True, max_depth, current_depth + 1) + ","
        return built_str

    def materialize_input_recursive(self,
                                    operator_info: dict,
                                    input_field: dict,
                                    objects_bucket: ObjectsBucket,
                                    input_name: str,
                                    check_deps: bool,
                                    max_depth: int,
                                    current_depth: int) -> str:
        """Materializes a single input field
           - if the field is one we already know it depends on, just instantly resolve. Or else going down into
             the oftype will make us lose its name

        Args:
            operator_info (dict): All information about the operator (either all QUERYs or all MUTATIONs) that we want to materialize
            input_field (dict): The field for a mutation (has the)
            objects_bucket (dict): The dynamically available objects that are currently in circulation
            input_name (str): The input's name in the overall query (not to be confused with input_field["name"] - which is the field's name in the struct)
            check_deps (bool): Whether to check the dependencies first or not

        Returns:
            str: String of the materialized input field
        """
        built_str = ""
        hard_dependencies: dict = operator_info.get("hardDependsOn", {})
        soft_dependencies: dict = operator_info.get("softDependsOn", {})

        # Must first resolve any dependencies we have access to(since if we go down and resolve ofTypes we lose its name)
        if check_deps and input_field["name"] in hard_dependencies:
            hard_dependency_object_name = hard_dependencies[input_field["name"]]
            if objects_bucket.is_object_in_bucket(hard_dependency_object_name):
                # Use the object from the objects bucket, mark it as used, then continue constructing the string
                randomly_chosen_object_dependency_val = self.getter.get_closest_value_to_input(input_field["name"], hard_dependency_object_name, objects_bucket)
                self.used_objects[hard_dependency_object_name] = randomly_chosen_object_dependency_val
                built_str += f'"{randomly_chosen_object_dependency_val}"'
            elif hard_dependency_object_name == "UNKNOWN":
                self.logger.info(f"Using UNKNOWN input for field: {input_field}")
                built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
            else:
                if self.fail_on_hard_dependency_not_met:  # If we are using the dependency graph, then we should be careful dependencies aren't met
                    raise HardDependencyNotMetException(hard_dependency_object_name)
                else:  # Otherwise, in regular non-dependency aware mode, we just materialize the input field
                    self.logger.info("Hard dependency not met -- using random input")
                    built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
        elif check_deps and input_field["name"] in soft_dependencies:
            soft_depedency_name = soft_dependencies[input_field["name"]]
            if objects_bucket.is_object_in_bucket(soft_depedency_name):
                # Use the object from the objects bucket, mark it as used, then continue constructing the string
                randomly_chosen_dependency_val = objects_bucket.get_random_object_field_value(soft_depedency_name, input_field["name"])
                self.used_objects[soft_depedency_name] = randomly_chosen_dependency_val
                built_str += f'"{randomly_chosen_dependency_val}"'
            else:
                built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
        elif input_field["kind"] == "NON_NULL":
            built_str += self.materialize_input_recursive(operator_info, input_field["ofType"], objects_bucket, input_name, True, max_depth, current_depth)
        elif input_field["kind"] == "LIST":
            built_str += f"[{self.materialize_input_recursive(operator_info, input_field['ofType'], objects_bucket, input_name, True, max_depth, current_depth)}]"
        elif input_field["kind"] == "INPUT_OBJECT":
            input_object = self.api.input_objects[input_field["type"]]
            built_str += "{" + self.materialize_input_fields(operator_info, input_object["inputFields"], objects_bucket, max_depth, current_depth) + "}"
        elif input_field["kind"] == "SCALAR":
            built_str += self.getter.get_random_scalar(input_name, input_field["type"], objects_bucket)
        elif input_field["kind"] == "ENUM":
            built_str += self.getter.get_random_enum_value(self.api.enums[input_field["type"]]["enumValues"])
        else:
            built_str += ""

        return built_str
