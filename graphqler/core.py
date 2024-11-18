from graphqler.fuzzer import Fuzzer
from graphqler.compiler import Compiler
from graphqler.utils.config_handler import set_config
from graphqler.utils.stats import Stats
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.api import API

def compile_and_fuzz(path: str, url: str, input_config: dict | None = None) -> dict:
    """
    Runs the program in compile and fuzz mode.

    Args:
        path (str): Directory where all compilation outputs will be saved.
        url (str): URL of the target.
        input_config (dict, optional): A configuration dictionary with any overridden config values. Defaults to None.

    Returns:
        dict: A dictionary containing the following keys:
            - 'objects_bucket' (ObjectsBucket): The bucket of created objects. See the `ObjectsBucket` class for more details.
            - 'stats' (Stats): The stats object containing fuzzer statistics. See the `Stats` class for more details.
                - 'total_queries' (int): The total number of queries.
                - 'total_mutations' (int): The total number of mutations.
                - 'total_objects' (int): The total number of objects.
            - 'api' (API): The API object with API information. See the `API` class for more details.
                - 'queries' (dict): A dictionary of queries { query_name: query_info }.
                - 'mutations' (dict): A dictionary of mutations { mutation_name: mutation_info }.
                - 'objects' (dict): A dictionary of objects { object_name: object_info }.
                - 'input_objects' (dict): A dictionary of input objects { input_object_name: input_object_info }.
                - 'enums' (dict): A dictionary of enums { enum_name: enum_info }.
                - 'unions' (dict): A dictionary of unions { union_name: union_info }.
                - 'interfaces' (dict): A dictionary of interfaces { interface_name: interface_info }.
            - 'results' (dict): A dictionary of results { endpoint: Set(Result) }. See the `Result` class for more details.
    """
    if input_config:
        set_config(input_config)

    compiler = Compiler(path, url)
    compiler.run()

    fuzzer = Fuzzer(path, url)
    fuzzer.run()

    api: API = fuzzer.api

    objects_bucket = ObjectsBucket(api=api).load()
    stats = Stats().load()

    return {
        'objects_bucket': objects_bucket,
        'stats': stats,
        'api': fuzzer.api,
        'results': stats.results
    }
