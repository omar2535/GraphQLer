# Configuration

"""For the compiler / parser"""
RAW_INTROSPECTION_FILE_NAME = "introspection.json"
INTROSPECTION_RESULT_FILE_NAME = "introspection_result.json"
SCHEMA_FILE_NAME = "schema.json"
FUNCTION_LIST_FILE_NAME = "mutation_function_list.yml"
QUERY_PARAMETER_FILE_NAME = "query_parameter_list.yml"
MUTATION_PARAMETER_FILE_NAME = "mutation_parameter_list.yml"
OBJECT_LIST_FILE_NAME = "object_list.yml"

"""General Graphql definitions: https://spec.graphql.org/June2018/"""
BUILT_IN_TYPES = ["ID", "Int", "Float", "String", "Boolean"]

BUILT_IN_TYPE_KINDS = ["SCALAR", "OBJECT", "INTERFACE", "UNION", "ENUM", "INPUT_OBJECT", "LIST", "NON_NULL"]
