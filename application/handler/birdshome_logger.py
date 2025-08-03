import logging, os
import os.path
from logging.handlers import RotatingFileHandler


class BirdshomeLogger(logging.Logger):

    def __init__(self, name: str, level: int, location: str, logformat: str):
        super().__init__(name, level)
        log_location = os.path.join(location,name+'.log')
        logger_handler = RotatingFileHandler(filename=log_location, maxBytes=100000, backupCount=10)
        log_formater = logging.Formatter(logformat)
        logger_handler.setFormatter(log_formater)
        self.addHandler(logger_handler)