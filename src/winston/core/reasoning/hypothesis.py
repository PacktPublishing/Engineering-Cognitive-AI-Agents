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

  def _update_workspace(
    self,
    workspace_content: str,
    hypotheses_content: str,
  ) -> str:
    """Update the workspace with new content.

    The LLM has full autonomy to structure the workspace as needed.

    Parameters
    ----------
    workspace_content : str
        Current workspace content (not used in freeform mode)
    hypotheses_content : str
        New content to replace the entire workspace

    Returns
    -------
    str
        Updated workspace content
    """
    logger.debug(
      f"Original workspace content: {workspace_content}"
    )
    logger.debug(f"New content: {hypotheses_content}")

    # Simply return the new content as the complete workspace
    return hypotheses_content

  async def _update_workspace_and_respond(
    self,
    workspace_content: str,
    content: str,
    agency_workspace: Path,
  ) -> Response:
    """Update workspace with new content and create response.

    Parameters
    ----------
    workspace_content : str
        Current workspace content (not used in freeform mode)
    content : str
        New content to replace the entire workspace
    agency_workspace : Path
        Path to workspace file

    Returns
    -------
    Response
        Response with updated content
    """
    # Check if the workspace exists
    if (
      agency_workspace.exists()
      and workspace_content.strip()
    ):
      try:
        # Generate a task description for the edit
        task = "Update the workspace with hypothesis generation results"

        # Create updated workspace content that includes the hypothesis content
        updated_content = workspace_content

        # Check if we already have a Hypothesis Generation Results section
        if (
          "# Hypothesis Generation Results"
          not in updated_content
        ):
          # Add the hypothesis results section
          updated_content += f"\n\n# Hypothesis Generation Results\n\n{content}"
        else:
          # Replace the existing hypothesis results section
          sections = updated_content.split(
            "# Hypothesis Generation Results"
          )
          updated_content = (
            sections[0]
            + "# Hypothesis Generation Results\n\n"
            + content
          )
          # Add back any sections that might have come after the hypothesis section
          if len(sections) > 2:
            for section in sections[2:]:
              updated_content += section

        # Save the updated content
        self.workspace_manager.save_workspace(
          agency_workspace, updated_content
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

      except Exception as e:
        # Fall back to direct save if update fails
        logger.warning(
          f"Workspace update failed, falling back to direct save: {e}"
        )
        self.workspace_manager.save_workspace(
          agency_workspace,
          content,
        )
    else:
      # Save the new content directly to the workspace
      self.workspace_manager.save_workspace(
        agency_workspace,
        content,
      )

    # Return response with proper metadata flags
    return Response(
      content=content,
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
      yield await self._update_workspace_and_respond(
        workspace_content,
        response.content,
        agency_workspace,
      )
      return

    # If we only got streaming responses, send a final non-streaming response
    if accumulated_content:
      final_content = "".join(accumulated_content)
      yield await self._update_workspace_and_respond(
        workspace_content,
        final_content,
        agency_workspace,
      )
