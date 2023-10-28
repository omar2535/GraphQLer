from pathlib import Path
from .singleton import singleton
from .file_utils import initialize_file

import constants
import pprint
import json


@singleton
class Stats:
    file_path = "/tmp/stats.txt"  # This gets overriden on startup
    http_status_codes = {}

    def __init__(self):
        self.http_status_codes = {}

    def add_http_status_code(self, payload_name: str, status_code: int):
        """Adds the http status code to stats

        Args:
            payload_name (str): The name of the query or mutation
            status_code (int): The status code
        """
        if status_code in self.http_status_codes:
            if payload_name in self.http_status_codes[status_code]:
                self.http_status_codes[status_code][payload_name] += 1
            else:
                self.http_status_codes[status_code][payload_name] = 1
        else:
            self.http_status_codes[status_code] = {payload_name: 1}
        self.save()

    def set_file_path(self, working_dir: str):
        initialize_file(Path(working_dir) / constants.STATS_FILE_PATH)
        self.file_path = Path(working_dir) / constants.STATS_FILE_PATH

    def save(self):
        with open(self.file_path, "w") as f:
            f.write(json.dumps(self.http_status_codes, indent=4))
