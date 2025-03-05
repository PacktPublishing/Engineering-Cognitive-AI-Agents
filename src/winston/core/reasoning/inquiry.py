"""Inquiry Agent: Specialist agent for solution validation test design.

The Inquiry Agent is a key specialist in Winston's enhanced reasoning system,
responsible for designing tests to validate proposed solutions. It operates
as part of a coordinated reasoning system alongside Hypothesis and Validation agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by designing
empirical tests to reduce uncertainty. Through active inference, it:
1. Analyzes hypotheses to identify key validation points
2. Designs specific, practical tests
3. Defines clear success criteria
4. Enables systematic validation

Design Philosophy:
The agent implements systematic test design by:
1. Analyzing hypotheses and their test criteria from workspace content
2. Drawing on relevant testing patterns through memory integration
3. Generating practical validation approaches
4. Providing clear execution guidelines

Implementation Note:
The agent generates test designs in markdown format and returns the results
to the coordinator, which manages the workspace state centrally."""

from collections.abc import AsyncIterator

from loguru import logger

from winston.core.agent import (
  BaseAgent,
  Message,
  Response,
)
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System


class InquiryAgent(BaseAgent):
  """Designs validation tests informed by workspace state."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process with inquiry design."""
    # Track accumulated content from streaming responses
    accumulated_content: list[str] = []

    # Extract workspace content from message metadata
    workspace_content = message.metadata.get(
      "workspace_content", ""
    )

    # Generate test designs using LLM
    async for response in self._handle_conversation(
      Message(
        content=message.content,
        metadata={
          "workspace_content": workspace_content
        },
      )
    ):
      if response.metadata.get("streaming"):
        accumulated_content.append(response.content)
        yield response
        continue

      logger.debug("Processing non-streaming response")
      logger.debug(
        f"Response content: {response.content}"
      )

      # Return response with proper metadata flags
      yield Response(
        content=response.content,
        metadata={
          "streaming": False,
          "specialist_type": "inquiry",
        },
      )
      return

    # If we only got streaming responses, send a final non-streaming response
    if accumulated_content:
      final_content = "".join(accumulated_content)
      yield Response(
        content=final_content,
        metadata={
          "streaming": False,
          "specialist_type": "inquiry",
        },
      )
