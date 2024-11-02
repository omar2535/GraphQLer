from Levenshtein import distance
from graphqler.config import MAX_LEVENSHTEIN_THRESHOLD


def find_closest_string_leveshtein(strings: list[str], target: str, threshold: float) -> str:
    """Finds the closest string to the target string given a threshold. If none are found, returns ""

    Args:
        strings (list[str]): The list of strings to search for
        target (str): The target string to search for
        threshold (float): The treshold value

    Returns:
        str: Returns a string if it's within the threshold, otherwise returns ""
    """
    closest_distance = threshold + 1
    closest_string = ""
    for string in strings:
        dist = distance(string, target)
        if dist <= threshold and dist < closest_distance:
            closest_distance = dist
            closest_string = string
    return closest_string


def find_closest_string(strings: list[str], target: str) -> str:
    """Finds the closest string to the target string

    Args:
        strings (list[str]): The list of strings (in our case, object names)
        target (str): The target (in our case, either the field name or the query/mutation name)

    Returns:
        str: The found matching string, or "" if nothing close is found
    """
    # Do some pre-procssing first (remove underscores, lowercase)
    target = target.lower().replace("_", "")
    lookup = {}
    for string in strings:
        lookup[string.lower().replace("_", "")] = string

    found_similar_strings = []
    for normalized_string, string in lookup.items():
        if normalized_string in target:
            found_similar_strings.append(string)
    if len(found_similar_strings) == 0:
        return ""
    closest_string = find_closest_string_leveshtein(found_similar_strings, target, MAX_LEVENSHTEIN_THRESHOLD)
    return closest_string
