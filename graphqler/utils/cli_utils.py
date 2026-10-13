from graphqler import config
from pathlib import Path
from graphqler.utils.artifact_manifest import ArtifactValidationError, validate_manifest


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
    from graphqler.utils.request_utils import reset_session

    reset_session()


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
    from graphqler.utils.request_utils import reset_session

    reset_session()


def is_compiled(path: str | Path) -> bool:
    """Return whether a compatible, complete artifact set exists."""
    if path is None:
        return False
    settings = config.snapshot()
    try:
        validate_manifest(path, "chains", settings)
    except (ArtifactValidationError, OSError):
        return False
    return True
