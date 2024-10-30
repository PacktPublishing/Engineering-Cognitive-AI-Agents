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
    print(
      f"Updating workspace ({agent.id}) with message: {message.content}"
    )
    workspace = self.load_workspace()

    # Base prompt template
    base_template = """
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
"""

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
      base_template.format(
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
    self.save_workspace(response.content)
    return response.content
