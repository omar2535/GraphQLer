# Configuration

"""For the compiler / parser"""
EXTRACTED_DIR_NAME = "extracted"
INTROSPECTION_RESULT_FILE_NAME = "introspection_result.json"
QUERY_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/query_parameter_list.yml"
MUTATION_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/mutation_parameter_list.yml"
OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/object_list.yml"
INPUT_OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/input_object_list.yml"
COMPILED_OBJECT_LIST_FILE_NAME = "compiled_object_list.yml"

"""General Graphql definitions: https://spec.graphql.org/June2018/"""
BUILT_IN_TYPES = ["ID", "Int", "Float", "String", "Boolean"]
BUILT_IN_TYPE_KINDS = ["SCALAR", "OBJECT", "INTERFACE", "UNION", "ENUM", "INPUT_OBJECT", "LIST", "NON_NULL"]


"""Toggles"""
USE_FUZZY_ID_SEARCH = True
