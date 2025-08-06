import sys
import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rich": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "rich",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,  # 👈 ensures use of stdout not stderr
        },
    },
    "root": {"level": "DEBUG", "handlers": ["default"]},
}

dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("ai-news-platform")
