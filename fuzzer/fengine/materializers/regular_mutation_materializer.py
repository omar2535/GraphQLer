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

    def materialize_output(self, output: dict, used_objects: list[str], include_name) -> str:
        """Materializes the output. Some interesting cases:
           - If we want to stop on an object materializing its fields, we need to not even include the object name
             IE: {id, firstName, user {}} should just be {id, firstName}
           Note: This function should be called on a base output type

        Args:
            output (dict): The output
            used_objects (list[str]): A list of used objects
            include_name (list[str]): Whether to include the name of the field or not

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

    def materialize_inputs(self, mutation_info, inputs: dict, objects_bucket: dict) -> str:
        """Materialize the mutation's inputs

        Args:
            mutation_info (dict): The mutation info
            objects_bucket (dict): Objects currently in the bucket

        Returns:
            str: a string of key: val, key: val, and possible more based on input object
        """
        built_str = ""
        for input_name, input_info in inputs.items():
            if input_info is None:
                return ""
            elif "kind" in input_info and input_info["kind"] == "INPUT_OBJECT":
                input_object_name = input_info["name"]
                input_object = self.input_objects[input_object_name]
                built_str += f"{input_name}: "
                built_str += self.materialize_inputs(mutation_info, input_object["inputFields"], objects_bucket)
                built_str += ", "
            elif input_info["kind"] == "NON_NULL":
                built_str += f"{input_name}: "
                oftype = input_info["ofType"]
                built_str += self.materialize_field(mutation_info, input_name, oftype, objects_bucket)
                built_str += ", "
            elif input_info["kind"] == "LIST":
                oftype = input_info["ofType"]
                built_str += f"{input_name}: "
                built_str += self.materialize_field(mutation_info, input_name, oftype, objects_bucket)
                built_str += ", "
            elif input_info["kind"] == "SCALAR":
                scalar_val = ""
                # If it's a ID that's hard depends on, then try to use from object bucket, if can't, then raise error
                # If it's an ID that's a soft depends on, then try to use from object bucket, if can't, then skip
                if input_info["type"] == "ID" and input_name in mutation_info["hardDependsOn"].keys():
                    object_name = mutation_info["hardDependsOn"][input_name]
                    if object_name in objects_bucket and len(objects_bucket[object_name] != 0):
                        grabbed_object = random.choice(objects_bucket[object_name])
                        scalar_val = grabbed_object["id"]
                    elif object_name == "UNKNOWN":
                        # If it's unknown, get a random ID from our objects bucket
                        scalar_val = get_random_id_from_bucket(objects_bucket)
                    else:
                        raise Exception("Couldn't materialize a hard depends on ID")
                elif input_info["type"] == "ID" and input_name in mutation_info["softDependsOn"].keys():
                    object_name = mutation_info["softDependsOn"][input_name]
                    if object_name in objects_bucket and len(objects_bucket[object_name] != 0):
                        grabbed_object = random.choice(objects_bucket[object_name])
                        scalar_val = grabbed_object["id"]
                    elif object_name == "UNKNOWN":
                        # If it's unknown, get a random ID from our objects bucket
                        scalar_val = get_random_id_from_bucket(objects_bucket)
                    else:
                        scalar_val = ""
                elif input_info["type"] == "String":
                    scalar_val = f"\"{get_random_scalar(input_name, input_info['type'])}\""
                else:
                    scalar_val = get_random_scalar(input_name, input_info["type"])
                built_str += f"{input_name} : {scalar_val},"
        return built_str

    def materialize_field(self, mutation_info: dict, input_name: str, field: dict, objects_bucket: dict) -> str:
        """Attempt to materialize the field

        Args:
            mutation_info (dict): The mutation info
            input_name (str): The input name (from the very top)
            field (dict): The field (has kind, name, type, ofType)
            objects_bucket (dict): The objects bucket

        Raises:
            Exception: If materialization fails

        Returns:
            str: The materialized scalar
        """
        if field["kind"] == "LIST":
            return "[" + self.materialize_field(field["ofType"]) + "]"
        elif field["kind"] == "NON_NULL":
            return self.materialize_field(field["ofType"])
        elif field["kind"] == "INPUT_OBJECT":
            input_object_name = field["name"]
            input_object = self.input_objects[input_object_name]
            return self.materialize_inputs(mutation_info, input_object["inputFields"], objects_bucket)
        elif field["kind"] == "SCALAR":
            # If it's a ID that's hard depends on, then try to use from object bucket, if can't, then raise error
            # If it's an ID that's a soft depends on, then try to use from object bucket, if can't, then skip
            if field["name"] == "ID" and input_name in mutation_info["hardDependsOn"].keys():
                object_name = mutation_info["hardDependsOn"][input_name]
                if object_name in objects_bucket and len(objects_bucket[object_name] != 0):
                    grabbed_object = random.choice(objects_bucket[object_name])
                    return grabbed_object["id"]
                elif object_name == "UNKNOWN":
                    # If it's unknown, get a random ID from our objects bucket
                    return get_random_id_from_bucket(objects_bucket)
                else:
                    raise Exception("Couldn't materialize a hard depends on ID")
            elif field["name"] == "ID" and input_name in mutation_info["softDependsOn"].keys():
                object_name = mutation_info["softDependsOn"][input_name]
                if object_name in objects_bucket and len(objects_bucket[object_name] != 0):
                    grabbed_object = random.choice(objects_bucket[object_name])
                    return grabbed_object["id"]
                elif object_name == "UNKNOWN":
                    # If it's unknown, get a random ID from our objects bucket
                    return get_random_id_from_bucket(objects_bucket)
                else:
                    return ""
            elif field["type"] == "String":
                return f"\"{get_random_scalar(input_name, field['type'])}\""
            else:
                return get_random_scalar(input_name, field["type"])
        elif field["kind"] == "ENUM":
            enum_name = field["type"]
            enums = self.enums[enum_name]
            enum_value = get_random_enum_value(enums)
            if enum_value:
                return enum_value
            else:
                return ""
        else:
            # Non-recognized kind
            return ""
