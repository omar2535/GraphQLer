# Configuration

"""Debugging purposes"""

DEBUG = False

"""For proxy"""
PROXY = None  # Don't use this, this will be overriten by argparse

"""For any authentication tokens"""
AUTHORIZATION = None  # Don't use this, this will be overriten by argparse

"""For the compiler / parser"""
OUTPUT_DIRECTORY = "graphqler-output"
SERIALIZED_DIR_NAME = "serialized"
EXTRACTED_DIR_NAME = "extracted"
COMPILED_DIR_NAME = "compiled"
ENDPOINT_RESULTS_DIR_NAME = "endpoint_results"

INTROSPECTION_RESULT_FILE_NAME = "introspection_result.json"

"""Pickle files -- mainly for cross-process communication"""
OBJECTS_BUCKET_PICKLE_FILE_NAME = "objects_bucket.pkl"
STATS_PICKLE_FILE_NAME = "stats.pkl"

QUERY_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/query_parameter_list.yml"
MUTATION_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/mutation_parameter_list.yml"
OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/object_list.yml"
INPUT_OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/input_object_list.yml"
ENUM_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/enum_list.yml"
UNION_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/union_list.yml"
INTERFACE_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/interface_list.yml"

COMPILED_OBJECTS_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_objects.yml"
COMPILED_MUTATIONS_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_mutations.yml"
COMPILED_QUERIES_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_queries.yml"

"""For clairvoyance"""
WORDLIST_PATH = ""

"""For the resolver"""
MAX_LEVENSHTEIN_THRESHOLD = 20  # A very high threshold, we could probably lower this, but this almost guarantees us to find a matching object name - ID

"""For the linker"""
GRAPH_VISUALIZATION_OUTPUT = "dependency_graph.png"

"""General Graphql definitions: https://spec.graphql.org/October2021/"""
BUILT_IN_TYPES = ["ID", "Int", "Float", "String", "Boolean"]
BUILT_IN_TYPE_KINDS = ["SCALAR", "OBJECT", "INTERFACE", "UNION", "ENUM", "INPUT_OBJECT", "LIST", "NON_NULL"]

"""For materializers"""
MAX_OBJECT_CYCLES = 5
MAX_OUTPUT_SELECTOR_DEPTH = 5
HARD_CUTOFF_DEPTH = 20
MAX_INPUT_DEPTH = 20

"""For loggers"""
FUZZER_LOG_FILE_PATH = "logs/fuzzer.log"
COMPILER_LOG_FILE_PATH = "logs/compiler.log"
DETECTOR_LOG_FILE_PATH = "logs/detector.log"
IDOR_LOG_FILE_PATH = "logs/idor.log"

"""For stats"""
STATS_FILE_NAME = "stats.txt"
OBJECTS_BUCKET_TEXT_FILE_NAME = "objects_bucket.txt"
UNIQUE_RESPONSES_FILE_NAME = "unique_responses.txt"

"""For plugins"""
PLUGINS_PATH = f"{OUTPUT_DIRECTORY}/plugins"

"""For using GraphQLer in different modes"""
USE_OBJECTS_BUCKET = True  # This mode is for when we want to use the objects bucket
USE_DEPENDENCY_GRAPH = True  # This mode is for when we want to use DFS through the dependency graph
NO_DATA_COUNT_AS_SUCCESS = False  # This mode is for when we want to count no data in the data object as a success or failure

"""For fuzzing"""
ALLOW_DELETION_OF_OBJECTS = False  # This mode is for when we want to allow the deletion of objects from the objects bucket when coming across a DELETE mutation success
MAX_FUZZING_ITERATIONS = 5
MAX_TIME = 3600  # in seconds
SKIP_MAXIMAL_PAYLOADS = False  # This mode is for when we want to skip the maximal payloads
SKIP_DOS_ATTACKS = True  # This mode is for when we want to skip the DoS check
SKIP_INJECTION_ATTACKS = False  # This mode is for when we want to skip the injection check
SKIP_MISC_ATTACKS = False  # This mode is for when we want to skip the miscellaneous attacks

"""For each request"""
REQUEST_TIMEOUT = 120  # in seconds
TIME_BETWEEN_REQUESTS = 0.001  # in seconds

"""For custom skipping nodes"""
SKIP_NODES = []

"""For custom headers"""
CUSTOM_HEADERS = {}
