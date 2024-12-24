"""Memory Coordinator: Central orchestrator for Winston's cognitive memory system.

The Memory Coordinator implements a Society of Mind approach to memory management,
coordinating specialized agents that handle different aspects of memory operations.
Rather than treating memory as simple storage, this system mirrors human cognitive
processes by maintaining working context while building long-term knowledge.

Architecture Overview:
```mermaid
graph TD
    MC[Memory Coordinator] -->|Request Analysis| EA[Episode Analyst]
    EA -->|Episode Status| MC
    MC -->|Request Operations| SMC[Semantic Memory Coordinator]
    SMC -->|Retrieval| RS[Retrieval Specialist]
    SMC -->|Storage| SS[Storage Specialist]
    RS -->|Context| SMC
    SS -->|Updates| SMC
    SMC -->|Retrieved Context + New Facts| MC
    MC -->|Update Request| WMS[Working Memory Specialist]
    WMS -->|Updated State| MC
```

Design Philosophy:
The memory system addresses a fundamental challenge in LLM-based cognitive
architectures: while language models provide sophisticated reasoning, they cannot
inherently learn from interactions or maintain context over time. The Memory
Coordinator bridges this gap by:

1. Managing Working Memory
   - Maintains immediate cognitive context
   - Coordinates shared understanding between agents
   - Preserves relevant context across interactions

2. Building Long-term Knowledge
   - Detects and processes new information
   - Maintains semantic connections between facts
   - Updates existing knowledge when understanding changes

3. Processing Experiences
   - Identifies cognitive episode boundaries
   - Extracts key facts and relationships
   - Compresses experiences into semantic knowledge

Example Flow:
When Winston learns "I usually drink coffee in the morning, like my father used to",
the system:
1. Episode Analyst determines this reveals preferences and relationships
2. Semantic Memory retrieves any related knowledge about routines/preferences
3. Storage Specialist captures both the preference and family connection
4. Working Memory Specialist updates current context while maintaining relationships

Key Architectural Principles:
- Coordinators handle flow control (pure Python)
- Specialists make cognitive decisions (LLM-based)
- Tools execute concrete actions
- Clear separation of concerns throughout

This design enables Winston to build and maintain a rich web of knowledge while
keeping each component focused and maintainable. The coordinator ensures these
pieces work together seamlessly, providing other agents with a simple interface
to sophisticated memory operations.
"""

import json
from textwrap import dedent
from typing import AsyncIterator

from loguru import logger

from winston.core.agent import BaseAgent
from winston.core.agent_config import AgentConfig
from winston.core.memory.episode_analyst import (
  EpisodeAnalyst,
  EpisodeBoundaryResult,
)
from winston.core.memory.semantic.coordinator import (
  SemanticMemoryCoordinator,
  SemanticMemoryResult,
)
from winston.core.memory.working_memory import (
  WorkingMemorySpecialist,
  WorkspaceUpdateResult,
)
from winston.core.messages import (
  Message,
  Response,
)
from winston.core.paths import AgentPaths
from winston.core.steps import ProcessingStep
from winston.core.system import AgentSystem
from winston.core.workspace import WorkspaceManager


class MemoryCoordinator(BaseAgent):
  """Orchestrates memory operations between specialist agents."""

  def __init__(
    self,
    system: AgentSystem,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    logger.info("MemoryCoordinator initialized")

    # Initialize specialist agents with their own configs
    self.episode_analyst = EpisodeAnalyst(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "memory"
        / "episode_analyst.yaml"
      ),
      paths,
    )

    self.semantic_memory = SemanticMemoryCoordinator(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "memory"
        / "semantic"
        / "coordinator.yaml"
      ),
      paths,
    )

    self.working_memory = WorkingMemorySpecialist(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "memory"
        / "working_memory.yaml"
      ),
      paths,
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Orchestrate memory operations sequence."""
    logger.debug(f"Processing message: {message}")

    # Validate shared workspace requirement
    if "shared_workspace" not in message.metadata:
      logger.error(
        "Shared workspace not found in message metadata."
      )
      raise ValueError(
        "Shared workspace required for memory operations"
      )

    # Load the current workspace
    workspace_manager = WorkspaceManager()
    current_workspace = (
      workspace_manager.load_workspace(
        message.metadata["shared_workspace"]
      )
    )

    # Add the current workspace to the message metadata,
    # making it available to downstream agents
    message.metadata["current_workspace"] = (
      current_workspace
    )

    logger.trace(
      "Evaluating context shift with episode analyst."
    )
    # Let episode analyst evaluate the context shift
    async with ProcessingStep(
      name="Episode Analysis agent", step_type="run"
    ) as step:
      episode_analysis = {}
      async for (
        response
      ) in self.episode_analyst.process(message):
        if not response.metadata.get("streaming"):
          logger.trace(
            f"Raw episode analysis obtained: {response}"
          )
          episode_analysis = (
            EpisodeBoundaryResult.model_validate_json(
              response.content
            )
          )
          # Update the step
          await step.show_response(
            Response(
              content=dedent(f"""
```markdown
# Episode Analysis:

- New Episode: {episode_analysis.is_new_episode}
- Preserve Context: {json.dumps(episode_analysis.preserve_context, indent=2)}
```""").strip(),
              metadata=message.metadata,
            )
          )

          # Add the episode analysis to the message metadata,
          # making it available to downstream agents
          message.metadata["is_new_episode"] = (
            episode_analysis.is_new_episode
          )
          message.metadata["preserve_context"] = (
            episode_analysis.preserve_context
          )

    logger.info(
      f"Episode analysis completed: {episode_analysis}"
    )

    logger.trace(
      "Handling knowledge operations with semantic memory specialist."
    )

    # Let semantic memory coordinator handle knowledge operations
    semantic_result = None
    async with ProcessingStep(
      name="Semantic Memory Coordinator agent",
      step_type="run",
    ) as step:
      async for (
        response
      ) in self.semantic_memory.process(message):
        if not response.metadata.get("streaming"):
          logger.trace(
            f"Raw semantic results obtained: {response}"
          )

          semantic_result = (
            SemanticMemoryResult.model_validate_json(
              response.content
            )
          )

          # Add both retrieval and storage results to metadata
          message.metadata["retrieved_context"] = {
            "content": semantic_result.content,
            "relevance": semantic_result.relevance,
            "lower_relevance_results": semantic_result.lower_relevance_results,
          }

          if semantic_result.id:  # If storage occurred
            message.metadata["stored_knowledge"] = {
              "id": semantic_result.id,
              "action": semantic_result.action,
              "reason": semantic_result.reason,
            }

          # Show consolidated results in step
          await step.show_response(
            Response(
              content=dedent(f"""
```markdown
# Semantic Memory Results:

## Retrieved Context:
- Content: {semantic_result.content if semantic_result.content else 'None'}
- Relevance: {semantic_result.relevance if semantic_result.relevance else 'N/A'}
- Additional Results: {len(semantic_result.lower_relevance_results) if semantic_result.lower_relevance_results else 0}

## Storage Results:
- ID: {semantic_result.id if semantic_result.id else 'No storage'}
- Action: {semantic_result.action if semantic_result.action else 'None'}
- Reason: {semantic_result.reason if semantic_result.reason else 'N/A'}
```""").strip(),
              metadata=message.metadata,
            )
          )

    # Finally, let working memory specialist update workspace

    # if this is a new episode, get fresh template

    # Use a new message that only has the latest user message and metadata needed.
    # This ensures the LLM doesn't get distracted by the conversation history.
    metadata = {
      "is_new_episode": message.metadata.get(
        "is_new_episode"
      ),
    }
    if message.metadata.get("is_new_episode"):
      metadata["current_workspace"] = (
        workspace_manager.get_workspace_template(
          message.metadata["shared_workspace"],
        )
      )
    else:
      metadata["current_workspace"] = message.metadata[
        "current_workspace"
      ]
    if message.metadata.get("preserve_context"):
      metadata["preserve_context"] = (
        message.metadata.get("preserve_context")
      )
    if message.metadata.get("retrieved_context"):
      metadata["retrieved_context"] = (
        message.metadata.get("retrieved_context")
      )

    working_memory_message = Message(
      content=message.content,
      metadata=metadata,
    )

    working_memory_result = None
    async with ProcessingStep(
      name="Working Memory agent",
      step_type="run",
    ) as step:
      async for (
        response
      ) in self.working_memory.process(
        working_memory_message
      ):
        if not response.metadata.get("streaming"):
          logger.trace(
            f"Working memory results obtained: {response}"
          )
          working_memory_result = (
            WorkspaceUpdateResult.model_validate_json(
              response.content
            )
          )
          await step.show_response(
            Response(
              content=f"```markdown\n{working_memory_result.updated_workspace}\n```",
              metadata=message.metadata,
            )
          )

    # Update the actual workspace file
    logger.info("Saving updated content to workspace.")
    workspace_manager.save_workspace(
      message.metadata["shared_workspace"],
      working_memory_result.updated_workspace,
    )

    # Memory operations are complete, yield the result of
    # the updated workspacce as a response
    yield Response(
      content=working_memory_result.updated_workspace,
      metadata=message.metadata,
    )
