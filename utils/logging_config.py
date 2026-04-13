"""Structured JSON logging configuration for routing observability."""

import json
import logging
import sys
from datetime import datetime, timezone


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "structured_data"):
            log_entry.update(record.structured_data)
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
