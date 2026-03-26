"""Simple singleton class to parse query listings from the introspection query"""

from .parser import Parser


class QueryListParser(Parser):
    def __init__(self):
        pass

    def __extract_arg_info(self, field):
        input_args = {}
        for arg in field:
            arg_info = {
                "name": arg["name"],
                "type": arg["type"]["name"] if "name" in arg["type"] else None,
                "kind": arg["type"]["kind"] if "kind" in arg["type"] else None,
                "ofType": self.extract_oftype(arg["type"]),
            }
            input_args[arg["name"]] = arg_info
        return input_args

    def _detect_pagination(self, query_args: dict, return_type: dict) -> dict:
        """Detect Relay-style or offset-based pagination patterns in a query.

        Inspects the input argument names and the return type to infer whether
        the query is a pagination endpoint.

        Args:
            query_args: Parsed input arguments dict (keyed by arg name).
            return_type: Parsed return-type dict with ``kind``, ``name``, and
                ``ofType`` fields.

        Returns:
            A dict with keys ``style`` (``"relay"``, ``"offset"``, or
            ``"none"``), ``cursor_arg`` (the arg name that carries the cursor,
            or ``None``), and ``size_arg`` (the page-size arg name, or ``None``).
        """
        arg_names_lower = {k.lower(): k for k in query_args}

        # Relay cursor args
        cursor_arg: str | None = None
        for relay_key in ("after", "before"):
            if relay_key in arg_names_lower:
                cursor_arg = arg_names_lower[relay_key]
                break
        if cursor_arg is None and "cursor" in arg_names_lower:
            cursor_arg = arg_names_lower["cursor"]

        # Relay size args
        size_arg: str | None = None
        for size_key in ("first", "last", "limit", "pagesize"):
            if size_key in arg_names_lower:
                size_arg = arg_names_lower[size_key]
                break

        # Offset-style args
        offset_arg: str | None = None
        for offset_key in ("offset", "page", "skip"):
            if offset_key in arg_names_lower:
                offset_arg = arg_names_lower[offset_key]
                break

        # Return-type name (unwrap NON_NULL / LIST wrappers)
        return_type_name = return_type.get("name")
        if not return_type_name:
            of_type = return_type.get("ofType")
            while isinstance(of_type, dict):
                return_type_name = of_type.get("name")
                if return_type_name:
                    break
                of_type = of_type.get("ofType")

        is_connection = bool(return_type_name and return_type_name.endswith("Connection"))

        # Classify
        is_relay = bool(cursor_arg and arg_names_lower.get("after") or arg_names_lower.get("before")) or is_connection
        is_offset = bool(offset_arg) and not is_relay

        if is_relay:
            style = "relay"
        elif is_offset:
            style = "offset"
        else:
            style = "none"

        return {
            "style": style,
            "cursor_arg": cursor_arg,
            "size_arg": size_arg,
        }

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for only objects

        Args:
            data (dict): Introspection JSON as a dictionary

        Returns:
            dict: List of objects with their types
        """
        # Grab just the objects from the dict
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        query_type_name = introspection_data.get("data", {}).get("__schema", {}).get("queryType", {}).get("name", "Query")
        queries_object = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == query_type_name]

        # No queries in the introspection
        if len(queries_object) == 0:
            return {}

        queries = queries_object[0]["fields"]

        # Convert it to the YAML structure we want
        query_info_dict = {}
        for query in queries:
            query_name = query["name"]
            query_args = self.__extract_arg_info(query["args"])
            return_type = {"kind": query["type"].get("kind"), "name": query["type"].get("name"), "ofType": self.extract_oftype(query["type"]), "type": query["type"].get("name")}

            query_info_dict[query_name] = {
                "name": query_name,
                "inputs": query_args,
                "output": return_type,
                "pagination": self._detect_pagination(query_args, return_type),
            }

        return query_info_dict
