import logging
import sys
from typing import Optional

class LoggerClient:
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(self.level)

        if not self.logger.handlers:
            # Console Handler
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(self.level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def get(self) -> logging.Logger:
        return self.logger
