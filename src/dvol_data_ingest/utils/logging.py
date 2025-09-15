from __future__ import annotations

import os
from pathlib import Path

from loguru import logger


def setup_logging(
    level: str | None = None,
    json: bool | None = None,
    log_file: str | None = None,
) -> None:
    """Configure Loguru logging with optional JSON output and file rotation.

    Env vars (defaults in parentheses):
    - LOG_LEVEL (INFO)
    - LOG_FORMAT (text|json) (text)
    - LOG_FILE (none)

    If a file is specified, rotation and retention are enabled.
    """

    # Remove existing handlers to avoid duplicate logs on re-config
    logger.remove()

    # Resolve level
    env_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    # Resolve format
    env_format = (os.getenv("LOG_FORMAT", None))
    use_json = json if json is not None else (env_format == "json")

    # Console sink
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=env_level,
        serialize=use_json,
        backtrace=False,
        diagnose=False,
    )

    # Optional file sink with rotation
    file_path = log_file or os.getenv("LOG_FILE")
    if file_path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(path),
            level=env_level,
            serialize=use_json,
            rotation="10 MB",
            retention="7 days",
            backtrace=False,
            diagnose=False,
        )


__all__ = ["setup_logging", "logger"]

