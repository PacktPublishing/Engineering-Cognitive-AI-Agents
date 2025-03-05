"""Hypothesis Agent: Specialist agent for solution generation and analysis.

The Hypothesis Agent is a key specialist in Winston's enhanced reasoning system,
responsible for analyzing problems and generating potential solutions. It operates
as part of a coordinated reasoning system alongside Inquiry and Validation agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by generating
testable predictions to reduce uncertainty. Through active inference, it:
1. Identifies areas of uncertainty in current understanding
2. Proposes specific, testable explanations
3. Enables empirical validation through other specialists
4. Supports learning from outcomes

Design Philosophy:
The agent implements systematic problem analysis and solution generation by:
1. Analyzing problem context and constraints from workspace content
2. Drawing on relevant past experiences through memory integration
3. Generating and prioritizing potential solutions
4. Providing clear validation criteria for testing

Implementation Note:
The agent generates hypotheses in markdown format and returns the results
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


class HypothesisAgent(BaseAgent):
  """Generates hypotheses informed by workspace state."""

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
    """Process with hypothesis generation."""
    # Track accumulated content from streaming responses
    accumulated_content: list[str] = []

    # Extract workspace content from message metadata
    workspace_content = message.metadata.get(
      "workspace_content", ""
    )

    # Generate hypotheses using LLM
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
          "reasoning_stage": True,
          "specialist_type": "hypothesis",
        },
      )
      return

    # If we only got streaming responses, send a final non-streaming response
    if accumulated_content:
      final_content = "".join(accumulated_content)
      yield Response(
        content=final_content,
        metadata={
          "reasoning_stage": True,
          "specialist_type": "hypothesis",
        },
      )
