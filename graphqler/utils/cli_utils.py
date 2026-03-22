from graphqler import config
from pathlib import Path


def set_auth_token_constant(auth_argument: str) -> None:
    """Sets the constants for auth token argument.
       If it has a space, it will be used as is, otherwise it will be prepended with "Bearer "

    Args:
        auth_token (str): The auth token argument
    """
    if len(auth_argument.split(" ")) >= 2:
        config.AUTHORIZATION = auth_argument
    else:
        config.AUTHORIZATION = f"Bearer {auth_argument}"


def set_idor_auth_token_constant(auth_argument: str) -> None:
    """Sets the secondary (attacker) auth token used for chain-based IDOR testing.
       If the value already contains a space (e.g. "Bearer …"), it is used as-is;
       otherwise it is prefixed with "Bearer ".

    Args:
        auth_argument (str): The secondary auth token argument
    """
    if len(auth_argument.split(" ")) >= 2:
        config.IDOR_SECONDARY_AUTH = auth_argument
    else:
        config.IDOR_SECONDARY_AUTH = f"Bearer {auth_argument}"


def is_compiled(path: str | Path) -> bool:
    """Checks if the compiled directory exists

    Args:
        path (str): The path to the compiled directory

    Returns:
        bool: True if the compiled directory exists, False otherwise
    """
    if path is None:
        return False
    path = Path(path)
    return (
        (path / config.COMPILED_DIR_NAME).exists()
        and (path / config.COMPILED_OBJECTS_FILE_NAME).exists()
        and (path / config.COMPILED_QUERIES_FILE_NAME).exists()
        and (path / config.COMPILED_MUTATIONS_FILE_NAME).exists()
        and (path / config.INTROSPECTION_RESULT_FILE_NAME).exists()
    )
