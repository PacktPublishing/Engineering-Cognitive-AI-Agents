"""Common utilities for the Winston project.

This module provides shared functionality including:
- Centralized configuration management with Config class
- MCP (Model Context Protocol) host management
- Intent database operations and queries
- Intent generation for tool discovery

All modules in this package follow Winston's core principles:
- Minimal cognitive architecture
- Trust model intelligence over orchestration
- Protocol-driven extensibility
"""

from .config import Config, initialize_config, setup_logging, config
from .mcp_host import MCPHost
from .intent_database import initialize_intent_database, query_intent_nodes
from .intent_generator import IntentGenerator

__all__ = [
    "Config",
    "initialize_config",
    "setup_logging",
    "config",
    "MCPHost",
    "initialize_intent_database",
    "query_intent_nodes",
    "IntentGenerator",
]
