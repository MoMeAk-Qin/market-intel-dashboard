from __future__ import annotations

import logging
import logging.config
from pathlib import Path

from .config import AppConfig


def setup_logging(config: AppConfig) -> None:
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": config.log_level,
                },
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "standard",
                    "level": config.log_level,
                    "filename": str(log_path),
                    "encoding": "utf-8",
                },
            },
            "root": {
                "level": config.log_level,
                "handlers": ["console", "file"],
            },
        }
    )
