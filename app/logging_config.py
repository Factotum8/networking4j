"""Loguru setup, shared by the FastAPI app and the CLI.

Per AGENTS.md code-style rules: every return and every if/else branch that
carries decision-making weight should be logged with context. This module
just wires up the sink/format; call sites do the actual logging.
"""

from __future__ import annotations

import sys

from loguru import logger

from app.config import settings


def configure_logging() -> None:
    """Reset loguru's default sink and install one tuned for this app."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
    logger.debug("Logging configured (level={})", settings.log_level)
