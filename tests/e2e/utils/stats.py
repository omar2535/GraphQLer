"""This module contains utility functions for stats files."""

import json
import os


def get_vulnerabilities_from_stats(stats_dir: str) -> dict:
    """Reads the vulnerabilities dict from the JSON stats report.

    Args:
        stats_dir (str): Directory where stats files are saved.

    Returns:
        dict: vulnerabilities mapping as written by Stats.save_json(), or {} if not found.
    """
    json_path = os.path.join(stats_dir, "stats.json")
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r") as f:
        data = json.load(f)
    return data.get("vulnerabilities", {})


def is_detection_flagged(vulnerabilities: dict, detection_name: str, confirmed: bool = False) -> bool:
    """Returns True if any node was flagged for the given detection.

    Args:
        vulnerabilities (dict): The vulnerabilities dict from get_vulnerabilities_from_stats().
        detection_name (str): The DETECTION_NAME string used by the detector.
        confirmed (bool): If True, only count confirmed vulnerabilities; otherwise include potential.

    Returns:
        bool: True if at least one node was flagged.
    """
    if detection_name not in vulnerabilities:
        return False
    for _node_name, vuln in vulnerabilities[detection_name].items():
        if confirmed and vuln.get("is_vulnerable"):
            return True
        if not confirmed and (vuln.get("is_vulnerable") or vuln.get("potentially_vulnerable")):
            return True
    return False


def get_percent_query_mutation_success(stats_file_path: str) -> float:
    """Gets the percentage of successful queries and mutations from the stats file.

    Args:
        stats_file_path (str): The path to the stats file.

    Returns:
        float: The percentage of successful queries and mutations up to 2 decimal points
    """
    with open(stats_file_path, "r") as stats_file:
        lines = stats_file.readlines()

        for line in lines:
            if "Number of unique query/mutation successes" in line:
                line = line.strip().split(":")
                fraction_str_split = line[1].strip().split("/")
                numerator = int(fraction_str_split[0])
                denominator = int(fraction_str_split[1])
                return round(float(numerator / denominator) * 100, 2)
