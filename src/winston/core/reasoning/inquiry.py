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
The agent generates test designs in markdown format and updates the shared agency
workspace directly. This allows use of simpler LLMs that don't support tool calling
while maintaining the structured test design process."""

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


class InquiryAgent(BaseAgent):
  """Designs validation tests informed by workspace state."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = WorkspaceManager()

  def _update_investigation_section(
    self,
    workspace_content: str,
    investigation_content: str,
  ) -> str:
    """Update the Investigation Design section in the workspace.

    Parameters
    ----------
    workspace_content : str
        Current workspace content
    investigation_content : str
        New investigation content to insert

    Returns
    -------
    str
        Updated workspace content with new investigation section
    """
    logger.debug(
      f"Original workspace content: {workspace_content}"
    )
    logger.debug(
      f"New investigation content: {investigation_content}"
    )

    # Find the section
    start = workspace_content.find(
      "## Investigation Design"
    )
    if start == -1:
      # Add new section if not found
      logger.debug(
        "No Investigation Design section found, adding new one"
      )
      return (
        workspace_content
        + "\n\n## Investigation Design\n\n"
        + investigation_content
      )

    # Find the next section to determine where this section ends
    end = workspace_content.find("\n##", start + 2)
    if end == -1:
      end = len(workspace_content)

    logger.debug(
      f"Found Investigation Design section from {start} to {end}"
    )
    logger.debug(
      f"Original section content: {workspace_content[start:end]}"
    )

    # Replace the entire section with new content
    updated = (
      workspace_content[:start]
      + "## Investigation Design\n\n"
      + investigation_content
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
    """Update workspace with new content and create final response.

    Parameters
    ----------
    workspace_content : str
        Current workspace content
    content : str
        Content to add to workspace
    agency_workspace : Path
        Path to agency workspace

    Returns
    -------
    Response
        Final non-streaming response
    """
    # Update workspace with content
    updated_content = (
      self._update_investigation_section(
        workspace_content,
        content,
      )
    )
    logger.debug("Workspace updated with new content")

    self.workspace_manager.save_workspace(
      agency_workspace, updated_content
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
    """Process with workspace-based test design."""
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
