"""This module contains utility functions for stats files."""


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
