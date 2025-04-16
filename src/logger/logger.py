import logging
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self, logger_type: str, stream_handler: bool = True):
        self.logger_type = logger_type
        self.stream_handler = stream_handler
        
        self.logger = self.get_logger()

        if not self.logger_found:
            self.log(message=f'Logger {self.logger_type} was configured with {self.stream_handler} console stream')

    def get_logger(self):
        logger = logging.getLogger(self.logger_type)

        if logger.hasHandlers():
            self.logger_found = True
            return logger

        logger.setLevel(logging.INFO)

        logger_path = f'{self.logger_type}.log'
        logger_handler = RotatingFileHandler(logger_path)
        logger_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

        logger.addHandler(logger_handler)

        if self.stream_handler:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

            logger.addHandler(stream_handler)

        self.logger_found = False

        return logger

    def log(self, message: str, level: str = "warning"):
        """
        Logging method with color adjustments and file logging
        """

        level_mapping = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR
        }

        self.logger.log(level_mapping.get(level, "warning"), message)

