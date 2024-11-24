import logging
import logging.config
from typing_extensions import Any
from datetime import datetime
from pythonjsonlogger import jsonlogger

from takehome.config import settings

class LoggingContext:
    """
    A class for managing a logging context.

    Attributes:
        store (dict): A dictionary to store logging context key-value pairs.
    """
    def __init__(self, **kwargs: Any) -> 'LoggingContext':
        """
        Initializes a LoggingContext instance.

        Args:
            self,
            **kwargs: Key-value pairs to populate the logging context store.

        Returns:
            LoggingContext instance
        """

        self.store: dict = {}

        for key, value in kwargs.items():
            self.store[key] = value

    def upsert(self, **kwargs: Any) -> None:
        """
        Adds or updates key-value pairs in the logging context store.

        Args:
            self,
            **kwargs: Key-value pairs to add or update.

        Returns:
            None

        Raises:
            ValueError: If self.store does not exist/ is empty.
            TypeError: If self.store is not a dictionary.
        """

        if not self.store:
            raise ValueError("Logging context store not found to be initialized")
        
        if not isinstance(self.store, dict):
            raise TypeError("Logging context store not found to be a dictionary")

        for key, value in kwargs.items():
            self.store[key] = value

    def remove_keys(self, keys) -> None:
        """
        Removes specified keys from the logging context store.

        Args:
            self,
            keys (List[str]): List of keys to remove.

        Returns:
            None

        Raises:
            ValueError: If self.store does not exist/ is empty.
            TypeError: If self.store is not a dictionary.
        """

        if not self.store:
            raise ValueError("Logging context store not found to be initialized")
        
        if not isinstance(self.store, dict):
            raise TypeError("Logging context store not found to be a dictionary")

        for key in keys:
            if key in self.store:
                del self.store[key]

    def clear(self) -> None:
        """
        Clears the current logging context store.

        Args:
            self

        Returns:
            None

        Raises:
            ValueError: If self.store does not exist/ is empty.
            TypeError: If self.store is not a dictionary.
        """

        if not self.store:
            raise ValueError("Logging context store not found to be initialized")
        
        if not isinstance(self.store, dict):
            raise TypeError("Logging context store not found to be a dictionary")
        
        self.store.clear()

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['Simplify_server'] = True

        if not log_record.get('emission_timestamp'):
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['emission_timestamp'] = now

        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        log_record['message'] = record.message


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": CustomJsonFormatter,
            "format": "%(emission_timestamp)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.CONSOLE_LOG_LEVEL,
            "formatter": "json",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console"],
            "level": settings.CONSOLE_LOG_LEVEL,
            "propagate": False
        }
    }
}

def fetch_logger():
    logging.config.dictConfig(LOGGING_CONFIG)

    _logger = logging.getLogger(__name__)
    _logger.setLevel(settings.CONSOLE_LOG_LEVEL)

    # Console Stream logger
    console_handler = logging.StreamHandler()
    _logger.addHandler(console_handler)

    return _logger

LOGGER = fetch_logger()
