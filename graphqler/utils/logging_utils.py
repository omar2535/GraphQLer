import logging
from graphqler import constants
from pathlib import Path
from graphqler.utils.singleton import singleton
from graphqler.utils.file_utils import initialize_file


@singleton
class Logger:
    fuzzer_logger = None
    compiler_logger = None
    fuzzer_log_path = ""
    compiler_log_path = ""

    def __init__(self):
        pass

    def initialize_loggers(self, mode: str, save_path: str):
        """Initialize logger paths

        Args:
            mode (str): Mode of run
            save_path (str): Save path
        """
        self.fuzzer_log_path = Path(save_path) / constants.FUZZER_LOG_FILE_PATH
        self.compiler_log_path = Path(save_path) / constants.COMPILER_LOG_FILE_PATH
        self.idor_log_path = Path(save_path) / constants.IDOR_LOG_FILE_PATH
        if mode == "fuzz":
            self.fuzzer_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.fuzzer_log_path)
        elif mode == "compile":
            self.compiler_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.compiler_log_path)
        elif mode == "idor":
            self.fuzzer_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.idor_log_path)
        else:
            self.fuzzer_log_path.parent.mkdir(parents=True, exist_ok=True)
            self.compiler_log_path.parent.mkdir(parents=True, exist_ok=True)
            initialize_file(self.fuzzer_log_path)
            initialize_file(self.compiler_log_path)

        self.fuzzer_logger = self._get_logger("fuzzer", self.fuzzer_log_path)
        self.compiler_logger = self._get_logger("compiler", self.compiler_log_path)
        self.idor_logger = self._get_logger("idor", self.idor_log_path)

    def get_fuzzer_logger(self) -> logging.Logger:
        """Gets the fuzzer logger

        Returns:
            logging.Logger: The fuzzer logger
        """
        if not self.fuzzer_logger:
            self.fuzzer_logger = self._get_logger("fuzzer", self.fuzzer_log_path)
        return self.fuzzer_logger

    def get_compiler_logger(self) -> logging.Logger:
        """Gets the compiler logger

        Returns:
            logging.Logger: The compiler logger
        """
        if not self.compiler_logger:
            self.compiler_logger = self._get_logger("compiler", self.compiler_log_path)
        return self.compiler_logger

    def get_idor_logger(self) -> logging.Logger:
        """Gets the IDOR logger

        Returns:
            logging.Logger: The IDOR logger
        """
        if not self.idor_logger:
            self.idor_logger = self._get_logger("idor", self.idor_log_path)
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
        if constants.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        return logger
