"""Materializer:
Base class for a regular materializer
"""

from graphqler import constants
from .utils import get_random_scalar, get_random_enum_value, clean_output_selectors
from graphqler.utils.logging_utils import Logger
from ..exceptions.hard_dependency_not_met_exception import HardDependencyNotMetException

import random
import logging


class Materializer:
    def __init__(self,
                 objects: dict,
                 operator_info: dict,
                 input_objects: dict,
                 enums: dict,
                 unions: dict,
                 interfaces: dict,
                 fail_on_hard_dependency_not_met: bool = True):
        """Default constructor for a regular materializer

        Args:
            objects (dict): The objects that exist in the Graphql schema
            operator_info (dict): All information about the operator (either all QUERYs or all MUTATIONs) that we want to materialize
            input_objects (dict): The input objects that exist in the Graphql schema
            enums (dict): The enums that exist in the Graphql schema
            unions (dict): The unions that exist in the Graphql schema
            interfaces (dict): The interfaces that exist in the Graphql schema
            logger (logging.Logger): The logger
        """
        self.objects = objects
        self.operator_info = operator_info
        self.input_objects = input_objects
        self.enums = enums
        self.unions = unions
        self.interfaces = interfaces
        self.logger = Logger().get_fuzzer_logger().getChild(__name__)  # Get a child logger
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.used_objects = {}

    def get_payload(self, name: str, objects_bucket: dict, graphql_type: str = '') -> tuple[str, dict]:
        """Materializes the payload with parameters filled in

        Args:
            query_name (str): name of the graphql query or mutation
            objects_bucket (dict): objects bucket
            graphql_type (str, optional): one of Query or Mutation. Defaults to ''.

        Returns:
            tuple[str, dict]: The string of the payload, and the used objects list
        """
        pass

    def materialize_output(self,
                           output_info: dict,
                           used_objects: list[str],
                           objects_bucket: dict,
                           include_name: bool,
                           max_depth: int = 5) -> str:
        """Materializes the output. If returns empty string,
           then tries to get at least something, bypassing the max depth until the hard cutoff.

        Args:
            output_info (dict): The output information
            used_objects (list[str]): The used objects
            objects_bucket (dict): List of objects that have been created or found
            include_name (bool): The included name
            max_depth (int, optional): Maximum depth for recursive expansion of objects. Defaults to 2.
                                       If nothing is returned for this max depth, then we try to get at least something
                                       by bypassing the max depth until the hard cutoff.

        Returns:
            str: The otput selectors
        """
        output_selectors = ""
        max_depth = max_depth
        while output_selectors == "":
            output_selectors = self.materialize_output_recursive(
                field=output_info,
                used_objects=used_objects,
                objects_bucket=objects_bucket,
                include_name=include_name,
                max_depth=max_depth,
                current_depth=0
            )
            if max_depth > constants.HARD_CUTOFF_DEPTH:
                break
            max_depth += 1
        cleaned_output_selectors = clean_output_selectors(output_selectors)
        return cleaned_output_selectors

    def materialize_output_recursive(self,
                                     field: dict,
                                     used_objects: list[str],
                                     objects_bucket: dict,
                                     include_name: bool,
                                     max_depth: int,
                                     current_depth: int = 0) -> str:
        """Materializes the output recursively. Some interesting cases:
           - If we want to stop on an object materializing its fields, we need to not even include the object name
             IE: {id, firstName, user {}} should just be {id, firstName}
           Note: This function should be called on a base output type

        Args:
            field (dict): The field to be output
            used_objects (list[str]): A list of used objects
            objects_bucket (dict): List of objects that have been created or found
            include_name (bool): Whether to include the name of the field or not
            max_depth (int): The maximum depth to expand outputs for nested objects
            current_depth (int): The current depth of the output

        Returns:
            str: The built output payload
        """
        built_str = ""

        # If we reached max_depth, don't materialize anything except for NON_NULL / scalars
        if current_depth >= max_depth:
            return ""

        # When we are including names (IE. fields of an object), we need to include the name of the field
        if include_name:
            built_str += field["name"]

        # If there are arguments for this, materialize the arguments
        if 'inputs' in field and len(field["inputs"]) != 0:
            inputs = self.materialize_input_fields(self.operator_info, field["inputs"], {}, max_depth, current_depth)
            if inputs != "":
                built_str += f"({inputs})"

        # Main materialiation logic
        if field["kind"] == "OBJECT":
            materialized_object_fields = self.materialize_output_object_fields(field["type"], used_objects, objects_bucket, max_depth, current_depth)
            if materialized_object_fields != "":
                built_str += " {"
                built_str += materialized_object_fields
                built_str += "},"
        elif field["kind"] == "UNION":  # For a UNION type, loop through all the UNION types and materialize them into fragments
            union_types = self.unions[field["type"]]["possibleTypes"]
            built_str += " {"
            for union_type in union_types:
                materialized_fragment = self.materialize_output_recursive(union_type, used_objects, objects_bucket, False, max_depth, current_depth)
                if materialized_fragment != "":
                    built_str += f"... on {union_type['name']} " + materialized_fragment
            built_str += "},"
        elif field["kind"] == "INTERFACE":  # For an INTERFACE type, loop through all the INTERFACE types and materialize them into fragments
            interface_types = self.interfaces[field["type"]]["possibleTypes"]
            built_str += " {"
            for interface_type in interface_types:
                materialized_fragment = self.materialize_output_recursive(interface_type, used_objects, objects_bucket, False, max_depth, current_depth)
                if materialized_fragment != "":
                    built_str += f"... on {interface_type['name']} " + materialized_fragment
            built_str += "},"
        elif field["kind"] == "NON_NULL" or field["kind"] == "LIST":  # For a NON_NULL / LIST kind: Don't +1 here because it is an oftype (which doesn't add depth), or else we will double count
            oftype = field["ofType"]
            materialized_output = self.materialize_output_recursive(oftype, used_objects, objects_bucket, False, max_depth, current_depth)
            if materialized_output != "":
                built_str += materialized_output + ", "
        else:
            built_str += ","

        # If it's a non-scalar but we didn't materialize any fields, then we should return an empty string
        # Very important for NON_NULL / LIST / OBJECT types
        if include_name and built_str == field["name"] and field["kind"] != "SCALAR":
            return ""

        # A bit of post processing on the built payload
        if include_name and built_str[-1] != ",":
            built_str += ","
        elif not include_name and built_str.strip() == "{}":
            built_str = ""

        return built_str

    def materialize_output_object_fields(self,
                                         object_name: str,
                                         used_objects: list[str],
                                         objects_bucket: dict,
                                         max_depth: int,
                                         current_depth: int) -> str:
        """Loop through an objects fields, and call materialize_output on each of them

        Args:
            object_information (dict): The object's information
            used_objects (list[str]): A list of used objects
            objects_bucket (dict): List of objects that have been created or found
            max_depth (int): The maximum depth to expand outputs for nested objects
            current_depth (int): The current depth of the output

        Returns:
            str: The built output string
        """
        built_str = ""
        object_info = self.objects[object_name]
        fields_to_materialize = object_info["fields"]

        # If we've seen this object more than the max object cycles, don't use it again
        # But only do this check while we aren't only materializing non-null fields
        if used_objects.count(object_name) >= constants.MAX_OBJECT_CYCLES:
            return built_str

        # Mark that we've used this object
        used_objects.append(object_name)

        # Loop through the fields to materialize each field
        for field in fields_to_materialize:
            field_output = self.materialize_output_recursive(field, used_objects, objects_bucket, True, max_depth, current_depth + 1)
            if field_output != "" and field_output != "{}":
                built_str += field_output
        return built_str

    def materialize_inputs(self, operator_info: dict, inputs: dict, objects_bucket: dict, max_depth: int) -> str:
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

    def materialize_input_fields(self, operator_info: dict, inputs: dict, objects_bucket: dict, max_depth: int, current_depth: int = 0) -> str:
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

        # Go through each input field and materialize it
        for input_name, input_field in inputs.items():
            built_str += f"{input_name}: " + self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, True, max_depth, current_depth + 1) + ","
        return built_str

    def materialize_input_recursive(
        self, operator_info: dict, input_field: dict, objects_bucket: dict, input_name: str, check_deps: bool, max_depth: int, current_depth: int
    ) -> str:
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
        if current_depth >= max_depth:
            return ""

        built_str = ""
        hard_dependencies: dict = operator_info.get("hardDependsOn", {})
        soft_dependencies: dict = operator_info.get("softDependsOn", {})

        # Must first resolve any dependencies we have access to(since if we go down and resolve ofTypes we lose its name)
        if check_deps and input_field["name"] in hard_dependencies:
            hard_dependency_name = hard_dependencies[input_field["name"]]
            if hard_dependency_name in objects_bucket:
                # Use the object from the objects bucket, mark it as used, then continue constructing the string
                randomly_chosen_dependency_val = random.choice(objects_bucket[hard_dependency_name])
                self.used_objects[hard_dependency_name] = randomly_chosen_dependency_val
                built_str += f'"{randomly_chosen_dependency_val}"'
            elif hard_dependency_name == "UNKNOWN":
                self.logger.info(f"Using UNKNOWN input for field: {input_field}")
                built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
            else:
                if self.fail_on_hard_dependency_not_met:  # If we are using the dependency graph, then we should be careful dependencies aren't met
                    raise HardDependencyNotMetException(hard_dependency_name)
                else:  # Otherwise, in regular non-dependency aware mode, we just materialize the input field
                    self.logger.info("Hard dependency not met -- using random input")
                    built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
        elif check_deps and input_field["name"] in soft_dependencies:
            soft_depedency_name = soft_dependencies[input_field["name"]]
            if soft_depedency_name in objects_bucket:
                # Use the object from the objects bucket, mark it as used, then continue constructing the string
                randomly_chosen_dependency_val = random.choice(objects_bucket[soft_depedency_name])
                self.used_objects[soft_depedency_name] = randomly_chosen_dependency_val
                built_str += f'"{randomly_chosen_dependency_val}"'
            else:
                built_str += self.materialize_input_recursive(operator_info, input_field, objects_bucket, input_name, False, max_depth, current_depth)
        elif input_field["kind"] == "NON_NULL":
            built_str += self.materialize_input_recursive(operator_info, input_field["ofType"], objects_bucket, input_name, True, max_depth, current_depth)
        elif input_field["kind"] == "LIST":
            built_str += f"[{self.materialize_input_recursive(operator_info, input_field['ofType'], objects_bucket, input_name, True, max_depth, current_depth)}]"
        elif input_field["kind"] == "INPUT_OBJECT":
            input_object = self.input_objects[input_field["type"]]
            built_str += "{" + self.materialize_input_fields(operator_info, input_object["inputFields"], objects_bucket, max_depth, current_depth) + "}"
        elif input_field["kind"] == "SCALAR":
            built_str += get_random_scalar(input_name, input_field["type"], objects_bucket)
        elif input_field["kind"] == "ENUM":
            built_str += get_random_enum_value(self.enums[input_field["type"]]["enumValues"])
        else:
            built_str += ""
        return built_str
