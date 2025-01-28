"""Storage Specialist: Expert agent for knowledge integration and conflict resolution.

The Storage Specialist makes sophisticated decisions about if and how to store new
information, handling everything from simple facts to complex knowledge updates.
Unlike basic storage systems, this specialist reasons about temporal changes,
resolves conflicts, and maintains knowledge coherence.

Architecture Overview:
```mermaid
graph TD
    SS[Storage Specialist]

    subgraph "Analysis Phase"
        EA[Evaluate Action]
        subgraph "Action Types"
            NS[No Storage Needed]
            NC[New Creation]
            TC[Temporal Change]
            CR[Correction]
            CF[Conflict Resolution]
        end
    end

    subgraph "Storage Phase"
        KS[Knowledge Store]
        ES[Embedding Store]
        MD[Metadata/Context]
        HT[History Tracking]
    end

    SS -->|Analyzes| EA
    EA -->|Determines| NS
    EA -->|Determines| NC
    EA -->|Determines| TC
    EA -->|Determines| CR
    EA -->|Determines| CF

    NC -->|New Entry| KS
    TC -->|Version History| HT
    CR -->|Update + Rationale| KS
    CF -->|Resolution + Context| KS

    KS --> ES
    KS --> MD
```

Design Philosophy:
The storage specialist implements sophisticated knowledge management through
careful analysis of information types and relationships:

1. Storage Decisions
   - Commands rarely need storage
   - Questions inform context but aren't stored
   - Facts and preferences typically stored
   - Observations may need compression
   - System actions usually skipped

2. Temporal Management
   When handling "I've switched to tea":
   - Preserves coffee preference history
   - Records temporal progression
   - Maintains morning routine context
   - Notes preference evolution

3. Conflict Resolution
   For contradictory information:
   - Evaluates source reliability
   - Considers temporal sequence
   - Preserves conflicting versions
   - Documents resolution rationale

4. Context Preservation
   - Maintains semantic connections
   - Tracks relationship context
   - Preserves temporal markers
   - Records decision metadata

Example Scenarios:

1. No Storage Needed:
   Input: "Open the window"
   Analysis:
   - Command, not knowledge
   - No persistent value
   - Action only
   Result: NO_STORAGE_NEEDED

2. Temporal Change:
   Input: "I've switched to tea"
   Analysis:
   - Existing preference found
   - Temporal progression
   - Context preservation needed
   Result: TEMPORAL_CHANGE
   Actions:
   - Archive coffee preference
   - Store new preference
   - Maintain context
   - Update embeddings

3. Conflict Resolution:
   Input: "Actually, I still drink coffee sometimes"
   Analysis:
   - Partial contradiction
   - Pattern refinement
   - Temporal aspects
   Result: CONFLICT_RESOLUTION
   Actions:
   - Update recent change
   - Note pattern complexity
   - Preserve history
   - Clarify conditions

4. Correction:
   Input: "No, I meant green tea, not black tea"
   Analysis:
   - Direct correction
   - Same temporal context
   - Specific detail update
   Result: CORRECTION
   Actions:
   - Update specific detail
   - Maintain other context
   - Note correction
   - No history needed

Key Design Decisions:
- Rich action type enumeration
- Careful history preservation
- Context-aware updates
- Clear update rationales
- Flexible metadata tracking

The specialist's system prompt guides the LLM to:
1. Analyze information type
2. Check existing knowledge
3. Determine appropriate action
4. Explain storage decisions
5. Maintain knowledge coherence

This design enables sophisticated knowledge management while maintaining:
- Clear decision patterns
- Robust conflict handling
- Rich temporal tracking
- Context preservation
- Knowledge coherence
"""

import json
from enum import StrEnum, auto
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.memory.embeddings import (
  EmbeddingStore,
)
from winston.core.memory.storage import (
  KnowledgeStorage,
)
from winston.core.paths import AgentPaths
from winston.core.system import AgentSystem
from winston.core.tools import Tool


class KnowledgeActionType(StrEnum):
  """Types of knowledge storage actions."""

  NO_STORAGE_NEEDED = auto()
  CREATE = auto()
  UPDATE = auto()
  TEMPORAL_CHANGE = auto()
  CORRECTION = auto()
  CONFLICT_RESOLUTION = auto()


class StoreKnowledgeResult(BaseModel):
  """Result of knowledge storage/update operation."""

  id: str | None = Field(
    default=None,
    description="ID of stored/updated knowledge",
  )
  content: str | None = Field(
    default=None, description="The knowledge content"
  )
  metadata: dict[str, str] | None = Field(
    default=None, description="Associated metadata"
  )
  action: KnowledgeActionType = Field(
    description="Type of action taken"
  )
  reason: str = Field(
    description="Explanation for the action taken"
  )


class StorageRequest(BaseModel):
  """Unified request model for all storage operations."""

  action: KnowledgeActionType = Field(
    description="Type of storage action"
  )
  content: str | None = Field(
    default=None,
    description="Content to store or update",
  )
  knowledge_id: str | None = Field(
    default=None,
    description="ID of knowledge to update (for updates only)",
  )
  semantic_metadata: str = Field(
    description="JSON-encoded dictionary of key:value pairs for filtering",
  )
  preserve_history: bool = Field(
    description="Whether to preserve old version during updates",
  )
  reason: str = Field(
    description="Explanation for the action taken"
  )


class StorageSpecialist(BaseAgent):
  """Specialist for evaluating and storing new knowledge."""

  def __init__(
    self,
    system: AgentSystem,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    """Initialize storage specialist."""
    super().__init__(system, config, paths)
    logger.info(
      f"Initializing StorageSpecialist {self.id}"
    )

    # Initialize storage components
    storage_path = paths.workspaces / "knowledge"
    embedding_path = paths.workspaces / "embeddings"
    logger.debug(
      f"Setting up storage paths:\n"
      f"Storage: {storage_path}\n"
      f"Embeddings: {embedding_path}"
    )

    self._storage = KnowledgeStorage(storage_path)
    self._embeddings = EmbeddingStore(embedding_path)

    tool = Tool(
      name="manage_knowledge",
      description="Unified tool for managing knowledge storage and updates",
      handler=self._handle_storage_request,
      input_model=StorageRequest,
      output_model=StoreKnowledgeResult,
    )
    self.system.register_tool(tool)
    self.system.grant_tool_access(self.id, [tool.name])

    logger.info(
      "StorageSpecialist initialization complete"
    )

  def _dump_obj(self, obj: Any) -> str:
    """Helper to safely dump objects for logging."""
    try:
      if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), indent=2)
      return str(obj)
    except Exception as e:
      return f"<unable to dump object: {e}>"

  async def _handle_storage_request(
    self,
    request: StorageRequest,
  ) -> StoreKnowledgeResult:
    """Handle all storage operations based on action type."""
    logger.info(
      f"Processing storage request action: {request.action}"
    )
    logger.debug(
      f"Full request:\n{self._dump_obj(request)}"
    )

    try:
      if (
        request.action
        == KnowledgeActionType.NO_STORAGE_NEEDED
      ):
        logger.debug(
          f"No storage needed, reason: {request.reason}"
        )
        return StoreKnowledgeResult(
          action=KnowledgeActionType.NO_STORAGE_NEEDED,
          reason=request.reason,
        )

      # Parse metadata if provided
      metadata = {}
      if request.semantic_metadata:
        logger.trace(
          f"Parsing metadata: {request.semantic_metadata}"
        )
        metadata = json.loads(
          request.semantic_metadata
        )
        if not isinstance(metadata, dict):
          logger.error(
            f"Invalid metadata type: {type(metadata)}"
          )
          raise ValueError(
            "Expected metadata to be a dictionary"
          )
          logger.debug(
            f"Parsed metadata: {json.dumps(metadata, indent=2)}"
          )

      if request.action == KnowledgeActionType.CREATE:
        logger.info("Processing CREATE action")
        if not request.content:
          logger.error(
            "Missing required content for CREATE"
          )
          raise ValueError(
            "Content required for storage"
          )

        knowledge_id = await self._storage.store(
          content=request.content,
          context=metadata,
        )
        logger.debug(
          f"Created knowledge with ID: {knowledge_id}"
        )

        knowledge = await self._storage.load(
          knowledge_id
        )
        logger.trace(
          f"Loaded knowledge:\n{self._dump_obj(knowledge)}"
        )

        await self._embeddings.add_embedding(knowledge)
        logger.debug(
          "Added embeddings for new knowledge"
        )

        result = StoreKnowledgeResult(
          id=knowledge_id,
          content=request.content,
          metadata=metadata,
          action=request.action,
          reason=request.reason,
        )
        logger.debug(
          f"CREATE result:\n{self._dump_obj(result)}"
        )
        return result

      # Handle updates
      logger.info(
        f"Processing update action: {request.action}"
      )
      if (
        not request.knowledge_id or not request.content
      ):
        logger.error(
          "Missing required fields for update operation"
        )
        raise ValueError(
          "knowledge_id and content required for updates"
        )

      if request.preserve_history:
        logger.debug(
          f"Preserving history for knowledge {request.knowledge_id}"
        )
        existing = await self._storage.load(
          request.knowledge_id
        )
        logger.trace(
          f"Existing knowledge:\n{self._dump_obj(existing)}"
        )

        await self._storage.store(
          content=existing.content,
          context={
            **existing.context,
            "archived": "true",
          },
        )
        logger.debug("Archived existing version")

      updated = await self._storage.update(
        request.knowledge_id,
        content=request.content,
        context=metadata,
      )
      logger.debug(
        f"Updated knowledge:\n{self._dump_obj(updated)}"
      )

      await self._embeddings.update_embedding(updated)
      logger.debug("Updated embeddings")

      result = StoreKnowledgeResult(
        id=request.knowledge_id,
        content=request.content,
        metadata=metadata,
        action=request.action,
        reason=request.reason,
      )
      logger.debug(
        f"Update result:\n{self._dump_obj(result)}"
      )
      return result

    except Exception as e:
      logger.error(
        f"Storage operation failed: {str(e)}",
        exc_info=True,
      )
      raise
