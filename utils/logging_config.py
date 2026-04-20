"""Structured JSON logging configuration for routing observability."""

import json
import logging
import sys
from datetime import datetime, timezone


_RESERVED_LOG_FIELDS = {"timestamp", "level", "logger", "message", "exception"}


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON.

    - Includes exception traceback when ``exc_info`` is set.
    - Merges ``record.structured_data`` without overwriting reserved fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        structured = getattr(record, "structured_data", None)
        if isinstance(structured, dict):
            for key, value in structured.items():
                if key in _RESERVED_LOG_FIELDS:
                    # Don't let custom payloads silently overwrite core fields.
                    log_entry[f"data_{key}"] = value
                else:
                    log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return a structured JSON logger for routing events."""
    logger = logging.getLogger("routing_observability")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def log_routing_decision(
    logger: logging.Logger,
    *,
    query: str,
    selected_agent: str,
    reason: str,
    confidence: float,
    alternatives_considered: list[str] | None = None,
    override_applied: bool = False,
) -> None:
    """Emit a structured routing_decision log event."""
    data = {
        "event": "routing_decision",
        "query": query,
        "selected_agent": selected_agent,
        "reason": reason,
        "confidence": confidence,
        "alternatives_considered": alternatives_considered or [],
        "override_applied": override_applied,
    }
    logger.info(
        "routing_decision",
        extra={"structured_data": data},
    )


def log_self_reflection(
    logger: logging.Logger,
    *,
    query: str,
    agent: str,
    kb_results_count: int,
    reflection: dict,
    action: str = "KEEP",
    final_agent: str | None = None,
) -> None:
    """Emit a structured self_reflection log event."""
    data = {
        "event": "self_reflection",
        "query": query,
        "agent": agent,
        "kb_results_count": kb_results_count,
        "reflection": reflection,
        "action": action,
        "final_agent": final_agent or agent,
    }
    logger.info(
        "self_reflection",
        extra={"structured_data": data},
    )
