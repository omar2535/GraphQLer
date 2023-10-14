import logging
import pathlib


def get_logger(name: str, file_path: str) -> logging.Logger:
    """Gets a logger with the given name, file path, and level. Creates any required directories

    Args:
        name (str): The name of the logger
        file_path (str): The file path of the logged file

    Returns:
        logging.Logger: The logger returned
    """
    # create directories if they don't exist
    pathlib.Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("[%(levelname)s][%(asctime)s][[%(name)s]]:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(file_path)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger
