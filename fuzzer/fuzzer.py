"""Class for fuzzer

Fuzzer actually does 2 things:
0. Serializes the YAML files into built-in types for easier use when fuzzing
1. Creates the object-dependency graph for fuzzing
2. Run the actual fuzzing
"""

from graph import GraphGenerator


class Fuzzer:
    def __init__(self, save_path: str, url: str):
        """Initializes the fuzzer, reading information from the compiled files

        Args:
            save_path (str): Save directory path
            url (str): URL for graphql introspection query to hit
        """
        self.save_path = save_path
        self.url = url

    def run(self):
        pass
