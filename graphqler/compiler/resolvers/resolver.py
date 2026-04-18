from .utils import find_closest_string, strip_crud_prefix
from graphqler.utils.parser_utils import get_base_oftype


class Resolver:
    def __init__(self):
        pass

    def _resolve_produces(self, operation: dict, objects: dict) -> str:
        """Returns the inner object type produced by a list/connection output, or empty string.

        A query or mutation "produces" an inner type when its direct output type is a
        connection/wrapper object (e.g. CountryConnection) that contains a list field named
        ``items``, ``nodes``, or ``edges`` whose base element type is a known OBJECT.
        For Relay-style ``edges`` fields the resolution descends one extra level through
        the edge type's ``node`` field to return the actual domain object type.

        Example::

            # Schema:
            #   type Query { countries: CountryConnection }
            #   type CountryConnection { items: [Country] }
            #   type Country { id: ID! }
            #
            # Compiled query dict:
            #   {"output": {"kind": "OBJECT", "name": "CountryConnection", ...}}
            #
            # _resolve_produces(query, objects)  =>  "Country"
            #
            # The graph generator then wires:  countries -> Country  (weight 100)
            # so the bucket contains real Country IDs before country(id: ID!) runs.

        Args:
            operation (dict): A compiled query or mutation dict (must have an ``output`` key)
            objects (dict): All compiled objects from the schema

        Returns:
            str: The inner object type name (e.g. "Country"), or "" if not applicable
        """
        output = operation.get("output", {})
        if output.get("ofType") is not None:
            base_output = get_base_oftype(output["ofType"])
        else:
            base_output = output

        if base_output.get("kind") != "OBJECT":
            return ""

        outer_type_name = base_output.get("type") or base_output.get("name") or ""
        if not outer_type_name or outer_type_name not in objects:
            return ""

        connection_keys = ("items", "nodes", "edges")
        for field in objects[outer_type_name].get("fields", []):
            if field["name"] not in connection_keys:
                continue
            oftype = field.get("ofType")
            if not oftype:
                continue
            inner_base = get_base_oftype(oftype)
            if inner_base.get("kind") != "OBJECT":
                continue
            inner_type = inner_base.get("type") or inner_base.get("name") or ""
            if not inner_type or inner_type not in objects:
                continue
            if field["name"] == "edges":
                node_type = self._resolve_node_type(inner_type, objects)
                if node_type:
                    return node_type
            return inner_type

        return ""

    def _resolve_node_type(self, edge_type_name: str, objects: dict) -> str:
        """Returns the OBJECT type of the ``node`` field of a Relay edge type, or empty string.

        Args:
            edge_type_name (str): The edge type (e.g. "CountryEdge")
            objects (dict): All compiled objects from the schema

        Returns:
            str: The node's OBJECT type name (e.g. "Country"), or "" if not found
        """
        if edge_type_name not in objects:
            return ""
        for field in objects[edge_type_name].get("fields", []):
            if field["name"] != "node":
                continue
            oftype = field.get("ofType")
            if oftype:
                base = get_base_oftype(oftype)
                if base.get("kind") == "OBJECT":
                    node_type = base.get("type") or base.get("name") or ""
                    if node_type and node_type in objects:
                        return node_type
            if field.get("kind") == "OBJECT":
                node_type = field.get("type") or field.get("name") or ""
                if node_type and node_type in objects:
                    return node_type
        return ""

    def get_inputs_related_to_ids(self, inputs: dict, input_objects: dict) -> dict:
        """Recursively finds any inputs that has ID in its name as that would imply it references other objects

        Args:
            inputs (dict): An inputs
            input_objects (dict): The input objects to be used for recursive search

        Returns:
            dict: A dictionary of id and if it's NON_NULL or not IE. {'userId': False, 'clientId': True}
        """
        if inputs is None:
            return {}
        else:
            found_ids = {}
            for input_name, input in inputs.items():
                if self.is_input_an_id(input):
                    found_ids[input_name] = input["kind"] == "NON_NULL"
                elif self.is_input_object(input):
                    input_object_name = input["ofType"]["name"]
                    if input_object_name not in input_objects:
                        continue
                    input_object = input_objects[input_object_name]
                    found_ids.update(self.get_inputs_related_to_ids(input_object["inputFields"], input_objects))
            return found_ids

    def resolve_inputs_related_to_ids_to_objects(self, endpoint_name: str, inputs_related_to_ids: dict, objects: dict) -> dict:
        """Resolves inputs related to IDs by looking at the name of the parameter after the ID string is removed

        Args:
            endpoint_name (str): The name of the query or mutation for these inputs
            inputs_related_to_ids (dict): The inputs name (IE: userId)
            objects (dict): All the possible objects for this API

        Returns:
            dict: Input parameters to the objects and the required / not required mappings
        """
        input_id_object_mapping = {"hardDependsOn": {}, "softDependsOn": {}}

        for input_name, required in inputs_related_to_ids.items():
            # Get the object's name
            object_name = input_name
            if input_name.lower() == "id":
                guessed_object_name = find_closest_string(list(objects.keys()), strip_crud_prefix(endpoint_name))
            elif input_name.lower() == "ids":
                guessed_object_name = find_closest_string(list(objects.keys()), strip_crud_prefix(endpoint_name))
            elif input_name[-2:].lower() == "id":
                object_name = object_name[:-2]
                guessed_object_name = find_closest_string(list(objects.keys()),object_name)
            elif input_name[-3:].lower() == "ids":
                object_name = object_name[:-3]
                guessed_object_name = find_closest_string(list(objects.keys()),object_name)
            else:
                guessed_object_name = ""

            # Check if the object's name is in the object listing
            if guessed_object_name in objects:
                assigned_dependency_name = guessed_object_name
            else:
                assigned_dependency_name = "UNKNOWN"

            # Now assign it either a hardDependsOn or softDependsOn
            if required:
                input_id_object_mapping["hardDependsOn"][input_name] = assigned_dependency_name
            else:
                input_id_object_mapping["softDependsOn"][input_name] = assigned_dependency_name
        return input_id_object_mapping

    def is_input_object(self, input: dict) -> bool:
        return input["ofType"] and input["ofType"]["kind"] == "INPUT_OBJECT"

    def is_input_an_id(self, input: dict) -> bool:
        """Checks if the input is an ID field

        Args:
            input (dict): The input field to check

        Returns:
            bool: True if the field is an ID, False otherwise
        """
        if input["ofType"]:
            input = get_base_oftype(input["ofType"])

        return input["kind"] == "SCALAR" and input["type"] == "ID"
