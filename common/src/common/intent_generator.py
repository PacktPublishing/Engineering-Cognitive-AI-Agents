"""Generates a hierarchical set of intents from MCP tool schemas.

This module provides the IntentGenerator class, which uses a multi-pass
approach with a Large Language Model (LLM) to build a two-level hierarchy
of intents (Tool-Level and Server-Level) from the tools exposed by MCP servers.
Higher-level domain abstractions emerge from the semantic properties of the
vector space.
"""

import json
import hashlib
from typing import Any

from jinja2 import Environment
from loguru import logger
from mcp import Tool
from openai import AsyncOpenAI
from chromadb import Collection

from .config import INTENT_INSERTION_THRESHOLD
from .mcp_host import MCPHost
from .intent_database import (
    get_collection_metadata,
    save_collection_metadata,
    clear_collection,
    index_item,
    update_document,
    query_by_intent,
)


class IntentGenerator:
    """Generates a hierarchical set of intents from MCP tool schemas.

    This class uses a multi-pass approach with an LLM to build a
    two-level hierarchy of intents.

    Parameters
    ----------
    openai_client : AsyncOpenAI
        An authenticated OpenAI client instance.
    mcp_host : MCPHost
        An initialized MCPHost containing the server configurations.
    template_env : Environment
        A Jinja2 environment for loading prompt templates.
    """

    client: AsyncOpenAI
    host: MCPHost
    template_env: Environment
    persist_dir: str

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        mcp_host: MCPHost,
        template_env: Environment,
        persist_dir: str,
    ):
        """Initialize the IntentGenerator.

        Parameters
        ----------
        openai_client : AsyncOpenAI
            An authenticated OpenAI client instance.
        mcp_host : MCPHost
            An initialized MCPHost instance.
        template_env : Environment
            Jinja2 environment for loading prompt templates.
        persist_dir : str
            Path to the directory for persistent data (e.g., ChromaDB).
        """
        self.client = openai_client
        self.host = mcp_host
        self.template_env = template_env
        self.persist_dir = persist_dir

    async def generate_and_store_intents_if_needed(
        self, collection: Collection
    ) -> None:
        """
        Check if the MCP configuration has changed and, if so, regenerate and
        store the entire intent hierarchy.
        """
        if await self.is_regeneration_needed():
            logger.info("MCP config change detected. Regenerating intent hierarchy...")
            clear_collection(collection)

            await self._build_intent_index(collection)

            current_hash = self._calculate_config_hash()
            await save_collection_metadata(
                self.persist_dir, metadata={"config_hash": current_hash}
            )
            logger.info("Intent hierarchy regenerated and config hash updated.")
        else:
            logger.info("MCP config unchanged. Skipping intent regeneration.")

    async def is_regeneration_needed(self) -> bool:
        """Check if the MCP config has changed since the last run."""
        current_hash = self._calculate_config_hash()
        persisted_metadata = await get_collection_metadata(self.persist_dir)
        persisted_hash: str | None = persisted_metadata.get("config_hash")
        logger.debug(f"IntentGenerator calculated current_hash: {current_hash}")
        logger.debug(f"IntentGenerator found persisted_hash: {persisted_hash}")
        regeneration_needed = current_hash != persisted_hash
        logger.debug(f"Regeneration decision: {regeneration_needed}")
        return regeneration_needed

    def _calculate_config_hash(self) -> str:
        """Generate a secure hash of the current MCP configuration."""
        config_str = json.dumps(self.host.config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(config_str.encode("utf-8")).hexdigest()

    async def _build_intent_index(self, collection: Collection) -> None:
        """Orchestrate the server-by-server intent generation process with global UPSERT logic.

        This method implements the two-level intent hierarchy as described in the
        architecture document. It processes each server's tools together to generate
        coherent L1 and L2 intents, while maintaining a global index that avoids
        semantic duplication across servers.

        Parameters
        ----------
        collection : Collection
            The ChromaDB collection to store the intent hierarchy.
        """
        logger.info("Starting server-by-server intent generation...")
        all_tools = await self.host.get_all_tools()

        # Process each server's tools together
        for server_name, tool_list in all_tools.items():
            logger.info(f"Processing server: {server_name}")

            # Step 1: Process L1 intents for this server
            server_l1_intents = await self._process_server_l1_intents(collection, server_name, tool_list)

            # Step 2: Process L2 intents for this server using the L1 intents
            await self._process_server_l2_intents(collection, server_name, server_l1_intents)

        # Log the final counts
        l1_result = collection.get(where={"type": "L1"})
        l2_result = collection.get(where={"type": "L2"})
        l1_count = len(l1_result.get("ids", [])) if l1_result else 0
        l2_count = len(l2_result.get("ids", [])) if l2_result else 0
        logger.info(f"Intent index built with {l1_count} L1 intents and {l2_count} L2 intents.")

    async def _find_similar_intent(
        self, collection: Collection, intent_text: str, intent_type: str
    ) -> tuple[bool, str | None]:
        """Find a semantically similar intent in the collection.

        Parameters
        ----------
        collection : Collection
            The ChromaDB collection to search.
        intent_text : str
            The intent text to search for.
        intent_type : str
            The type of intent to search for ("L1" or "L2").

        Returns
        -------
        tuple[bool, str | None]
            A tuple containing a boolean indicating if a match was found and
            the ID of the matching document if found, None otherwise.
        """
        # Query the collection for semantically similar intents of the specified type
        results = query_by_intent(
            collection,
            intent_text,
            n_results=1,
            where_clause={"type": intent_type}
        )

        # Apply a high threshold for semantic similarity (0.92)
        if results and len(results) > 0:
            best_match = results[0]
            similarity = best_match.get("similarity", 0)
            match_id = best_match.get("id")
            match_text = best_match.get("document", "Unknown")

            logger.info(f"Found potential {intent_type} match for intent: '{intent_text}'")
            logger.info(f"  Match text: '{match_text}'")
            logger.info(f"  Similarity score: {similarity:.4f} (threshold: {INTENT_INSERTION_THRESHOLD})")

            if similarity >= INTENT_INSERTION_THRESHOLD:
                logger.info(f"  ✅ Match accepted: Similarity {similarity:.4f} >= {INTENT_INSERTION_THRESHOLD}")
                return True, match_id
            else:
                logger.info(f"  ❌ Match rejected: Similarity {similarity:.4f} < {INTENT_INSERTION_THRESHOLD}")
        else:
            logger.info(f"No potential {intent_type} matches found for intent: '{intent_text}'")

        return False, None

    async def _process_server_l1_intents(
        self, collection: Collection, server_name: str, tool_list: list[Tool]
    ) -> list[str]:
        """Process L1 intents for a server with global UPSERT logic.

        For each tool on the server, generate an L1 intent and either update an
        existing semantically similar L1 intent or create a new one.

        Parameters
        ----------
        collection : Collection
            The ChromaDB collection to store the intents.
        server_name : str
            The name of the server being processed.
        tool_list : list[Tool]
            The list of tools on the server.

        Returns
        -------
        list[str]
            A list of L1 intent texts generated for this server.
        """
        logger.debug(f"Generating L1 intents for server: {server_name}")
        template = self.template_env.get_template("common/generate_l1_intent.md")
        server_l1_intents = []

        for tool in tool_list:
            # Generate L1 intent text for this tool
            prompt = await template.render_async(tool=tool)
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            intent_text = (response.choices[0].message.content or "").strip()
            tool_uri = f"tool::{server_name}::{tool.name}"

            # Check if a semantically similar L1 intent already exists
            match_found, existing_id = await self._find_similar_intent(collection, intent_text, "L1")

            if match_found and existing_id:
                # UPDATE: Add this tool to the existing L1 intent
                logger.debug(f"Updating existing L1 intent with new tool: {tool.name}")
                existing_doc = collection.get(ids=[existing_id], include=["metadatas", "documents"])

                if not existing_doc:
                    logger.error(f"Failed to retrieve document with ID: {existing_id}")
                    continue

                metadatas = existing_doc.get("metadatas", [])
                if not metadatas or not metadatas[0]:
                    logger.error(f"Failed to retrieve existing document with ID: {existing_id}")
                    continue

                existing_tools_str = metadatas[0].get("tools", "[]")
                try:
                    # Ensure we're parsing a string
                    if isinstance(existing_tools_str, str):
                        existing_tools = json.loads(existing_tools_str)
                    else:
                        logger.warning(f"Tools metadata is not a string: {type(existing_tools_str)}")
                        existing_tools = []
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse tools JSON for document: {existing_id}")
                    existing_tools = []

                # Add the new tool URI if it's not already in the list
                if tool_uri not in existing_tools:
                    existing_tools.append(tool_uri)

                # Prepare metadata update - always include tools, and add schema if missing
                metadata_update = {"tools": json.dumps(existing_tools)}

                # Check if schema is missing and add it from current tool
                existing_schema = metadatas[0].get("schema")
                if not existing_schema:
                    metadata_update["schema"] = json.dumps(tool.inputSchema)

                # Update the document with the merged tools list and schema
                update_document(
                    collection,
                    existing_id,
                    metadata_update
                )

                # Use the existing intent text for L2 generation
                documents = existing_doc.get("documents", [])
                if not documents or not documents[0]:
                    logger.error(f"Document with ID {existing_id} has no content")
                    continue

                existing_document = documents[0]
                server_l1_intents.append(existing_document)
            else:
                # INSERT: Create a new L1 intent document
                logger.debug(f"Creating new L1 intent for tool: {tool.name}")
                doc_id = f"intent::L1::{server_name}::{tool.name}"
                index_item(
                    collection,
                    {
                        "id": doc_id,
                        "text": intent_text,
                        "metadata": {
                            "type": "L1",
                            "tools": json.dumps([tool_uri]),
                            "schema": json.dumps(tool.inputSchema),
                        },
                    }
                )
                server_l1_intents.append(intent_text)

        logger.info(f"Generated {len(server_l1_intents)} L1 intents for server: {server_name}")
        return server_l1_intents

    async def _process_server_l2_intents(
        self, collection: Collection, server_name: str, l1_intent_texts: list[str]
    ) -> None:
        """Process L2 intents for a server with global UPSERT logic.

        Generate L2 categories from the server's L1 intents and either update
        existing semantically similar L2 intents or create new ones.

        Parameters
        ----------
        collection : Collection
            The ChromaDB collection to store the intents.
        server_name : str
            The name of the server being processed.
        l1_intent_texts : list[str]
            The list of L1 intent texts for this server.
        """
        if not l1_intent_texts:
            logger.warning(f"No L1 intents to categorize for server: {server_name}")
            return

        logger.debug(f"Generating L2 categories for server: {server_name}")
        template = self.template_env.get_template("common/generate_l2_intent.md")

        # Generate L2 categories using the LLM
        prompt = await template.render_async(l1_intents=l1_intent_texts)
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        llm_output = (response.choices[0].message.content or "").strip()

        # Parse the LLM output to extract L2 groups
        l2_groups = self._parse_l2_groups(llm_output)

        # Process each L2 group
        for group_idx, (l2_intent_text, group_l1_intents) in enumerate(l2_groups):
            # Check if a semantically similar L2 intent already exists
            match_found, existing_id = await self._find_similar_intent(collection, l2_intent_text, "L2")

            if match_found and existing_id:
                # UPDATE: Merge this group's L1 intents with the existing L2 intent
                logger.debug(f"Updating existing L2 intent: {l2_intent_text}")
                existing_doc = collection.get(ids=[existing_id], include=["metadatas"])

                if not existing_doc:
                    logger.error(f"Failed to retrieve document with ID: {existing_id}")
                    continue

                metadatas = existing_doc.get("metadatas", [])
                if not metadatas or not metadatas[0]:
                    logger.error(f"Failed to retrieve existing document with ID: {existing_id}")
                    continue

                existing_l1_intents_str = metadatas[0].get("l1_intents", "[]")
                try:
                    # Ensure we're parsing a string
                    if isinstance(existing_l1_intents_str, str):
                        existing_l1_intents = json.loads(existing_l1_intents_str)
                    else:
                        logger.warning(f"L1 intents metadata is not a string: {type(existing_l1_intents_str)}")
                        existing_l1_intents = []
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse l1_intents JSON for document: {existing_id}")
                    existing_l1_intents = []

                # Merge the L1 intents, avoiding duplicates
                merged_l1_intents = list(set(existing_l1_intents + group_l1_intents))

                # Update the document with the merged L1 intents
                update_document(
                    collection,
                    existing_id,
                    {"l1_intents": json.dumps(merged_l1_intents)}
                )
            else:
                # INSERT: Create a new L2 intent document
                logger.debug(f"Creating new L2 intent: {l2_intent_text}")
                doc_id = f"intent::L2::{server_name}::{group_idx}"
                index_item(
                    collection,
                    {
                        "id": doc_id,
                        "text": l2_intent_text,
                        "metadata": {
                            "type": "L2",
                            "l1_intents": json.dumps(group_l1_intents),
                        },
                    }
                )

        logger.info(f"Generated {len(l2_groups)} L2 categories for server: {server_name}")

    def _parse_l2_groups(self, llm_output: str) -> list[tuple[str, list[str]]]:
        """Parse the LLM output to extract L2 groups.

        Parameters
        ----------
        llm_output : str
            The raw output from the LLM containing [GROUP] blocks.

        Returns
        -------
        list[tuple[str, list[str]]]
            A list of tuples, each containing an L2 intent text and a list of L1 intent texts.
        """
        groups = []
        current_l2_intent = None
        current_l1_intents = []
        in_l1_list = False

        # Split the output into lines and process each line
        for line in llm_output.split('\n'):
            line = line.strip()

            if not line:
                continue

            if line == '[GROUP]':
                # Start a new group
                if current_l2_intent and current_l1_intents:
                    groups.append((current_l2_intent, current_l1_intents))
                current_l2_intent = None
                current_l1_intents = []
                in_l1_list = False
            elif line.startswith('L2 Intent:'):
                # Extract the L2 intent text
                current_l2_intent = line[len('L2 Intent:'):].strip()
            elif line == 'L1 Intents:':
                # Start collecting L1 intents
                in_l1_list = True
            elif in_l1_list and line.startswith('- '):
                # Add an L1 intent to the current group
                l1_intent = line[2:].strip()
                current_l1_intents.append(l1_intent)

        # Add the last group if it exists
        if current_l2_intent and current_l1_intents:
            groups.append((current_l2_intent, current_l1_intents))

        return groups

    async def _generate_l1_tool_intents_async(
        self, all_tools: dict[str, list[Tool]]
    ) -> list[dict[str, Any]]:
        """Generate Level 1 intents, one for each tool."""
        logger.debug("Generating Level 1 (Tool) intents...")
        template = self.template_env.get_template("common/generate_l1_intent.md")
        intents = []
        for server_name, tool_list in all_tools.items():
            for tool in tool_list:
                prompt = await template.render_async(tool=tool)
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                )
                intent_text = (response.choices[0].message.content or "").strip()
                tool_uri = f"tool::{server_name}::{tool.name}"
                logger.debug(
                    f"Generated L1 intent for {server_name}::{tool.name}: {intent_text}"
                )
                intents.append({
                    "id": f"intent::L1::{server_name}::{tool.name}",
                    "intent": intent_text,
                    "tool_uri": tool_uri,
                })
        logger.info(f"Generated {len(intents)} L1 intents.")
        return intents

    async def _generate_l2_server_intents_async(
        self, l1_intents: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate Level 2 intents, one for each server."""
        logger.debug("Generating Level 2 (Server) intents...")
        template = self.template_env.get_template("common/generate_l2_intent.md")
        server_to_l1: dict[str, list[dict[str, Any]]] = {}
        for intent in l1_intents:
            server_name = intent["id"].split("::")[2]
            server_to_l1.setdefault(server_name, []).append(intent)

        intents = []
        for server_name, child_intents in server_to_l1.items():
            child_intent_texts = [i["intent"] for i in child_intents]
            prompt = await template.render_async(
                server_name=server_name, child_intents=child_intent_texts
            )
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            intent_text = (response.choices[0].message.content or "").strip()
            intents.append({
                "id": f"intent::L2::{server_name}",
                "intent": intent_text,
                "l1_intent_texts": child_intent_texts,
            })
        logger.info(f"Generated {len(intents)} L2 intents.")
        return intents
