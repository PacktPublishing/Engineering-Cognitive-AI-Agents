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
    update_prompt = dedent(
      f"""
        Given this new interaction:
        User: {message.content}

        And the current workspace:
        {workspace}

        Update the workspace to include this interaction and any learned information.
        Maintain existing sections and formatting.
        Extract and update user preferences if any are implied.
        Keep the workspace concise and relevant.
      """
    ).strip()

    response = await agent.generate_response(
      Message(
        content=update_prompt,
        metadata={"type": "workspace_update"},
      )
    )
    self.save_workspace(response.content)
    return response.content
