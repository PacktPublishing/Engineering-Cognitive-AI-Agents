# src/winston/core/workspace.py
from pathlib import Path
from textwrap import dedent
from typing import ClassVar, Union

from winston.core.messages import Message
from winston.core.protocols import Agent

DEFAULT_INITIAL_TEMPLATE = dedent("""
# Cognitive Workspace

## User Preferences

## Recent Interactions

## Current Context

## Working Memory
""").strip()


DEFAULT_UPDATE_TEMPLATE = dedent("""
Update the `Current Workspace` to incorporate the new information effectively.

# Steps

1. **Integrate Key Insights**: Extract critical insights and relationships from `Update Content` and integrate them into the existing workspace.
2. **Specific Updates**:
   - If `Message Type` is "Interaction": Update the relevant workspace sections, such as context and preferences.
   - For other types, create or append sections as necessary to reflect the new content appropriately (i.e., if it is new, retain all details as provided)
3. **Preserve Structure**: Maintain existing sections, formatting, and overall organization to ensure clarity and conciseness.

# Output Format

Provide the updated workspace in a clear and structured markdown format, maintaining existing layout and introducing necessary modifications or additions to incorporate new content.

# Examples

**Example 1**

- **Input**:
  - `msg_type`: "Interaction"
  - `content_format`: "User interacted with new features."
  - `workspace`: "## Existing Context..."

- **Output**:
  - `workspace`: "## Existing Context... \n\n### Updated Features...\n- User interacted with new features...\n"

(Note: realistic examples should include detailed content and integration reflecting the actual updates for clarity and completeness.)

Message Type: {msg_type}
Update Content:
```markdown
{content_format}
```

Current Workspace:
```markdown
{workspace}
```
""").strip()


class WorkspaceManager:
  """Singleton manager for all workspaces."""

  _instance: ClassVar[
    Union["WorkspaceManager", None]
  ] = None

  def __new__(cls) -> "WorkspaceManager":
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance._initialize()
    return cls._instance

  def _initialize(self) -> None:
    """Initialize the workspace manager."""
    self._workspaces: dict[Path, str] = {}

  def initialize_workspace(
    self,
    workspace_path: Path,
    content: str | None = None,
  ) -> None:
    """Initialize a workspace if it doesn't exist."""
    if not workspace_path.exists():
      workspace_path.parent.mkdir(
        parents=True, exist_ok=True
      )
      workspace_path.write_text(
        content or DEFAULT_INITIAL_TEMPLATE
      )

  def load_workspace(
    self,
    workspace_path: Path,
  ) -> str:
    """Load workspace content, initializing if needed."""
    if workspace_path not in self._workspaces:
      self.initialize_workspace(workspace_path)
      self._workspaces[workspace_path] = (
        workspace_path.read_text()
      )
    return self._workspaces[workspace_path]

  def save_workspace(
    self,
    workspace_path: Path,
    content: str,
  ) -> None:
    """Save workspace content."""
    workspace_path.write_text(content)
    self._workspaces[workspace_path] = content

  async def update_workspace(
    self,
    workspace_path: Path,
    message: Message,
    agent: Agent,
    update_template: str | None = None,
  ) -> str:
    """Update workspace with new interaction.

    Parameters
    ----------
    workspace_path : Path
        Path to the workspace to update
    message : Message
        The new message to process
    agent : Agent
        Agent to use for generating the update

    Returns
    -------
    str
        The updated workspace content
    """
    print(f"Updating workspace: {workspace_path}")
    workspace = self.load_workspace(workspace_path)

    # Base prompt template

    # Dynamic content formatting based on message type
    msg_type = message.metadata.get(
      "type", "Interaction"
    )

    content_format = (
      message.content
      if msg_type != "Interaction"
      else f"User: {message.content}"
    )

    update_prompt = dedent(
      (
        update_template or DEFAULT_UPDATE_TEMPLATE
      ).format(
        msg_type=msg_type.replace("_", " "),
        content_format=content_format,
        workspace=workspace,
      )
    ).strip()

    response = await agent.generate_response(
      Message(
        content=update_prompt,
        metadata={"type": "Workspace Update"},
      )
    )
    self.save_workspace(
      workspace_path, response.content
    )
    return response.content
