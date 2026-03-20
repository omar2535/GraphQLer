# flake8: noqa

import json
import sys
import time
from os import path
from pathlib import Path

from graphqler.__main__ import run_compile_mode, run_fuzz_mode

from graphqler import config
import graphqler
import multiprocessing
import platform


# Dictionary specifying the API URL and path
APIS_TO_TEST = [
    ("https://countries.trevorblades.com/", "ablation-test-oob/countries-test/"),
    ("https://api.react-finland.fi/graphql", "ablation-test-oob/react-finland-test/"),
    ("https://rickandmortyapi.com/graphql", "ablation-test-oob/rick-and-morty-test/"),
    ("https://graphqlzero.almansi.me/api", "ablation-test-oob/graphql-zero-test/"),
    ("https://graphql.anilist.co/", "ablation-test-oob/anilist-test"),
    ("https://portal.ehri-project.eu/api/graphql", "ablation-test-oob/ehri-test/"),
    ("https://www.universe.com/graphql", "ablation-test-oob/universe-test"),
    ("https://beta.pokeapi.co/graphql/v1beta", "ablation-test-oob/pokeapi-test"),
    ("https://hivdb.stanford.edu/graphql", "ablation-test-oob/hivdb-test"),
    ("https://api.tcgdex.net/v2/graphql", "ablation-test-oob/tcgdex-test/"),
    # ('http://localhost:4000/graphql', 'benchmark-tests/user-wallet-test/'),
    # ("https://api.spacex.land/graphql/", "spacex-test/"),
    # ('http://localhost:4000/graphql', 'benchmark-tests/food-delivery-test/')
    # ('https://graphql.anilist.co/', 'benchmark-tests/anilist-test/'),
    # ('https://www.universe.com/graphql', 'benchmark-tests/universe-test/'),
    # ('https://beta.pokeapi.co/graphql/v1beta', 'benchmark-tests/pokeapi-test/'),
    # ('http://localhost:3000/', 'benchmark-tests/json-graphql-server/'),
]

# MAX_TIMES = [5, 10, 20, 30, 60]
MAX_TIMES = [60]
NUM_RETRIES = 1

# Set the constants
config.USE_OBJECTS_BUCKET = False
config.USE_DEPENDENCY_GRAPH = True
config.NO_DATA_COUNT_AS_SUCCESS = False
config.SKIP_DOS_ATTACKS = True
config.SKIP_MISC_ATTACKS = True
config.SKIP_INJECTION_ATTACKS = True
config.SKIP_MAXIMAL_PAYLOADS = True
config.DEBUG = False
# config.TIME_BETWEEN_REQUESTS = 0.5


def _save_run_metadata(output_path: str, api_url: str, max_time: int):
    """Save a run_metadata.json file capturing the exact configuration used for this run.

    This makes results reproducible and explains any differences between runs
    (e.g. the Table 2 vs Table 3 discrepancy is caused by different config snapshots).
    """
    metadata = {
        "graphqler_version": getattr(graphqler, "__version__", "unknown"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "api_url": api_url,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "MAX_TIME": max_time,
            "USE_OBJECTS_BUCKET": config.USE_OBJECTS_BUCKET,
            "USE_DEPENDENCY_GRAPH": config.USE_DEPENDENCY_GRAPH,
            "NO_DATA_COUNT_AS_SUCCESS": config.NO_DATA_COUNT_AS_SUCCESS,
            "SKIP_DOS_ATTACKS": config.SKIP_DOS_ATTACKS,
            "SKIP_MISC_ATTACKS": config.SKIP_MISC_ATTACKS,
            "SKIP_INJECTION_ATTACKS": config.SKIP_INJECTION_ATTACKS,
            "SKIP_MAXIMAL_PAYLOADS": config.SKIP_MAXIMAL_PAYLOADS,
        },
    }
    Path(output_path).mkdir(parents=True, exist_ok=True)
    with open(Path(output_path) / "run_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)


# Run the command multiple times
def run_api(api_to_test):
    api_name = api_to_test[1]
    api_url = api_to_test[0]
    for max_time in MAX_TIMES:
        output_path = f"{api_name}/{max_time}/"
        is_success = False
        num_tries = 0
        while is_success is False and num_tries < NUM_RETRIES:
            try:
                print(f"Running the API {api_name} with path {output_path} and max time {max_time}")
                config.MAX_TIME = max_time
                _save_run_metadata(output_path, api_url, max_time)
                run_compile_mode(output_path, api_url)
                run_fuzz_mode(output_path, api_url)
                is_success = True
            except Exception as e:
                print(e)
                num_tries += 1
                config.TIME_BETWEEN_REQUESTS = 0.1 * num_tries
                time.sleep(10 * num_tries)
        if is_success is False:
            # Getting here means the API failed to run through retries
            print(f"Error running the API {api_name} with path {output_path} and max time {max_time}")


# Run each of the APIs in parallel
if __name__ == "__main__":
    processes = []
    for api_to_test in APIS_TO_TEST:
        p = multiprocessing.Process(target=run_api, args=(api_to_test,))
        processes.append(p)
        p.start()

    for process in processes:
        process.join()
