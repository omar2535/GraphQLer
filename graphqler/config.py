# Configuration

"""Debugging purposes"""
DEBUG: bool = False

"""For proxy"""
PROXY: str | None = None  # Don't use this, this will be overriten by argparse

"""For any authentication tokens"""
AUTHORIZATION: str | None = None  # Don't use this, this will be overriten by argparse

"""For the compiler / parser"""
OUTPUT_DIRECTORY: str = "graphqler-output"
SERIALIZED_DIR_NAME = "serialized"
EXTRACTED_DIR_NAME = "extracted"
COMPILED_DIR_NAME = "compiled"
EVAL_DIR_NAME = "eval"
ENDPOINT_RESULTS_DIR_NAME = "endpoint_results"
DETECTIONS_DIR_NAME = "detections"

INTROSPECTION_RESULT_FILE_NAME = "introspection_result.json"
CONFIG_FILE_NAME = "config.toml"

"""Pickle files -- mainly for cross-process communication"""
OBJECTS_BUCKET_PICKLE_FILE_NAME = "objects_bucket.pkl"
STATS_PICKLE_FILE_NAME = "stats.pkl"

QUERY_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/query_parameter_list.yml"
MUTATION_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/mutation_parameter_list.yml"
SUBSCRIPTION_PARAMETER_FILE_NAME = f"{EXTRACTED_DIR_NAME}/subscription_parameter_list.yml"
OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/object_list.yml"
INPUT_OBJECT_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/input_object_list.yml"
ENUM_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/enum_list.yml"
UNION_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/union_list.yml"
INTERFACE_LIST_FILE_NAME = f"{EXTRACTED_DIR_NAME}/interface_list.yml"

COMPILED_OBJECTS_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_objects.yml"
COMPILED_MUTATIONS_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_mutations.yml"
COMPILED_QUERIES_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_queries.yml"
COMPILED_SUBSCRIPTIONS_FILE_NAME = f"{COMPILED_DIR_NAME}/compiled_subscriptions.yml"
CHAINS_DIR_NAME = f"{COMPILED_DIR_NAME}/chains"

"""For clairvoyance"""
WORDLIST_PATH = ""

"""For the resolver"""
MAX_LEVENSHTEIN_THRESHOLD = 20  # A very high threshold, we could probably lower this, but this almost guarantees us to find a matching object name - ID

"""For the LLM-based resolver (opt-in alternative to the classic ID-based resolver)
Model string uses litellm format:
  OpenAI:    "gpt-4o-mini"  (set LLM_API_KEY or OPENAI_API_KEY env var)
  Anthropic: "anthropic/claude-3-5-haiku-20241022"  (set LLM_API_KEY or ANTHROPIC_API_KEY env var)
  Ollama:    "ollama/llama3"  (set LLM_BASE_URL to "http://localhost:11434")
  LiteLLM proxy: "openai/my-model"  (set LLM_BASE_URL to your proxy URL)
"""
USE_LLM: bool = False                         # Master toggle: use LLM for dependency graph inference, endpoint classification, and IDOR chain classification
LLM_MODEL: str = "gpt-4o-mini"              # litellm model string (encodes provider + model)
LLM_API_KEY: str = ""                        # API key; if empty, reads from env (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
LLM_BASE_URL: str = ""                       # Custom base URL (required for Ollama and LiteLLM proxies)
LLM_RESOLVER_FALLBACK_TO_ID: bool = True      # Fall back to classic ID-based resolver if LLM call fails
LLM_RESOLVER_SAVE_COMPARISON: bool = True     # Save a side-by-side comparison JSON of LLM vs classic results
LLM_MAX_RETRIES: int = 2                     # How many times to retry when the LLM returns non-JSON
LLM_ENABLE_REPORTER: bool = False             # Independent toggle: generate an LLM vulnerability report at end of fuzzing (requires USE_LLM=True)
LLM_REPORT_FILE_NAME: str = "report.md"     # Output filename for the LLM-generated report

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
USE_OBJECTS_BUCKET: bool = True  # This mode is for when we want to use the objects bucket
USE_DEPENDENCY_GRAPH: bool = True  # This mode is for when we want to use DFS through the dependency graph
NO_DATA_COUNT_AS_SUCCESS: bool = False  # This mode is for when we want to count no data in the data object as a success or failure
DISABLE_MUTATIONS: bool = False  # When True, only Query chains are generated — all Mutation nodes are excluded from fuzzing

"""For fuzzing"""
ALLOW_DELETION_OF_OBJECTS: bool = False  # This mode is for when we want to allow the deletion of objects from the objects bucket when coming across a DELETE mutation success
MAX_FUZZING_ITERATIONS: int = 1  # Number of complete sweeps through all chains; increase for more coverage depth
MAX_TIME: int = 3600  # in seconds
SKIP_MAXIMAL_PAYLOADS: bool = False  # This mode is for when we want to skip the maximal payloads
SKIP_DOS_ATTACKS: bool = True  # This mode is for when we want to skip the DoS check
SKIP_INJECTION_ATTACKS: bool = False  # This mode is for when we want to skip the injection check
SKIP_MISC_ATTACKS: bool = False  # This mode is for when we want to skip the miscellaneous attacks
SKIP_SUBSCRIPTIONS: bool = True  # Subscriptions require WebSocket transport; disabled by default (opt-in with --subscriptions)
SUBSCRIPTION_TIMEOUT: int = 5  # Seconds to wait for events when executing a subscription
SUBSCRIPTION_PROTOCOL: str = "graphql-ws"  # WebSocket sub-protocol: "graphql-ws" (modern) or "subscriptions-transport-ws" (legacy Apollo)

"""For NoSQL blind extraction"""
NOSQLI_BLIND_EXTRACTION: bool = False  # When True, attempt char-by-char data extraction after a potential NoSQLi is detected
NOSQLI_EXTRACTION_CHARSET: str = "0123456789abcdef-"  # Charset to iterate during blind extraction (default covers hex IDs)
NOSQLI_MAX_EXTRACTION_LENGTH: int = 64  # Maximum number of characters to extract before stopping

"""For time-based SQL blind injection"""
TIME_BASED_SQL_SLEEP_SECONDS = 3  # Seconds to sleep in time-based SQL payloads (pg_sleep / SLEEP / WAITFOR)
TIME_BASED_SQL_THRESHOLD_RATIO = 0.8  # Response time >= sleep * ratio is treated as confirmed time-based SQLi

"""For field charset fuzzing and ID enumeration (GraphQLMap GRAPHQL_CHARSET / GRAPHQL_INCREMENT equivalent)"""
SKIP_ENUMERATION_ATTACKS: bool = True  # Disabled by default (sends many requests per node — opt-in)
# Charset used for field-level enumeration fuzzing (printable ASCII minus obvious injection chars)
FIELD_CHARSET: str = "0123456789abcdefghijklmnopqrstuvwxyz"
MAX_CHARSET_FUZZ_FIELDS: int = 3  # Max string fields to fuzz per node
FIELD_RESPONSE_LENGTH_VARIANCE_THRESHOLD = 0.5  # Flag if (max-min)/avg response length exceeds this ratio (raised from 0.2 to reduce FPs; paired with near-empty fraction check in detector)
# ID / integer enumeration (IDOR detection)
ID_ENUMERATION_COUNT: int = 10  # Number of integer IDs to probe (1 .. N)
ID_ENUMERATION_SUCCESS_THRESHOLD = 2  # Min distinct IDs that must return data to flag IDOR
ID_ENUMERATION_SCOPE_HEURISTIC: bool = True  # Classify endpoint scope (private/public) before running enumeration; skip public endpoints to avoid false positives

"""For each request"""
REQUEST_TIMEOUT: int = 120  # in seconds
TIME_BETWEEN_REQUESTS: float = 0.001  # in seconds

"""For custom skipping nodes"""
SKIP_NODES = []

"""For custom headers"""
CUSTOM_HEADERS = {}

"""For chain-based IDOR detection (cross-user access testing)"""
IDOR_SECONDARY_AUTH: str | None = None              # Attacker/secondary auth token (e.g. "Bearer token2"); if None, chain-based IDOR phase is skipped
SKIP_IDOR_CHAIN_FUZZING: bool = False         # Set True to disable the chain-based IDOR phase entirely
IDOR_HEURISTIC_CONFIDENCE_THRESHOLD: float = 0.5  # Chains scoring below this trigger LLM fallback (when enabled)
IDOR_USE_LLM_FALLBACK: bool = False           # When True, use LLM classifier for low-confidence chains

"""For chain-based UAF detection (use-after-delete / use-after-free testing)"""
SKIP_UAF_CHAIN_FUZZING: bool = False          # Set True to disable the chain-based UAF phase entirely
UAF_HEURISTIC_CONFIDENCE_THRESHOLD: float = 0.5  # Chains scoring below this trigger LLM fallback (when enabled)
UAF_USE_LLM_FALLBACK: bool = False            # When True, use LLM classifier for low-confidence chains

"""For arbitrary runtime profiles (multi-auth, custom headers, etc.)"""
PROFILES = {}

# TUI-only: last URL entered in the TUI (not persisted to config.toml, not used by CLI)
TUI_LAST_URL: str = ""

# TUI-only: when True the fuzzer must use threads (not multiprocessing) so that
# callbacks and log capture work inside the Textual event loop.  Set by the TUI
# at startup; never written to config.toml and never read by the CLI.
TUI_MODE: bool = False
