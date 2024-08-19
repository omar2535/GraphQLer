from graphqler import constants
from pathlib import Path


def set_auth_token_constant(auth_argument: str) -> None:
    """Sets the constants for auth token argument.
       If it has a space, it will be used as is, otherwise it will be prepended with "Bearer "

    Args:
        auth_token (str): The auth token argument
    """
    if len(auth_argument.split(" ")) >= 2:
        constants.AUTHORIZATION = auth_argument
    else:
        constants.AUTHORIZATION = f"Bearer {auth_argument}"


def is_compiled(path: str) -> bool:
    """Checks if the compiled directory exists

    Args:
        path (str): The path to the compiled directory

    Returns:
        bool: True if the compiled directory exists, False otherwise
    """
    path = Path(path)
    return (
        (path / constants.COMPILED_DIR_NAME).exists()
        and (path / constants.COMPILED_OBJECTS_FILE_NAME).exists()
        and (path / constants.COMPILED_QUERIES_FILE_NAME).exists()
        and (path / constants.COMPILED_MUTATIONS_FILE_NAME).exists()
        and (path / constants.INTROSPECTION_RESULT_FILE_NAME).exists()
    )
