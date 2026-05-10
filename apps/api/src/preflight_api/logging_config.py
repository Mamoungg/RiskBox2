import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


def configure_logging(service: str = "api") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "ts"},
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    return kwargs
