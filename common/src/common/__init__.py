"""Common utilities for the ECAA book project."""

from .config import get_config, setup_logging, validate_config
from .paths import get_chapter_path, get_chapter_config, clean_chapter, clean_all
from .intent_database import (
    initialize_intent_database,
    index_item,
    query_by_intent,
    index_tool,
    query_tools_by_intent,
    index_intent_node,
    query_intent_nodes,
    get_item_by_id,
    clear_collection,
    get_collection_metadata,
    save_collection_metadata,
)
from .intent_generator import IntentGenerator
from .mcp_host import MCPHost

__all__ = [
    "get_config",
    "setup_logging",
    "validate_config",
    "get_chapter_path",
    "get_chapter_config",
    "clean_chapter",
    "clean_all",
    "initialize_intent_database",
    "index_item",
    "query_by_intent",
    "index_tool",
    "query_tools_by_intent",
    "index_intent_node",
    "query_intent_nodes",
    "get_item_by_id",
    "clear_collection",
    "get_collection_metadata",
    "save_collection_metadata",
    "IntentGenerator",
    "MCPHost",
]
