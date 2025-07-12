"""Common configuration settings for the Winston project.

This module loads configuration from environment variables, provides access
to them, and sets up application-wide logging.
"""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
_ = load_dotenv(override=True)

# --- Core Constants ---
INTENT_DB_PERSIST_DIR: str = os.getenv("INTENT_DB_PERSIST_DIR", "chromadb_data")
INTENT_COLLECTION_NAME: str = os.getenv("INTENT_COLLECTION_NAME", "winston_intents")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
DEFAULT_MAX_PROCESSES: int = int(os.getenv("DEFAULT_MAX_PROCESSES", "5"))
INTENT_MATCH_THRESHOLD: float = float(os.getenv("INTENT_MATCH_THRESHOLD", "0.7"))
# Higher threshold for intent insertion decisions to ensure only very similar intents are merged
INTENT_INSERTION_THRESHOLD: float = float(os.getenv("INTENT_INSERTION_THRESHOLD", "0.92"))


def get_config() -> dict[str, Any]:
    """Retrieve the current configuration settings as a dictionary.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all current configuration constants.
    """
    return {
        "INTENT_DB_PERSIST_DIR": INTENT_DB_PERSIST_DIR,
        "INTENT_COLLECTION_NAME": INTENT_COLLECTION_NAME,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENAI_MODEL": OPENAI_MODEL,
        "DEFAULT_MAX_PROCESSES": DEFAULT_MAX_PROCESSES,
        "INTENT_MATCH_THRESHOLD": INTENT_MATCH_THRESHOLD,
        "INTENT_INSERTION_THRESHOLD": INTENT_INSERTION_THRESHOLD,
    }


def validate_config(config: dict[str, Any]) -> None:
    """Validate the given configuration dictionary.

    Logs warnings or errors for invalid configuration values, raising an
    exception on critical errors.

    Parameters
    ----------
    config : dict[str, Any]
        The configuration dictionary to validate.

    Raises
    ------
    ValueError
        If a critical configuration value is invalid.
    """
    persist_dir = Path(config["INTENT_DB_PERSIST_DIR"])
    if not persist_dir.exists():
        logger.warning(
            f"Intent DB persist directory '{persist_dir}' does not exist. "
            + "It will be created automatically by ChromaDB."
        )

    threshold = float(config["INTENT_MATCH_THRESHOLD"])
    if not 0.0 < threshold <= 1.0:
        msg = (
            f"Invalid intent match threshold: {threshold}. "
            + "Must be between 0 (exclusive) and 1 (inclusive)."
        )
        logger.error(msg)
        raise ValueError(msg)

    insertion_threshold = float(config["INTENT_INSERTION_THRESHOLD"])
    if not 0.0 < insertion_threshold <= 1.0:
        msg = (
            f"Invalid intent insertion threshold: {insertion_threshold}. "
            + "Must be between 0 (exclusive) and 1 (inclusive)."
        )
        logger.error(msg)
        raise ValueError(msg)


def setup_logging(log_file: Path | str | None = None) -> None:
    """Add a file handler to the global logger if a path is provided.

    This is an additive-only operation. It assumes the base logger providing
    colored console output is already configured.

    Parameters
    ----------
    log_file : Path or str, optional
        Path to the log file to add.
    """
    if log_file:
        _ = logger.add(
            log_file,
            rotation="1 week",
            diagnose=True,
            enqueue=True,
            level=os.getenv("LOGLEVEL", "DEBUG"),
            format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
            colorize=False,
        )


# validate_config(get_config())
