"""Centralized configuration management for the Winston project.

This module provides a unified configuration system that serves as the single
source of truth for all configuration values, whether from environment variables
or dynamically generated paths. The Config class supports dictionary-style
access and chapter-aware path generation.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
_ = load_dotenv(override=True)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class Config:
    """Centralized configuration manager with chapter-aware path generation.

    Provides dictionary-style access to all configuration values including
    environment variables and dynamically generated chapter-specific paths.
    Serves as the single source of truth for configuration throughout Winston.

    Parameters
    ----------
    chapter : str
        Chapter identifier (e.g., "chapter03") for path generation
    tmp_root : str, optional
        Root directory for transient state (default: "./tmp")

    Examples
    --------
    >>> config = Config("chapter03")
    >>> api_key = config["OPENAI_API_KEY"]
    >>> log_path = config["LOG_PATH"]
    >>> chapter_root = config["CHAPTER_ROOT"]
    """

    def __init__(self, chapter: str, tmp_root: str = "./tmp"):
        """Initialize configuration with chapter-specific paths.

        Parameters
        ----------
        chapter : str
            Chapter identifier for path generation
        tmp_root : str, optional
            Root directory for transient state
        """
        self.chapter = chapter
        # Convert to absolute path to ensure full paths in configuration
        self.tmp_root = Path(tmp_root).resolve()
        self._config: dict[str, Any] = {}

        # Load all configuration values
        self._load_environment_config()
        self._load_chapter_paths()

    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        self._config.update({
            "INTENT_DB_PERSIST_DIR": os.getenv("INTENT_DB_PERSIST_DIR", "chromadb_data"),
            "INTENT_COLLECTION_NAME": os.getenv("INTENT_COLLECTION_NAME", "winston_intents"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "DEFAULT_MAX_PROCESSES": int(os.getenv("DEFAULT_MAX_PROCESSES", "5")),
            "INTENT_MATCH_THRESHOLD": float(os.getenv("INTENT_MATCH_THRESHOLD", "0.7")),
            "INTENT_INSERTION_THRESHOLD": float(os.getenv("INTENT_INSERTION_THRESHOLD", "0.92")),
        })

    def _load_chapter_paths(self) -> None:
        """Generate and load chapter-specific paths."""
        chapter_root = self.tmp_root / self.chapter

        # Generate all standard facility paths
        self._config.update({
            "CHAPTER_ROOT": str(chapter_root),
            "LOG_PATH": str(chapter_root / "logs"),
            "CHROMA_PATH": str(chapter_root / "chroma_db"),
            "CACHE_PATH": str(chapter_root / "cache"),
            "DATA_PATH": str(chapter_root / "data"),
        })

    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key.

        Parameters
        ----------
        key : str
            Configuration key to retrieve

        Returns
        -------
        Any
            Configuration value

        Raises
        ------
        KeyError
            If configuration key is not found
        """
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists.

        Parameters
        ----------
        key : str
            Configuration key to check

        Returns
        -------
        bool
            True if key exists, False otherwise
        """
        return key in self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default.

        Parameters
        ----------
        key : str
            Configuration key to retrieve
        default : Any, optional
            Default value if key not found

        Returns
        -------
        Any
            Configuration value or default
        """
        return self._config.get(key, default)

    def keys(self) -> list[str]:
        """Get all configuration keys.

        Returns
        -------
        list[str]
            List of all configuration keys
        """
        return list(self._config.keys())

    def get_chapter_path(self, facility: str, create: bool = False) -> Path:
        """Get path for a specific chapter facility.

        Parameters
        ----------
        facility : str
            Facility name (e.g., "logs", "chroma_db", "cache")
        create : bool, optional
            Whether to create the directory if it doesn't exist

        Returns
        -------
        Path
            Full path to the chapter-specific facility directory
        """
        facility_path = self.tmp_root / self.chapter / facility

        if create and not facility_path.exists():
            facility_path.mkdir(parents=True, exist_ok=True)

        return facility_path

    def get_chapter_root(self, create: bool = False) -> Path:
        """Get root directory for the chapter.

        Parameters
        ----------
        create : bool, optional
            Whether to create the directory if it doesn't exist

        Returns
        -------
        Path
            Root directory for the chapter
        """
        chapter_root = self.tmp_root / self.chapter

        if create and not chapter_root.exists():
            chapter_root.mkdir(parents=True, exist_ok=True)

        return chapter_root

    def clean_chapter(self) -> None:
        """Remove all transient state for the chapter."""
        chapter_root = self.tmp_root / self.chapter
        if chapter_root.exists():
            shutil.rmtree(chapter_root)

    def validate(self) -> None:
        """Validate the configuration values.

        Raises
        ------
        ConfigurationError
            If critical configuration values are invalid
        """
        # Validate intent match threshold
        threshold = float(self._config["INTENT_MATCH_THRESHOLD"])
        if not 0.0 < threshold <= 1.0:
            raise ConfigurationError(
                f"Invalid intent match threshold: {threshold}. "
                "Must be between 0 (exclusive) and 1 (inclusive)."
            )

        # Validate intent insertion threshold
        insertion_threshold = float(self._config["INTENT_INSERTION_THRESHOLD"])
        if not 0.0 < insertion_threshold <= 1.0:
            raise ConfigurationError(
                f"Invalid intent insertion threshold: {insertion_threshold}. "
                "Must be between 0 (exclusive) and 1 (inclusive)."
            )

        # Note: Directory existence validation is intentionally omitted here
        # as directories will be created automatically when needed by ChromaDB
        # and other components. This avoids confusing warnings during initialization.


def substitute_config_variables(data: Any, config: Config) -> Any:
    """Recursively substitute ${KEY} placeholders with config values.

    Parameters
    ----------
    data : Any
        Data structure containing potential placeholders
    config : Config
        Configuration object to lookup values from

    Returns
    -------
    Any
        Data structure with placeholders substituted

    Examples
    --------
    >>> config = Config("chapter03")
    >>> data = {"path": "${CHAPTER_ROOT}/memory.json"}
    >>> result = substitute_config_variables(data, config)
    >>> result["path"]
    'tmp/chapter03/memory.json'
    """
    if isinstance(data, dict):
        return {k: substitute_config_variables(v, config) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_config_variables(item, config) for item in data]
    elif isinstance(data, str):
        # Find all ${KEY} patterns and replace them
        pattern = r'\$\{([^}]+)\}'

        def replace_var(match):
            key = match.group(1)
            if key in config:
                return str(config[key])
            else:
                logger.warning(f"Configuration key '{key}' not found for substitution")
                return match.group(0)  # Return original if not found

        return re.sub(pattern, replace_var, data)
    else:
        return data


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


# Global configuration instance - initialized by calling initialize_config()
config: Config | None = None


def initialize_config(chapter: str, tmp_root: str = "./tmp") -> Config:
    """Initialize the global configuration instance.

    This function must be called once at application startup before accessing
    the global config object.

    Parameters
    ----------
    chapter : str
        Chapter identifier for path generation
    tmp_root : str, optional
        Root directory for transient state

    Returns
    -------
    Config
        The initialized configuration instance

    Examples
    --------
    >>> from common.config import initialize_config, config
    >>> initialize_config("chapter03")
    >>> api_key = config["OPENAI_API_KEY"]
    """
    global config
    config = Config(chapter, tmp_root)
    config.validate()
    logger.info(f"Configuration initialized for {chapter}")
    return config


def get_config() -> dict[str, Any]:
    """Get configuration as dictionary for backward compatibility.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary

    Raises
    ------
    RuntimeError
        If configuration has not been initialized
    """
    if config is None:
        raise RuntimeError("Configuration not initialized. Call initialize_config() first.")

    return {
        "INTENT_DB_PERSIST_DIR": config["INTENT_DB_PERSIST_DIR"],
        "INTENT_COLLECTION_NAME": config["INTENT_COLLECTION_NAME"],
        "OPENAI_API_KEY": config["OPENAI_API_KEY"],
        "OPENAI_MODEL": config["OPENAI_MODEL"],
        "DEFAULT_MAX_PROCESSES": config["DEFAULT_MAX_PROCESSES"],
        "INTENT_MATCH_THRESHOLD": config["INTENT_MATCH_THRESHOLD"],
        "INTENT_INSERTION_THRESHOLD": config["INTENT_INSERTION_THRESHOLD"],
    }


def validate_config(config_dict: dict[str, Any]) -> None:
    """Validate configuration dictionary for backward compatibility.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to validate

    Raises
    ------
    ValueError
        If critical configuration values are invalid
    """
    if config is None:
        raise RuntimeError("Configuration not initialized. Call initialize_config() first.")

    try:
        config.validate()
    except ConfigurationError as e:
        raise ValueError(str(e)) from e


# Legacy constants for backward compatibility
# These will be deprecated once all code is migrated to use the Config class
INTENT_DB_PERSIST_DIR: str = os.getenv("INTENT_DB_PERSIST_DIR", "chromadb_data")
INTENT_COLLECTION_NAME: str = os.getenv("INTENT_COLLECTION_NAME", "winston_intents")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
DEFAULT_MAX_PROCESSES: int = int(os.getenv("DEFAULT_MAX_PROCESSES", "5"))
INTENT_MATCH_THRESHOLD: float = float(os.getenv("INTENT_MATCH_THRESHOLD", "0.7"))
INTENT_INSERTION_THRESHOLD: float = float(os.getenv("INTENT_INSERTION_THRESHOLD", "0.92"))
