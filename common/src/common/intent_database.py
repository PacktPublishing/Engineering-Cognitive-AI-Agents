#!/usr/bin/env python3
"""Winston Intent Database - ChromaDB integration for semantic searching.

This module provides the core functionality for storing and retrieving
hierarchical intents and their associated tools using a ChromaDB vector store.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

import chromadb
from chromadb import Collection
from chromadb.api.types import Embeddable, EmbeddingFunction
from chromadb.utils import embedding_functions
from loguru import logger

from common.config import INTENT_COLLECTION_NAME, INTENT_DB_PERSIST_DIR

# Load environment configuration

# ChromaDB configuration
DEFAULT_INTENT_MATCH_THRESHOLD = float(os.getenv("INTENT_MATCH_THRESHOLD", "0.5"))

# Global ChromaDB client and collections cache
_chroma_clients: dict[str, Any] = {}
_collections: dict[str, Collection] = {}


@logger.catch
def initialize_intent_database(
    persist_dir: str = INTENT_DB_PERSIST_DIR,
    collection_name: str = INTENT_COLLECTION_NAME,
) -> Collection:
    """Initialize ChromaDB client and the main collection.

    Parameters
    ----------
    persist_dir : str
        Directory path for ChromaDB persistence.
    collection_name : str, optional
        Name of the ChromaDB collection.

    Returns
    -------
    Collection
        ChromaDB collection for storing intents and tools.
    """
    collection_key = f"{persist_dir}:{collection_name}"
    if collection_key in _collections:
        return _collections[collection_key]

    client = chromadb.PersistentClient(path=persist_dir)
    _chroma_clients[persist_dir] = client

    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=cast(EmbeddingFunction[Embeddable], embedding_function),
    )

    _collections[collection_key] = collection
    logger.info(
        f"Initialized ChromaDB collection: '{collection.name}' at {persist_dir}"
    )
    return collection


@logger.catch
def index_item(collection: Collection, item: dict[str, Any]) -> None:
    """Store a generic item (intent or tool) in ChromaDB.

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to store the item in.
    item : dict[str, Any]
        A dictionary containing the item's data, including id, text, and metadata.
    """
    collection.add(
        ids=[item["id"]],
        documents=[item["text"]],
        metadatas=[item["metadata"]],
    )
    logger.info(f"Indexed {item['metadata'].get('type', 'item')} '{item['id']}': \"{item['text']}\"")

@logger.catch
def index_tool(
    collection: Collection,
    tool_schema: dict[str, Any],
    intent_description: str,
    category: str = "general",
) -> None:
    """Index a tool for semantic search (Chapter 2 compatibility).

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to store the tool in.
    tool_schema : dict[str, Any]
        The JSON schema of the tool.
    intent_description : str
        The text to be used for semantic matching.
    category : str, optional
        A category for the tool, by default "general".
    """
    tool_json = json.dumps(tool_schema, separators=(",", ":"))
    tool_id = f"{category}-{tool_schema['name']}"

    item = {
        "id": tool_id,
        "text": intent_description,
        "metadata": {
            "tool_schema": tool_json,
            "category": category,
            "tool_name": tool_schema["name"],
            "type": "tool",
            "description": tool_schema.get("description", ""),
        },
    }
    index_item(collection, item)


@logger.catch
def query_tools_by_intent(
    collection: Collection, intent: str, n_results: int = 5
) -> list[dict[str, Any]] | None:
    """Query for tools matching an intent (Chapter 2 compatibility).

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to query.
    intent : str
        Abstract intent description.
    n_results : int, optional
        Number of results to return, by default 5.

    Returns
    -------
    list[dict[str, Any]] | None
        List of matching tool schemas, or None.
    """
    results = query_by_intent(
        collection, intent, n_results=n_results, where_clause={"type": "tool"}
    )
    if not results:
        return None

    matching_tools = []
    for item in results:
        tool_schema = json.loads(item["tool_schema"])
        tool_schema["similarity"] = item["similarity"]
        matching_tools.append(tool_schema)

    return matching_tools


@logger.catch
def index_intent_node(collection: Collection, node: dict[str, Any]) -> None:
    """Store a hierarchical intent node in ChromaDB.

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to store the node in.
    node : dict[str, Any]
        A dictionary containing the node's data.
    """
    item = {
        "id": node["id"],
        "text": node["intent_text"],
        "metadata": {
            "type": "intent",
            "level": node["level"],
            "parent_id": node.get("parent_id"),
            "children_ids": json.dumps(node.get("children_ids", [])),
        },
    }
    index_item(collection, item)


def query_intent_nodes(
    collection: Collection,
    intent: str,
    n_results: int = 5,
    where_clause: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Query for any matching item (tool or intent). Renamed for clarity.

    This is a pass-through to the more generic query_by_intent, provided
    for semantic clarity in the Chapter 3 kernel.
    """
    return query_by_intent(
        collection, intent, n_results=n_results, where_clause=where_clause
    )

@logger.catch
def query_by_intent(
    collection: Collection,
    intent: str,
    n_results: int = 5,
    where_clause: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """Query ChromaDB for items matching an abstract intent.

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to query.
    intent : str
        Abstract intent description to match against.
    n_results : int, optional
        Number of results to return, by default 5.
    where_clause : dict[str, Any] | None, optional
        An optional filter to apply to the query.

    Returns
    -------
    list[dict[str, Any]] | None
        List of matching items (intents or tools), or None if no matches are found.
    """
    logger.debug(f"[INTENT_DB] Querying collection '{collection.name}' for intent: '{intent}'")
    logger.debug(f"[INTENT_DB] Query parameters: n_results={n_results}, where_clause={where_clause}")

    results = collection.query(
        query_texts=[intent],
        n_results=n_results,
        where=where_clause,
        include=["documents", "distances", "metadatas"],
    )

    doc_list = results.get("documents")
    dist_list = results.get("distances")
    meta_list = results.get("metadatas")
    id_list = results.get("ids")

    logger.debug(f"[INTENT_DB] Raw ChromaDB results: ids={len(id_list[0]) if id_list and id_list[0] else 0}, "
                f"docs={len(doc_list[0]) if doc_list and doc_list[0] else 0}, "
                f"distances={len(dist_list[0]) if dist_list and dist_list[0] else 0}, "
                f"metadatas={len(meta_list[0]) if meta_list and meta_list[0] else 0}")

    if not doc_list or not dist_list or not meta_list or not id_list or not doc_list[0]:
        logger.info(f"[INTENT_DB] No results found for intent: '{intent}' with filter: {where_clause}")
        return None

    matching_items = []
    for i, (rec_id, doc, dist, meta) in enumerate(zip(id_list[0], doc_list[0], dist_list[0], meta_list[0])):
        if meta is None:
            logger.warning(f"[INTENT_DB] Skipping result {i} due to null metadata")
            continue
        item = dict(meta)
        item["id"] = rec_id
        item["document"] = doc  # Use standard ChromaDB field name
        similarity = 1 - dist
        item["similarity"] = similarity
        matching_items.append(item)

        # Log detailed information about each match
        item_type = item.get("type", "unknown")
        item_id = item.get("tool_name", item.get("id", "unknown"))
        logger.debug(f"[INTENT_DB] Match {i+1}: type={item_type}, id={item_id}, similarity={similarity:.3f}")
        logger.debug(f"[INTENT_DB] Document text: {doc[:100]}{'...' if len(doc) > 100 else ''}")

    # Build similarity summary without nested f-strings to avoid syntax issues
    similarity_summary = []
    for item in matching_items:
        item_name = item.get("tool_name", item.get("id", "unknown"))
        similarity = item["similarity"]
        similarity_summary.append(f"{item_name}({similarity:.3f})")

    logger.info(f"[INTENT_DB] Found {len(matching_items)} items for intent '{intent}' with similarities: {similarity_summary}")

    return matching_items


@logger.catch
def get_item_by_id(collection: Collection, item_id: str) -> dict[str, Any] | None:
    """Retrieve a single item from the database by its unique ID.

    Parameters
    ----------
    collection : Collection
        ChromaDB collection to query.
    item_id : str
        The unique ID of the item to retrieve.

    Returns
    -------
    dict[str, Any] | None
        The retrieved item's metadata or None if not found.
    """
    result = collection.get(ids=[item_id], include=["metadatas"])
    metadatas = result.get("metadatas")
    if metadatas and metadatas[0]:
        return dict(metadatas[0])
    return None



@logger.catch
def clear_collection(collection: Collection) -> None:
    """Clear all items from the collection.

    This function deletes all documents and their associated metadata
    from the specified ChromaDB collection.

    Parameters
    ----------
    collection : Collection
        The ChromaDB collection to clear.
    """
    count = collection.count()
    if count > 0:
        ids_to_delete = collection.get(limit=count)["ids"]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Cleared {len(ids_to_delete)} items from '{collection.name}'")
    else:
        logger.info(f"Collection '{collection.name}' is already empty.")


@logger.catch
async def save_collection_metadata(
    persist_dir: str = INTENT_DB_PERSIST_DIR,
    collection_name: str = INTENT_COLLECTION_NAME,
    metadata: dict[str, Any] = {},
) -> None:
    """Store or update additional metadata at the collection level.

    This uses a special document with ID 'collection_metadata' to store
    a JSON blob of key-value pairs. It merges the provided metadata
    with any existing metadata.

    Parameters
    ----------
    persist_dir : str
        Directory path for ChromaDB persistence.
    collection_name : str
        Name of the ChromaDB collection.
    metadata : dict[str, Any]
        The metadata to save. It will be merged with existing metadata.
    """
    collection = initialize_intent_database(persist_dir, collection_name)
    existing_item = collection.get(ids=["collection_metadata"], include=["documents"])

    existing_metadata = {}
    documents = existing_item.get("documents")
    if documents and documents[0]:
        try:
            existing_metadata = json.loads(documents[0])
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse existing metadata; will overwrite.")

    updated_metadata = {**existing_metadata, **metadata}
    serialized_metadata = json.dumps(updated_metadata)

    collection.upsert(
        ids=["collection_metadata"],
        documents=[serialized_metadata],
        metadatas=[{"type": "metadata"}],
    )
    logger.info(f"Upserted collection metadata for '{collection.name}'.")


@logger.catch
async def get_collection_metadata(
    persist_dir: str = INTENT_DB_PERSIST_DIR,
    collection_name: str = INTENT_COLLECTION_NAME,
) -> dict[str, Any]:
    """Retrieve additional metadata stored at the collection level.

    Parameters
    ----------
    persist_dir : str
        Directory path for ChromaDB persistence.
    collection_name : str
        Name of the ChromaDB collection.

    Returns
    -------
    dict[str, Any]
        The metadata from the collection.
    """
    collection = initialize_intent_database(persist_dir, collection_name)
    result = collection.get(ids=["collection_metadata"], include=["documents"])

    documents = result.get("documents")
    if documents and documents[0]:
        try:
            return json.loads(documents[0])
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error decoding collection metadata: {e}")
            return {}

    logger.debug("No collection metadata found.")
    return {}


def _get_collection(persist_dir: str, collection_name: str) -> Collection:
    """Internal helper to retrieve an initialized collection."""
    key = f"{persist_dir}:{collection_name}"
    if key not in _collections:
        raise RuntimeError(
            f"Collection '{collection_name}' not initialized in '{persist_dir}'"
        )
    return _collections[key]


@logger.catch
def update_document(collection: Collection, doc_id: str, new_metadata: dict[str, Any]) -> None:
    """Update an existing document's metadata in ChromaDB.

    This function is used for the UPSERT logic in the intent hierarchy, allowing
    for the modification of existing documents (e.g., adding a new tool to an
    existing L1 intent's list or merging L1 intents into an L2 category).

    Parameters
    ----------
    collection : Collection
        ChromaDB collection containing the document.
    doc_id : str
        The unique ID of the document to update.
    new_metadata : dict[str, Any]
        The new metadata to merge with the existing metadata.
    """
    # Get the existing document
    result = collection.get(ids=[doc_id], include=["documents", "metadatas"])

    documents = result.get("documents")
    metadatas = result.get("metadatas")

    if not documents or not metadatas or not documents[0] or not metadatas[0]:
        logger.error(f"Document with ID '{doc_id}' not found for update.")
        return

    # Merge the new metadata with the existing metadata
    existing_metadata = dict(metadatas[0])

    # Special handling for arrays in metadata (tools for L1, l1_intents for L2)
    for key, value in new_metadata.items():
        # Always convert lists to JSON strings for ChromaDB compatibility
        if isinstance(value, list):
            # If the key exists in existing metadata
            if key in existing_metadata:
                existing_value = existing_metadata[key]

                # Case 1: Existing value is already a JSON string array
                if isinstance(existing_value, str) and existing_value.startswith('[') and existing_value.endswith(']'):
                    try:
                        existing_list = json.loads(existing_value)
                        if isinstance(existing_list, list):
                            # Merge lists and remove duplicates
                            combined_list = existing_list + value
                            # Remove duplicates while preserving order
                            seen = set()
                            deduplicated = [x for x in combined_list if not (x in seen or seen.add(x))]
                            existing_metadata[key] = json.dumps(deduplicated)
                        else:
                            # Not actually a list, overwrite
                            existing_metadata[key] = json.dumps(value)
                    except (json.JSONDecodeError, TypeError):
                        # Invalid JSON, overwrite
                        existing_metadata[key] = json.dumps(value)

                # Case 2: Existing value is a Python list (rare in ChromaDB but possible)
                elif isinstance(existing_value, list):
                    # Merge lists and remove duplicates - cast to ensure type safety
                    combined_list = list(existing_value) + list(value)
                    # Remove duplicates while preserving order
                    seen = set()
                    deduplicated = [x for x in combined_list if not (x in seen or seen.add(x))]
                    existing_metadata[key] = json.dumps(deduplicated)

                # Case 3: Existing value is something else, overwrite
                else:
                    existing_metadata[key] = json.dumps(value)

            # Key doesn't exist, just add it
            else:
                existing_metadata[key] = json.dumps(value)

        # Non-list values are stored as-is
        else:
            existing_metadata[key] = value

    # Update the document in the collection
    collection.update(
        ids=[doc_id],
        metadatas=[existing_metadata]
    )

    logger.info(f"Updated document '{doc_id}' with merged metadata.")
