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
The agent generates validation analyses in markdown format and updates the shared agency
workspace directly. This allows use of simpler LLMs that don't support tool calling
while maintaining the structured validation process."""

from collections.abc import AsyncIterator
from pathlib import Path

from loguru import logger

from winston.core.agent import (
  BaseAgent,
  Message,
  Response,
)
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System
from winston.core.workspace import WorkspaceManager

from .constants import AGENCY_WORKSPACE_KEY


class ValidationAgent(BaseAgent):
  """Evaluates test results and validates hypotheses."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = WorkspaceManager()

  def _update_workspace(
    self,
    workspace_content: str,
    validation_content: str,
  ) -> str:
    """Update the workspace with new content.

    The LLM has full autonomy to structure the workspace as needed.

    Parameters
    ----------
    workspace_content : str
        Current workspace content (not used in freeform mode)
    validation_content : str
        New content to replace the entire workspace

    Returns
    -------
    str
        Updated workspace content
    """
    logger.debug(
      f"Original workspace content: {workspace_content}"
    )
    logger.debug(f"New content: {validation_content}")

    # Simply return the new content as the complete workspace
    return validation_content

  def _update_workspace_and_respond(
    self,
    workspace_content: str,
    content: str,
    agency_workspace: Path,
  ) -> Response:
    """Update workspace with new content and create final response.

    Parameters
    ----------
    workspace_content : str
        Current workspace content (not used in freeform mode)
    content : str
        New content to replace the entire workspace
    agency_workspace : Path
        Path to agency workspace

    Returns
    -------
    Response
        Final non-streaming response
    """
    # Save the new content directly to the workspace
    self.workspace_manager.save_workspace(
      agency_workspace, content
    )
    logger.debug("Saved updated workspace")

    # Return final non-streaming response
    return Response(
      content=content,
      metadata={"streaming": False},
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process with workspace-based validation."""
    # Get agency workspace path from message
    agency_workspace = Path(
      message.metadata[AGENCY_WORKSPACE_KEY]
    )

    # Load workspace content
    workspace_content = (
      self.workspace_manager.load_workspace(
        agency_workspace
      )
    )

    # Track accumulated content from streaming responses
    accumulated_content: list[str] = []

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

      # Handle non-streaming response
      yield self._update_workspace_and_respond(
        workspace_content,
        response.content,
        agency_workspace,
      )
      return

    # If we only got streaming responses, send a final non-streaming response
    if accumulated_content:
      final_content = "".join(accumulated_content)
      yield self._update_workspace_and_respond(
        workspace_content,
        final_content,
        agency_workspace,
      )
