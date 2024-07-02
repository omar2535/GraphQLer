from graphqler import constants


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
