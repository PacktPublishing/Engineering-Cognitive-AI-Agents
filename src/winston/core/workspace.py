# src/winston/core/workspace.py
from pathlib import Path
from textwrap import dedent

from winston.core.messages import Message
from winston.core.protocols import Agent


class WorkspaceManager:
  def __init__(self, workspace_path: Path):
    self.workspace_path = workspace_path
    self.workspace_path.parent.mkdir(
      parents=True, exist_ok=True
    )
    self.initialize_workspace()

  def initialize_workspace(self) -> None:
    if not self.workspace_path.exists():
      self.workspace_path.write_text(
        dedent(
          """
          # Cognitive Workspace

          ## User Preferences

          ## Recent Interactions

          ## Current Context

          ## Working Memory
          """
        ).strip()
      )

  def load_workspace(self) -> str:
    return self.workspace_path.read_text()

  def save_workspace(self, content: str) -> None:
    self.workspace_path.write_text(content)

  async def update_workspace(
    self, message: Message, agent: Agent
  ) -> str:
    """Update workspace with new interaction.

    Parameters
    ----------
    message : Message
        The new message to process
    agent : Agent
        The agent to use for generating the update

    Returns
    -------
    str
        The updated workspace content
    """
    workspace = self.load_workspace()

    # Base prompt template
    base_template = """
        Given this {interaction_type}:
        {content_format}

        And the current workspace:
        {workspace}

        Update the workspace to incorporate this information:
        1. Integrate key insights and relationships identified
        2. Update relevant sections (context, preferences, etc.)
        3. Maintain existing sections and formatting
        4. Keep the workspace concise and well-organized
        """

    # Dynamic content formatting based on message type
    msg_type = message.metadata.get(
      "type", "interaction"
    )
    content_format = (
      message.content
      if msg_type != "interaction"
      else f"User: {message.content}"
    )

    update_prompt = dedent(
      base_template.format(
        interaction_type=msg_type.replace("_", " "),
        content_format=content_format,
        workspace=workspace,
      )
    ).strip()

    response = await agent.generate_response(
      Message(
        content=update_prompt,
        metadata={"type": "workspace_update"},
      )
    )
    self.save_workspace(response.content)
    return response.content
