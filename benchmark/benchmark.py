# flake8: noqa

import sys
from os import path

from graphqler.__main__ import run_compile_mode, run_fuzz_mode

from graphqler import constants
import multiprocessing


# Dictionary specifying the API URL and path
APIS_TO__TEST = [
    # ("https://countries.trevorblades.com/", "countries-test/"),
    # ("https://api.react-finland.fi/graphql", "react-finland-test/"),
    # ("https://rickandmortyapi.com/graphql", "rick-and-morty-test/"),
    # ("https://graphqlzero.almansi.me/api", "graphql-zero-test/"),
    # ("https://graphql.anilist.co/", "anilist-test"),
    # ("https://portal.ehri-project.eu/api/graphql", "ehri-test/"),
    # ("https://www.universe.com/graphql", "universe-test"),
    # ("https://beta.pokeapi.co/graphql/v1beta", "pokeapi-test"),
    # ("https://hivdb.stanford.edu/graphql", "hivdb-test"),
    # ("https://api.spacex.land/graphql/", "spacex-test/"),
    # ("https://api.tcgdex.net/v2/graphql", "tcgdex-test/"),
]

MAX_TIMES = [5, 10, 20, 30, 60]

# Set the constants
constants.USE_OBJECTS_BUCKET = True
constants.USE_DEPENDENCY_GRAPH = True
constants.NO_DATA_COUNT_AS_SUCCESS = True


# Run the command multiple times
def run_api(api_to_test):
    for max_time in MAX_TIMES:
        output_path = f"{api_to_test[1]}/{max_time}/"
        print(f"Running the API {api_to_test[0]} with path {output_path} and max time {max_time}")
        constants.MAX_TIME = max_time
        run_compile_mode(output_path, api_to_test[0])
        run_fuzz_mode(output_path, api_to_test[0])


# Run each of the APIs in parallel
if __name__ == "__main__":
    processes = []
    for api_to_test in APIS_TO__TEST:
        p = multiprocessing.Process(target=run_api, args=(api_to_test,))
        processes.append(p)
        p.start()

    for process in processes:
        process.join()
