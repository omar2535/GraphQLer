import logging
from graphqler import config
from pathlib import Path
from graphqler.utils.singleton import singleton
from graphqler.utils.file_utils import initialize_file


@singleton
class Logger:
    fuzzer_logger = None
    compiler_logger = None
    detector_logger = None
    idor_logger = None
    fuzzer_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.FUZZER_LOG_FILE_PATH)
    compiler_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.COMPILER_LOG_FILE_PATH)
    detector_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.DETECTOR_LOG_FILE_PATH)
    idor_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.IDOR_LOG_FILE_PATH)

    def __init__(self):
        self.fuzzer_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.FUZZER_LOG_FILE_PATH)
        self.compiler_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.COMPILER_LOG_FILE_PATH)
        self.detector_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.DETECTOR_LOG_FILE_PATH)
        self.idor_log_path = Path(config.OUTPUT_DIRECTORY) / Path(config.IDOR_LOG_FILE_PATH)

    def get_fuzzer_logger(self) -> logging.Logger:
        """Gets the fuzzer logger. Creates the logger if it doesn't exist, and creates the log file if it doesn't exist

        Returns:
            logging.Logger: The fuzzer logger
        """
        # create the log file if it doesn't exist
        if not self.fuzzer_log_path.exists():
            self.fuzzer_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.fuzzer_log_path)

        # create the logger if it doesn't exist
        if not self.fuzzer_logger or not self.fuzzer_logger.hasHandlers():
            self.fuzzer_logger = self._get_logger("fuzzer", self.fuzzer_log_path)

        # return the logger
        return self.fuzzer_logger

    def get_detector_logger(self) -> logging.Logger:
        """Gets the detector logger. Creates the logger if it doesn't exist, and creates the log file if it doesn't exist

        Returns:
            logging.Logger: The detector logger
        """
        # create the log file if it doesn't exist
        if not self.detector_log_path.exists():
            self.detector_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.detector_log_path)

        # create the logger if it doesn't exist
        if not self.detector_logger or not self.detector_logger.hasHandlers():
            self.detector_logger = self._get_logger("detector", self.detector_log_path)

        # return the logger
        return self.detector_logger

    def get_compiler_logger(self) -> logging.Logger:
        """Gets the compiler logger. Creates the logger if it doesn't exist, and creates the log file if it doesn't exist

        Returns:
            logging.Logger: The compiler logger
        """
        # create the log file if it doesn't exist
        if not self.compiler_log_path.exists():
            self.compiler_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.compiler_log_path)

        # create the logger if it doesn't exist
        if not self.compiler_logger:
            self.compiler_logger = self._get_logger("compiler", self.compiler_log_path)

        # return the logger
        return self.compiler_logger

    def get_idor_logger(self) -> logging.Logger:
        """Gets the IDOR logger. Creates the logger if it doesn't exist, and creates the log file if it doesn't exist

        Returns:
            logging.Logger: The IDOR logger
        """
        # create the log file if it doesn't exist
        if not self.idor_log_path.exists():
            self.idor_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.idor_log_path)

        # create the logger if it doesn't exist
        if not self.idor_logger:
            self.idor_logger = self._get_logger("idor", self.idor_log_path)

        # return the logger
        return self.idor_logger

    def _get_logger(self, name: str, file_path: str | Path) -> logging.Logger:
        """Gets a logger with the given name, file path, and level. Creates any required directories

        Args:
            name (str): The name of the logger
            file_path (str): The file path of the logged file

        Returns:
            logging.Logger: The logger returned
        """
        # create directories if they don't exist
        formatter = logging.Formatter("[%(levelname)s][%(asctime)s][%(name)s]:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler = logging.FileHandler(file_path)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        if config.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        return logger
