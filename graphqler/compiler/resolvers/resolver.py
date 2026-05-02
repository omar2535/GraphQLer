import re

from .utils import find_closest_string, strip_crud_prefix
from graphqler.utils.parser_utils import get_base_oftype

# Used only in the name-based fallback when no operation output type is available.
_BY_IDS_SUFFIX_RE = re.compile(r"byids?$", re.IGNORECASE)


class Resolver:
    def __init__(self):
        pass

    def _resolve_object_type_from_output(self, operation: dict, objects: dict) -> str:
        """Extracts the base OBJECT type name from an operation's output, or returns "".

        Strips any NON_NULL / LIST wrappers so that outputs typed as
        ``Character``, ``[Character]``, ``Character!`` or ``[Character!]!``
        all resolve to ``"Character"``.

        Used to infer ID-input dependencies from the operation's return type
        rather than from endpoint-name heuristics.

        Args:
            operation (dict): A compiled query or mutation dict (must have an ``output`` key)
            objects (dict): All compiled objects from the schema

        Returns:
            str: A known OBJECT type name, or "" if the output doesn't resolve to one
        """
        output = operation.get("output", {})
        # The top-level output may have its own ofType (NON_NULL / LIST wrapper)
        candidate = get_base_oftype(output.get("ofType") or output)
        if candidate.get("kind") != "OBJECT":
            return ""
        type_name = candidate.get("type") or candidate.get("name") or ""
        return type_name if type_name in objects else ""

    def _resolve_produces(self, operation: dict, objects: dict) -> str:
        """Returns the inner object type produced by a list/connection output, or empty string.

        A query or mutation "produces" an inner type when its direct output type is a
        connection/wrapper object (e.g. CountryConnection, Characters) that contains a
        list field whose base element type is a known OBJECT.

        Well-known list field names (checked in priority order):
        ``items``, ``nodes``, ``edges``, ``results``.
        For Relay-style ``edges`` fields the resolution descends one extra level through
        the edge type's ``node`` field to return the actual domain object type.
        If none of the well-known names match, any LIST-of-OBJECT field in the wrapper
        is used as a fallback (handles non-standard names such as ``data``).

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

        # Well-known list field names (checked first, in priority order).
        # "edges" is Relay-style and requires an extra unwrap through the edge's "node" field.
        preferred_keys = ("items", "nodes", "edges", "results")

        def _try_field(field: dict) -> str:
            oftype = field.get("ofType")
            if not oftype:
                return ""
            inner_base = get_base_oftype(oftype)
            if inner_base.get("kind") != "OBJECT":
                return ""
            inner_type = inner_base.get("type") or inner_base.get("name") or ""
            if not inner_type or inner_type not in objects:
                return ""
            if field["name"] == "edges":
                return self._resolve_node_type(inner_type, objects) or inner_type
            return inner_type

        fallback_field: dict | None = None
        for field in objects[outer_type_name].get("fields", []):
            if field["name"] in preferred_keys:
                result = _try_field(field)
                if result:
                    return result
            elif field.get("kind") == "LIST" and fallback_field is None:
                # Auto-discover: any LIST field of an OBJECT type can serve as the
                # items list for schemas that use non-standard names (e.g. "data").
                oftype = field.get("ofType")
                if oftype and get_base_oftype(oftype).get("kind") == "OBJECT":
                    fallback_field = field

        if fallback_field is not None:
            return _try_field(fallback_field)

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

    def resolve_inputs_related_to_ids_to_objects(self, endpoint_name: str, inputs_related_to_ids: dict, objects: dict, operation: dict | None = None) -> dict:
        """Resolves inputs related to IDs to their dependent object types.

        For bare ``id`` / ``ids`` inputs the resolution strategy is:

        1. **Output-type inference** (preferred): inspect the operation's return type.
           ``charactersByIds(ids: [ID!]!) → [Character]`` resolves directly to
           ``Character`` regardless of how the endpoint is named.
        2. **Name-based heuristic** (fallback): strip CRUD prefix and match
           against known object names via Levenshtein distance.  For compound
           inputs such as ``userId`` the object name is derived by removing the
           trailing ``id``/``ids`` suffix from the input name.

        Args:
            endpoint_name (str): The name of the query or mutation for these inputs
            inputs_related_to_ids (dict): Maps input name → required (True = NON_NULL)
            objects (dict): All the possible objects for this API
            operation (dict | None): The full compiled operation dict; when provided
                the output type is used as the primary signal for bare ``id``/``ids`` inputs.

        Returns:
            dict: Input parameters to the objects and the required / not required mappings
        """
        input_id_object_mapping = {"hardDependsOn": {}, "softDependsOn": {}}

        for input_name, required in inputs_related_to_ids.items():
            # Get the object's name
            object_name = input_name
            if input_name.lower() in ("id", "ids"):
                # Prefer output-type inference: the operation's return type directly
                # tells us which object these IDs belong to, without any name matching.
                guessed_object_name = self._resolve_object_type_from_output(operation, objects) if operation else ""
                # Fall back to endpoint-name matching when output type is unavailable.
                # For "ids" strip a "ByIds" suffix first so that "charactersByIds" →
                # "characters" → "character" → "Character" rather than "Characters".
                if not guessed_object_name:
                    if input_name.lower() == "ids":
                        endpoint_base = _BY_IDS_SUFFIX_RE.sub("", strip_crud_prefix(endpoint_name))
                        singular_base = endpoint_base[:-1] if endpoint_base.lower().endswith("s") else endpoint_base
                        guessed_object_name = find_closest_string(list(objects.keys()), singular_base)
                        if not guessed_object_name:
                            guessed_object_name = find_closest_string(list(objects.keys()), endpoint_base)
                    else:
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
