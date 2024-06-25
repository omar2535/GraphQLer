"""Insecure direct object reference fuzzer"""

from fuzzer.fuzzer import Fuzzer


class IDORFuzzer(Fuzzer):
    def __init__(self, path: str, url: str, objects_bucket: dict):
        """Iniitializes the IDOR fuzzer

        Args:
            path (str): The path to save the IDOR fuzzer
            url (str): The URL
            objects_bucket (dict): The objects bucket from a previous run
        """
        super().__init__(path, url)
        self.objects_bucket = objects_bucket

    def run(self):
        """Runs the fuzzer"""
        print("(F) Running IDOR fuzzer")
        print("(F) Finished IDOR fuzzer")
