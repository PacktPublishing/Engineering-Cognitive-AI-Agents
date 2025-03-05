# src/winston/core/workspace.py
import difflib
import json
from pathlib import Path
from textwrap import dedent
from typing import (
  Any,
  ClassVar,
  Dict,
  List,
  Optional,
  Tuple,
  Union,
)

from jinja2 import Template
from loguru import logger

from winston.core.messages import Message
from winston.core.protocols import Agent

DEFAULT_INITIAL_TEMPLATE = dedent("""
# User Preferences

[Record user habits, likes, dislikes, and stated preferences]

# Relevant Context

[Store background information, relationships, and contextual details that don't fit above]
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

Message Type: {{ msg_type }}
Update Content:
```markdown
{{ content_format }}
```

Current Workspace:
```markdown
{{ workspace }}
```
""").strip()


DEFAULT_EDIT_DELTA_TEMPLATE = dedent("""
You are an expert editor. Your task is to generate precise edit instructions for modifying a file based on a specific task.

# File Content
```
{{ file_content }}
```

# Task
{{ task }}

# Instructions
Generate a list of edit operations that, when applied to the file, will accomplish the task. Each operation should be one of:
1. INSERT: Add new content after a specific line
2. DELETE: Remove one or more lines
3. REPLACE: Replace one or more lines with new content

Format your response as a JSON array of edit operations, where each operation is an object with the following properties:
- "action": "insert", "delete", or "replace"
- "location": For "insert", the line number after which to insert (0-based); for "delete" and "replace", a tuple [start, end] of line numbers (0-based, inclusive)
- "content": For "insert" and "replace", the content to insert or replace with

Example:
```json
[
  {"action": "insert", "location": 5, "content": "New line to be inserted"},
  {"action": "delete", "location": [10, 12]},
  {"action": "replace", "location": [15, 17], "content": "New content to replace the old"}
]
```

Ensure your edits are precise and minimal, changing only what's necessary to accomplish the task.
""").strip()


DEFAULT_EDIT_VALIDATION_TEMPLATE = dedent("""
You are an expert validator. Your task is to verify that edits applied to a file have been correctly implemented and that the task has been accomplished.

# Original File
```
{{ original_content }}
```

# Edited File
```
{{ edited_content }}
```

# Task
{{ task }}

# Edit Operations Applied
```json
{{ edit_operations }}
```

# Instructions
Validate that:
1. All edit operations have been correctly applied
2. The task has been accomplished
3. No unintended changes were made

Provide your assessment in the following format:
```json
{
  "valid": true/false,
  "issues": ["issue1", "issue2", ...],
  "task_accomplished": true/false,
  "comments": "Any additional comments or explanations"
}
```

If there are no issues, the "issues" array should be empty.
""").strip()


# Define EditOperation type
class EditOperation:
  """Represents a single edit operation to be applied to a file."""

  def __init__(
    self,
    action: str,
    location: Union[int, List[int], Tuple[int, int]],
    content: Optional[str] = None,
  ):
    """Initialize an edit operation.

    Parameters
    ----------
    action : str
        The type of edit operation: "insert", "delete", or "replace"
    location : Union[int, List[int], Tuple[int, int]]
        For "insert", the line number after which to insert (0-based);
        for "delete" and "replace", a tuple or list [start, end] of line numbers (0-based, inclusive)
    content : Optional[str], optional
        For "insert" and "replace", the content to insert or replace with, by default None
    """
    self.action = action
    self.location = location
    self.content = (
      content if content is not None else ""
    )

  def to_dict(self) -> Dict[str, Any]:
    """Convert the edit operation to a dictionary.

    Returns
    -------
    Dict[str, Any]
        Dictionary representation of the edit operation
    """
    result = {
      "action": self.action,
      "location": self.location,
    }
    # Since we initialize content to empty string if None, it's never None here
    # But we only include it in the result if it's not an empty string
    if self.content:
      result["content"] = self.content
    return result

  @classmethod
  def from_dict(
    cls, data: Dict[str, Any]
  ) -> "EditOperation":
    """Create an edit operation from a dictionary.

    Parameters
    ----------
    data : Dict[str, Any]
        Dictionary representation of an edit operation

    Returns
    -------
    EditOperation
        The created edit operation
    """
    return cls(
      action=data["action"],
      location=data["location"],
      content=data.get("content"),
    )


class WorkspaceManager:
  """Singleton manager for all workspaces and file editing operations."""

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
    logger.trace(
      "Initializing new WorkspaceManager instance"
    )
    self._workspaces: dict[Path, str] = {}
    self._templates: dict[str, str] = {}
    self._workspace_owners: dict[Path, str] = {}
    self._edit_history: dict[
      Path, List[List[EditOperation]]
    ] = {}

  def initialize_workspace(
    self,
    workspace_path: Path,
    content: str | None = None,
    template: str | None = None,
    owner_id: str | None = None,
  ) -> None:
    """Register workspace metadata without creating the file.

    This method only registers the workspace owner and template information.
    The actual file will be created lazily when the workspace is first accessed
    for reading or writing.
    """
    if owner_id:
      self._workspace_owners[workspace_path] = owner_id
    if template and owner_id:
      self._templates[owner_id] = template

    # Only create the file if content is explicitly provided
    if (
      content is not None
      and not workspace_path.exists()
    ):
      logger.info(
        f"Creating new workspace at {workspace_path} with provided content"
      )
      workspace_path.parent.mkdir(
        parents=True, exist_ok=True
      )
      try:
        workspace_path.write_text(content)
        logger.debug(
          f"Workspace initialized successfully at {workspace_path}"
        )
      except Exception as e:
        logger.exception(
          f"Failed to create workspace at {workspace_path}: {e}"
        )
        raise

  def get_workspace_template(
    self, workspace_path: Path
  ) -> str:
    """Get template for a workspace."""
    owner_id = self._workspace_owners.get(
      workspace_path
    )
    if owner_id:
      return self._templates.get(
        owner_id, DEFAULT_INITIAL_TEMPLATE
      )
    return DEFAULT_INITIAL_TEMPLATE

  def get_workspace_owner(
    self, workspace_path: Path
  ) -> str | None:
    """Get the owner ID for a workspace."""
    return self._workspace_owners.get(workspace_path)

  def load_workspace(
    self,
    workspace_path: Path,
  ) -> str:
    """Load workspace content, creating it on-demand if needed."""
    logger.debug(
      f"Loading workspace from {workspace_path}"
    )
    if workspace_path not in self._workspaces:
      try:
        # Check if the file exists
        if not workspace_path.exists():
          # Register the workspace metadata without creating the file
          self.initialize_workspace(workspace_path)

          # Now create the file on-demand since we're actually accessing it
          logger.info(
            f"Creating workspace on-demand at {workspace_path}"
          )
          workspace_path.parent.mkdir(
            parents=True, exist_ok=True
          )
          workspace_path.write_text(
            self.get_workspace_template(workspace_path)
          )
          logger.debug(
            f"Workspace created on-demand at {workspace_path}"
          )

        # Read and cache the workspace content
        self._workspaces[workspace_path] = (
          workspace_path.read_text()
        )
        logger.trace(
          f"Workspace loaded and cached: {workspace_path}"
        )
      except Exception as e:
        logger.exception(
          f"Failed to load workspace {workspace_path}: {e}"
        )
        raise
    return self._workspaces[workspace_path]

  def save_workspace(
    self,
    workspace_path: Path,
    content: str,
  ) -> None:
    """Save workspace content to file.

    Parameters
    ----------
    workspace_path : Path
        Path to workspace file
    content : str
        Content to save
    """
    logger.debug(
      f"Saving workspace to: {workspace_path}"
    )
    logger.debug(
      f"Content to save: {content[:200]}..."
    )
    workspace_path.parent.mkdir(
      parents=True, exist_ok=True
    )
    workspace_path.write_text(content)
    self._workspaces[workspace_path] = (
      content  # Update the cache
    )
    logger.debug("Workspace saved successfully")

  async def update_workspace(
    self,
    workspace_path: Path,
    message: Message,
    agent: Agent,
    update_template: str | None = None,
    update_category: str | None = None,
  ) -> str:
    """Update workspace with new interaction."""
    logger.info(
      f"Updating workspace: {workspace_path}"
    )
    logger.debug(
      f"Update category: {update_category}, Message: {message}"
    )

    try:
      workspace = self.load_workspace(workspace_path)

      if update_category is None:
        update_category = "Interaction"

      content_format = (
        message.content
        if update_category != "Interaction"
        else f"User: {message.content}"
      )

      template = Template(
        update_template or DEFAULT_UPDATE_TEMPLATE
      )
      update_prompt = template.render(
        msg_type=update_category.replace("_", " "),
        content_format=content_format,
        workspace=workspace,
      ).strip()

      logger.trace(
        f"Generated update prompt: {update_prompt}"
      )

      response = await agent.generate_response(
        Message(
          content=update_prompt,
          metadata=message.metadata,
        )
      )
      logger.debug(
        f"Update response received: {response.content}"
      )

      self.save_workspace(
        workspace_path, response.content
      )
      logger.debug(
        "Workspace update completed successfully"
      )
      return response.content

    except Exception as e:
      logger.exception(
        f"Failed to update workspace {workspace_path}: {e}"
      )
      raise

  async def generate_edit_delta(
    self,
    file_path: Path,
    task: str,
    agent: Agent,
    delta_template: str | None = None,
  ) -> List[EditOperation]:
    """Generate edit instructions (delta) for a file based on a task.

    Parameters
    ----------
    file_path : Path
        Path to the file to edit
    task : str
        Description of the edit task to perform
    agent : Agent
        Agent to use for generating the delta
    delta_template : str | None, optional
        Custom template for generating the delta, by default None

    Returns
    -------
    List[EditOperation]
        List of edit operations to apply
    """
    logger.info(
      f"Generating edit delta for file: {file_path}"
    )
    logger.debug(f"Task: {task}")

    try:
      # Read the file content
      file_content = file_path.read_text()

      # Prepare the prompt
      template = Template(
        delta_template or DEFAULT_EDIT_DELTA_TEMPLATE
      )
      delta_prompt = template.render(
        file_content=file_content,
        task=task,
      ).strip()

      logger.trace(
        f"Generated delta prompt: {delta_prompt}"
      )

      # Get the response from the agent
      response = await agent.generate_response(
        Message(
          content=delta_prompt,
        )
      )

      # Parse the response as JSON
      try:
        # Extract JSON from the response if it's wrapped in markdown code blocks
        content = response.content
        if "```json" in content:
          content = (
            content.split("```json")[1]
            .split("```")[0]
            .strip()
          )
        elif "```" in content:
          content = (
            content.split("```")[1]
            .split("```")[0]
            .strip()
          )

        edit_operations_data = json.loads(content)
        edit_operations = [
          EditOperation.from_dict(op)
          for op in edit_operations_data
        ]

        logger.debug(
          f"Generated {len(edit_operations)} edit operations"
        )

        return edit_operations

      except json.JSONDecodeError as e:
        logger.error(
          f"Failed to parse edit operations as JSON: {e}"
        )
        logger.error(
          f"Response content: {response.content}"
        )
        raise

    except Exception as e:
      logger.exception(
        f"Failed to generate edit delta for {file_path}: {e}"
      )
      raise

  def apply_edit_delta(
    self,
    file_path: Path,
    edit_operations: List[EditOperation],
    output_path: Path | None = None,
  ) -> str:
    """Apply edit operations to a file.

    Parameters
    ----------
    file_path : Path
        Path to the file to edit
    edit_operations : List[EditOperation]
        List of edit operations to apply
    output_path : Path | None, optional
        Path to save the edited file, by default None (overwrites the original)

    Returns
    -------
    str
        The content of the edited file
    """
    logger.info(
      f"Applying edit delta to file: {file_path}"
    )
    logger.debug(
      f"Number of edit operations: {len(edit_operations)}"
    )

    try:
      # Read the file content
      file_content = file_path.read_text()
      lines = file_content.splitlines()

      # Track original line numbers for each line in the current file
      # This helps handle line number changes due to insertions/deletions
      original_line_numbers = list(range(len(lines)))

      # Apply edit operations
      for op in edit_operations:
        if op.action == "insert":
          # For insert, we need the index in the current file that corresponds
          # to the original line number specified in the operation
          insert_after = op.location
          if not isinstance(insert_after, int):
            logger.warning(
              f"Insert location is not an integer: {insert_after}. Using 0."
            )
            insert_after = 0

          # Find the index in the current file
          try:
            current_index = (
              original_line_numbers.index(insert_after)
            )
          except ValueError:
            # If the line number is not found, insert at the end
            current_index = len(lines) - 1

          # Insert the content
          new_content_lines = (
            op.content.splitlines()
            if op.content
            else []
          )
          lines[
            current_index + 1 : current_index + 1
          ] = new_content_lines

          # Update original line numbers
          # Lines after the insertion point need to be shifted
          original_line_numbers[
            current_index + 1 : current_index + 1
          ] = [-1] * len(new_content_lines)

        elif op.action == "delete":
          # For delete, we need to find all indices in the current file
          # that correspond to original line numbers in the specified range
          if (
            isinstance(op.location, (list, tuple))
            and len(op.location) == 2
          ):
            start, end = op.location
          else:
            logger.warning(
              f"Delete location is not a valid range: {op.location}. Skipping."
            )
            continue

          # Find indices to delete
          indices_to_delete = [
            i
            for i, orig_line_num in enumerate(
              original_line_numbers
            )
            if orig_line_num >= start
            and orig_line_num <= end
          ]

          # Delete lines in reverse order to avoid index shifting
          for i in sorted(
            indices_to_delete, reverse=True
          ):
            del lines[i]
            del original_line_numbers[i]

        elif op.action == "replace":
          # For replace, first delete the lines, then insert the new content
          if (
            isinstance(op.location, (list, tuple))
            and len(op.location) == 2
          ):
            start, end = op.location
          else:
            logger.warning(
              f"Replace location is not a valid range: {op.location}. Skipping."
            )
            continue

          # Find indices to replace
          indices_to_replace = [
            i
            for i, orig_line_num in enumerate(
              original_line_numbers
            )
            if orig_line_num >= start
            and orig_line_num <= end
          ]

          if not indices_to_replace:
            logger.warning(
              f"No lines found to replace for operation: {op.to_dict()}"
            )
            continue

          # Get the index where replacement should start
          replace_start_index = min(indices_to_replace)

          # Delete lines in reverse order
          for i in sorted(
            indices_to_replace, reverse=True
          ):
            del lines[i]
            del original_line_numbers[i]

          # Insert new content
          new_content_lines = (
            op.content.splitlines()
            if op.content
            else []
          )
          lines[
            replace_start_index:replace_start_index
          ] = new_content_lines
          original_line_numbers[
            replace_start_index:replace_start_index
          ] = [-1] * len(new_content_lines)

      # Join lines back into a string
      edited_content = "\n".join(lines)

      # Save the edited content
      if output_path:
        output_path.parent.mkdir(
          parents=True, exist_ok=True
        )
        output_path.write_text(edited_content)
        logger.debug(
          f"Edited file saved to: {output_path}"
        )
      else:
        file_path.write_text(edited_content)
        logger.debug(
          f"Original file updated: {file_path}"
        )

      # Store edit operations in history
      if file_path not in self._edit_history:
        self._edit_history[file_path] = []
      self._edit_history[file_path].append(
        edit_operations
      )

      return edited_content

    except Exception as e:
      logger.exception(
        f"Failed to apply edit delta to {file_path}: {e}"
      )
      raise

  async def validate_edit(
    self,
    original_content: str,
    edited_content: str,
    task: str,
    edit_operations: List[EditOperation],
    agent: Agent,
    validation_template: str | None = None,
  ) -> Dict[str, Any]:
    """Validate that edits were applied correctly and the task was accomplished.

    Parameters
    ----------
    original_content : str
        Original content of the file
    edited_content : str
        Edited content of the file
    task : str
        Description of the edit task
    edit_operations : List[EditOperation]
        List of edit operations that were applied
    agent : Agent
        Agent to use for validation
    validation_template : str | None, optional
        Custom template for validation, by default None

    Returns
    -------
    Dict[str, Any]
        Validation result with keys:
        - valid: bool - Whether the edits were applied correctly
        - issues: List[str] - List of issues found
        - task_accomplished: bool - Whether the task was accomplished
        - comments: str - Additional comments
    """
    logger.info("Validating edit")

    try:
      # Prepare the prompt
      template = Template(
        validation_template
        or DEFAULT_EDIT_VALIDATION_TEMPLATE
      )

      # Convert edit operations to JSON
      edit_operations_json = json.dumps(
        [op.to_dict() for op in edit_operations]
        if edit_operations
        else [],
        indent=2,
      )

      validation_prompt = template.render(
        original_content=original_content,
        edited_content=edited_content,
        task=task,
        edit_operations=edit_operations_json,
      ).strip()

      logger.trace(
        f"Generated validation prompt: {validation_prompt}"
      )

      # Get the response from the agent
      response = await agent.generate_response(
        Message(
          content=validation_prompt,
        )
      )

      # Parse the response as JSON
      try:
        # Extract JSON from the response if it's wrapped in markdown code blocks
        content = response.content
        if "```json" in content:
          content = (
            content.split("```json")[1]
            .split("```")[0]
            .strip()
          )
        elif "```" in content:
          content = (
            content.split("```")[1]
            .split("```")[0]
            .strip()
          )

        validation_result = json.loads(content)

        logger.debug(
          f"Validation result: {validation_result}"
        )

        return validation_result

      except json.JSONDecodeError as e:
        logger.error(
          f"Failed to parse validation result as JSON: {e}"
        )
        logger.error(
          f"Response content: {response.content}"
        )

        # Return a default validation result
        return {
          "valid": False,
          "issues": [
            f"Failed to parse validation result: {e}"
          ],
          "task_accomplished": False,
          "comments": "Validation failed due to parsing error",
        }

    except Exception as e:
      logger.exception(f"Failed to validate edit: {e}")
      return {
        "valid": False,
        "issues": [f"Validation error: {str(e)}"],
        "task_accomplished": False,
        "comments": "Validation failed due to an error",
      }

  def get_edit_diff(
    self,
    original_content: str,
    edited_content: str,
  ) -> str:
    """Generate a unified diff between original and edited content.

    Parameters
    ----------
    original_content : str
        Original content
    edited_content : str
        Edited content

    Returns
    -------
    str
        Unified diff
    """
    original_lines = original_content.splitlines()
    edited_lines = edited_content.splitlines()

    diff = difflib.unified_diff(
      original_lines,
      edited_lines,
      lineterm="",
      n=3,  # Context lines
    )

    return "\n".join(diff)

  async def edit_file(
    self,
    file_path: Path,
    task: str,
    agent: Agent,
    output_path: Path | None = None,
    delta_template: str | None = None,
    validation_template: str | None = None,
  ) -> Dict[str, Any]:
    """Edit a file based on a task, applying and validating changes.

    This is a convenience method that combines generate_edit_delta,
    apply_edit_delta, and validate_edit.

    Parameters
    ----------
    file_path : Path
        Path to the file to edit
    task : str
        Description of the edit task
    agent : Agent
        Agent to use for generating the delta and validation
    output_path : Path | None, optional
        Path to save the edited file, by default None (overwrites the original)
    delta_template : str | None, optional
        Custom template for generating the delta, by default None
    validation_template : str | None, optional
        Custom template for validation, by default None

    Returns
    -------
    Dict[str, Any]
        Result with keys:
        - edited_content: str - The edited content
        - edit_operations: List[Dict] - The edit operations applied
        - validation: Dict - The validation result
        - diff: str - Unified diff between original and edited content
    """
    logger.info(f"Editing file: {file_path}")
    logger.debug(f"Task: {task}")

    try:
      # Read the original content
      original_content = file_path.read_text()

      # Generate edit delta
      edit_operations = await self.generate_edit_delta(
        file_path,
        task,
        agent,
        delta_template,
      )

      if not edit_operations:
        logger.warning(
          "No edit operations were generated"
        )
        edit_operations = []

      # Apply edit delta
      edited_content = self.apply_edit_delta(
        file_path,
        edit_operations,
        output_path,
      )

      # Validate edit
      validation_result = await self.validate_edit(
        original_content,
        edited_content,
        task,
        edit_operations,
        agent,
        validation_template,
      )

      # Generate diff
      diff = self.get_edit_diff(
        original_content,
        edited_content,
      )

      return {
        "edited_content": edited_content,
        "edit_operations": [
          op.to_dict() for op in edit_operations
        ],
        "validation": validation_result,
        "diff": diff,
      }

    except Exception as e:
      logger.exception(
        f"Failed to edit file {file_path}: {e}"
      )
      raise
