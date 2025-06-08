import logging
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self, logger_type: str, stream_handler: bool = True):
        # Type = name for the logger (usually matches the module using it)
        self.logger_type = logger_type
        
        # Whether to also log to console (not just file)
        self.stream_handler = stream_handler

        # Init logger
        self.logger = self.get_logger()

        # First-time setup message
        if not self.logger_found:
            self.log(message=f'Logger {self.logger_type} was configured with {self.stream_handler} console stream')

    def get_logger(self):
        # Get logger by name (returns existing if already created)
        logger = logging.getLogger(self.logger_type)

        # If logger already has handlers → skip config
        if logger.hasHandlers():
            self.logger_found = True
            return logger

        # Otherwise, configure new logger
        logger.setLevel(logging.INFO)

        # Log file path (same as logger name)
        logger_path = f'{self.logger_type}.log'

        # File handler with rotation
        logger_handler = RotatingFileHandler(logger_path)
        logger_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(logger_handler)

        # Optional console output
        if self.stream_handler:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(stream_handler)

        # Mark this as a new logger
        self.logger_found = False

        return logger

    def log(self, message: str, level: str = "warning"):
        """
        Logs a message with given severity (info, warning, error).
        Defaults to warning if unknown level.
        """
        level_mapping = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR
        }

        self.logger.log(level_mapping.get(level, "warning"), message)
