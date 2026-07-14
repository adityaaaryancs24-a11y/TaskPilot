from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO", json_output: bool = True):
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.handlers.clear()

    if json_output:
        try:
            from pythonjsonlogger import jsonlogger

            class TaskPilotJSONFormatter(jsonlogger.JsonFormatter):
                def add_fields(
                    self,
                    log_record: dict[str, Any],
                    record: logging.LogRecord,
                    message_dict: dict[str, Any],
                ):
                    super().add_fields(log_record, record, message_dict)
                    log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
                    log_record["level"] = record.levelname
                    log_record["module"] = record.module
                    log_record["function"] = record.funcName
                    if hasattr(record, "request_id"):
                        log_record["request_id"] = record.request_id
                    if hasattr(record, "correlation_id"):
                        log_record["correlation_id"] = record.correlation_id

            formatter = TaskPilotJSONFormatter(
                "%(timestamp)s %(level)s %(module)s %(function)s %(message)s"
            )
        except ImportError:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)

    for lib in ("httpx", "httpcore", "urllib3", "sqlalchemy", "asyncio"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    return root


class CorrelationLogger:
    def __init__(self, wrapped: logging.Logger):
        self._logger = wrapped
        self._correlation_id: Optional[str] = None

    @property
    def correlation_id(self) -> Optional[str]:
        return self._correlation_id

    def set_correlation_id(self, cid: str):
        self._correlation_id = cid

    def _extra(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        extra = dict(extra or {})
        if self._correlation_id:
            extra["correlation_id"] = self._correlation_id
        return extra

    def info(self, msg: str, *args, extra: Optional[dict[str, Any]] = None, **kwargs):
        self._logger.info(msg, *args, extra=self._extra(extra), **kwargs)

    def error(self, msg: str, *args, extra: Optional[dict[str, Any]] = None, **kwargs):
        self._logger.error(msg, *args, extra=self._extra(extra), **kwargs)

    def warning(
        self, msg: str, *args, extra: Optional[dict[str, Any]] = None, **kwargs
    ):
        self._logger.warning(msg, *args, extra=self._extra(extra), **kwargs)

    def debug(self, msg: str, *args, extra: Optional[dict[str, Any]] = None, **kwargs):
        self._logger.debug(msg, *args, extra=self._extra(extra), **kwargs)

    def critical(
        self, msg: str, *args, extra: Optional[dict[str, Any]] = None, **kwargs
    ):
        self._logger.critical(msg, *args, extra=self._extra(extra), **kwargs)


correlation_logger = CorrelationLogger(logging.getLogger("taskpilot"))
