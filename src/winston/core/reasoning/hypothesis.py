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
The agent generates hypotheses in markdown format and updates the shared agency
workspace directly. This allows use of simpler LLMs that don't support tool calling
while maintaining the structured hypothesis generation process."""

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


class HypothesisAgent(BaseAgent):
  """Generates hypotheses informed by workspace state."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = WorkspaceManager()

  def _update_hypotheses_section(
    self,
    workspace_content: str,
    hypotheses_content: str,
  ) -> str:
    """Update the Generated Hypotheses section in the workspace.

    Parameters
    ----------
    workspace_content : str
        Current workspace content
    hypotheses_content : str
        New hypotheses content to insert

    Returns
    -------
    str
        Updated workspace content with new hypotheses section
    """
    logger.debug(
      f"Original workspace content: {workspace_content}"
    )
    logger.debug(
      f"New hypotheses content: {hypotheses_content}"
    )

    # Find the section
    start = workspace_content.find(
      "## Generated Hypotheses"
    )
    if start == -1:
      # Add new section if not found
      logger.debug(
        "No Generated Hypotheses section found, adding new one"
      )
      return (
        workspace_content
        + "\n\n## Generated Hypotheses\n\n"
        + hypotheses_content
      )

    # Find the next section to determine where this section ends
    end = workspace_content.find("\n##", start + 2)
    if end == -1:
      end = len(workspace_content)

    logger.debug(
      f"Found Generated Hypotheses section from {start} to {end}"
    )
    logger.debug(
      f"Original section content: {workspace_content[start:end]}"
    )

    # Replace the entire section with new content
    updated = (
      workspace_content[:start]
      + "## Generated Hypotheses\n\n"
      + hypotheses_content
      + "\n\n"
      + workspace_content[end:]
    )

    logger.debug(f"Final updated content: {updated}")
    return updated

  def _update_workspace_and_respond(
    self,
    workspace_content: str,
    content: str,
    agency_workspace: Path,
  ) -> Response:
    """Update workspace with new content and create response.

    Parameters
    ----------
    workspace_content : str
        Current workspace content
    content : str
        New content to add
    agency_workspace : Path
        Path to workspace file

    Returns
    -------
    Response
        Response with updated content
    """
    # Update workspace content
    updated_content = self._update_hypotheses_section(
      workspace_content,
      content,
    )
    self.workspace_manager.save_workspace(
      agency_workspace,
      updated_content,
    )

    # Return response with proper metadata flags
    return Response(
      content=updated_content,
      metadata={
        "reasoning_stage": True,
        "specialist_type": "hypothesis",
        "workspace": str(agency_workspace),
      },
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process with workspace-based hypothesis generation."""
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
