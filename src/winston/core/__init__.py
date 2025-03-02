"""Core module initialization with logging configuration."""

import sys
from pathlib import Path

from loguru import logger

# Remove default logger
logger.remove()

# Add console logging
logger.add(
  sys.stderr,
  level="INFO",
  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Add file logging
logger.add(
  logs_dir / "winston.log",
  rotation="10 MB",  # Rotate when file reaches 10 MB
  retention="1 month",  # Keep logs for 1 month
  compression="zip",  # Compress rotated logs
  level="DEBUG",  # Log debug and higher levels to file
  format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
  backtrace=True,  # Include backtrace in error logs
  diagnose=True,  # Include variables in error logs
)

# Log startup information
logger.info(
  "Winston core module initialized with file logging"
)
