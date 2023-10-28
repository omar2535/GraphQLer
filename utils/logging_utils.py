import logging
import constants
from pathlib import Path
from utils.singleton import singleton


# @singleton
# class Logger:
#     def __init__(self, save_path: str, mode: str = "run"):
#         """Initialize loggers

#         Args:
#             save_path (str): The path to save to
#             mode (str): The mode of the logger. Either "run" or "fuzz" or "compile"
#         """
#         if mode == "fuzz":
#             (Path(save_path) / constants.FUZZER_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
#             (Path(save_path) / constants.FENGINE_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
#         elif mode == "compile":
#             (Path(save_path) / constants.COMPILER_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
#         else:
#             (Path(save_path) / constants.COMPILER_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
#             (Path(save_path) / constants.FUZZER_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
#             (Path(save_path) / constants.FENGINE_LOG_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_logger(name: str, file_path: str) -> logging.Logger:
    """Gets a logger with the given name, file path, and level. Creates any required directories

    Args:
        name (str): The name of the logger
        file_path (str): The file path of the logged file

    Returns:
        logging.Logger: The logger returned
    """
    # create directories if they don't exist
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("[%(levelname)s][%(asctime)s][%(name)s]:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(file_path)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger
