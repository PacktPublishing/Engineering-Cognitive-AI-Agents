"""Validation Agent: Specialist agent for evaluating test results and validating hypotheses.

The Validation Agent is a key specialist in Winston's enhanced reasoning system,
responsible for evaluating test results against hypotheses. It operates
as part of a coordinated reasoning system alongside Hypothesis and Inquiry agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by evaluating
empirical evidence to update beliefs. Through active inference, it:
1. Analyzes test results against predictions
2. Updates confidence levels based on evidence
3. Identifies needed refinements
4. Guides learning from outcomes

Design Philosophy:
The agent implements systematic validation by:
1. Analyzing test results against success criteria
2. Evaluating evidence quality and relevance
3. Updating hypothesis confidence levels
4. Identifying refinement opportunities

Implementation Note:
The agent generates validation analyses in markdown format and returns the results
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


class ValidationAgent(BaseAgent):
  """Evaluates test results and validates hypotheses."""

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
    """Process with validation analysis."""
    # Track accumulated content from streaming responses
    accumulated_content: list[str] = []

    # Extract workspace content from message metadata
    workspace_content = message.metadata.get(
      "workspace_content", ""
    )

    # Generate validation analysis using LLM
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
          "specialist_type": "validation",
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
          "specialist_type": "validation",
        },
      )
