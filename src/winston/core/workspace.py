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
    # Remove workspace content cache
    self._templates: dict[str, str] = {}
    self._workspace_owners: dict[Path, str] = {}
    self._edit_history: dict[
      Path, List[List[EditOperation]]
    ] = {}
    logger.debug(
      "WorkspaceManager initialized with empty collections"
    )

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
    logger.debug(
      f"Initializing workspace metadata: path={workspace_path}, "
      f"content_provided={content is not None}, "
      f"template_provided={template is not None}, "
      f"owner_id={owner_id}"
    )

    if owner_id:
      self._workspace_owners[workspace_path] = owner_id
      logger.debug(
        f"Registered owner_id={owner_id} for workspace={workspace_path}"
      )
    if template and owner_id:
      self._templates[owner_id] = template
      logger.debug(
        f"Registered template for owner_id={owner_id}"
      )

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
    logger.debug(
      f"Getting template for workspace={workspace_path}"
    )
    owner_id = self._workspace_owners.get(
      workspace_path
    )
    logger.debug(
      f"Found owner_id={owner_id} for workspace"
    )

    if owner_id:
      template = self._templates.get(
        owner_id, DEFAULT_INITIAL_TEMPLATE
      )
      logger.debug(
        f"Using {"custom" if owner_id in self._templates else "default"} template for owner_id={owner_id}"
      )
      return template

    logger.debug(
      "No owner found, using default template"
    )
    return DEFAULT_INITIAL_TEMPLATE

  def get_workspace_owner(
    self, workspace_path: Path
  ) -> str | None:
    """Get the owner ID for a workspace."""
    owner_id = self._workspace_owners.get(
      workspace_path
    )
    logger.debug(
      f"Retrieved owner_id={owner_id} for workspace={workspace_path}"
    )
    return owner_id

  def load_workspace(
    self,
    workspace_path: Path,
  ) -> str:
    """Load workspace content, creating it on-demand if needed."""
    logger.debug(
      f"Loading workspace from {workspace_path}"
    )

    try:
      # Check if the file exists
      file_exists = workspace_path.exists()
      logger.debug(
        f"Workspace file exists: {file_exists}"
      )

      if not file_exists:
        # Register the workspace metadata without creating the file
        logger.debug(
          "Registering workspace metadata before creation"
        )
        self.initialize_workspace(workspace_path)

        # Now create the file on-demand since we're actually accessing it
        logger.info(
          f"Creating workspace on-demand at {workspace_path}"
        )
        workspace_path.parent.mkdir(
          parents=True, exist_ok=True
        )
        template = self.get_workspace_template(
          workspace_path
        )
        logger.debug(
          f"Using template of length {len(template)} characters"
        )
        workspace_path.write_text(template)
        logger.debug(
          f"Workspace created on-demand at {workspace_path}"
        )

      # Always read directly from the file system
      content = workspace_path.read_text()
      logger.debug(
        f"Read {len(content)} characters from workspace file"
      )
      logger.debug(
        f"Content preview: {content[:200]}..."
      )
      logger.trace(
        f"Workspace loaded: {workspace_path}"
      )
      return content
    except Exception as e:
      logger.exception(
        f"Failed to load workspace {workspace_path}: {e}"
      )
      raise

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
      f"Content length: {len(content)} characters"
    )
    logger.debug(
      f"Content preview: {content[:200]}..."
    )

    # Check if directory exists
    if not workspace_path.parent.exists():
      logger.debug(
        f"Creating parent directory: {workspace_path.parent}"
      )
      workspace_path.parent.mkdir(
        parents=True, exist_ok=True
      )

    # Check if content has changed by reading current file
    try:
      if workspace_path.exists():
        current_content = workspace_path.read_text()
        content_changed = current_content != content
      else:
        content_changed = True

      logger.debug(
        f"Content has changed: {content_changed}"
      )

      # Write to file system
      workspace_path.write_text(content)
      logger.debug(
        f"Successfully wrote {len(content)} characters to file"
      )
    except Exception as e:
      logger.exception(
        f"Error saving workspace to {workspace_path}: {e}"
      )
      raise

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
      f"Update category: {update_category}, Message type: {type(message).__name__}"
    )
    logger.debug(
      f"Message content length: {len(message.content)} characters"
    )
    logger.debug(
      f"Message metadata: {message.metadata}"
    )

    try:
      logger.debug(
        "Loading existing workspace content"
      )
      workspace = self.load_workspace(workspace_path)
      logger.debug(
        f"Loaded workspace of length {len(workspace)} characters"
      )

      if update_category is None:
        update_category = "Interaction"
        logger.debug(
          "No update category provided, defaulting to 'Interaction'"
        )
      else:
        logger.debug(
          f"Using provided update category: {update_category}"
        )

      content_format = (
        message.content
        if update_category != "Interaction"
        else f"User: {message.content}"
      )
      logger.debug(
        f"Formatted content length: {len(content_format)} characters"
      )

      # Prepare the template
      template_source = (
        update_template or DEFAULT_UPDATE_TEMPLATE
      )
      template_type = (
        "custom" if update_template else "default"
      )
      logger.debug(
        f"Using {template_type} update template"
      )

      template = Template(template_source)
      update_prompt = template.render(
        msg_type=update_category.replace("_", " "),
        content_format=content_format,
        workspace=workspace,
      ).strip()

      logger.trace(
        f"Generated update prompt: {update_prompt}"
      )
      logger.debug(
        f"Update prompt length: {len(update_prompt)} characters"
      )

      logger.debug(
        "Sending update prompt to agent for processing"
      )
      response = await agent.generate_response(
        Message(
          content=update_prompt,
          metadata=message.metadata,
        )
      )
      logger.debug(
        f"Update response received, length: {len(response.content)} characters"
      )

      logger.debug("Saving updated workspace content")
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
    logger.debug(f"Agent type: {type(agent).__name__}")
    logger.debug(
      f"Using custom template: {delta_template is not None}"
    )

    try:
      # Read the file content
      logger.debug(
        f"Reading content from file: {file_path}"
      )
      file_content = file_path.read_text()
      logger.debug(
        f"Read {len(file_content)} characters from file"
      )

      # Prepare the prompt
      template_source = (
        delta_template or DEFAULT_EDIT_DELTA_TEMPLATE
      )
      template_type = (
        "custom" if delta_template else "default"
      )
      logger.debug(
        f"Using {template_type} delta template"
      )

      template = Template(template_source)
      delta_prompt = template.render(
        file_content=file_content,
        task=task,
      ).strip()

      logger.trace(
        f"Generated delta prompt: {delta_prompt}"
      )
      logger.debug(
        f"Delta prompt length: {len(delta_prompt)} characters"
      )

      # Get the response from the agent
      logger.debug(
        "Sending delta prompt to agent for processing"
      )
      response = await agent.generate_response(
        Message(
          content=delta_prompt,
        )
      )
      logger.debug(
        f"Received response of length {len(response.content)} characters"
      )

      # Parse the response as JSON
      try:
        # Extract JSON from the response if it's wrapped in markdown code blocks
        logger.debug(
          "Extracting JSON from agent response"
        )
        content = response.content
        if "```json" in content:
          logger.debug(
            "Found JSON code block in response"
          )
          content = (
            content.split("```json")[1]
            .split("```")[0]
            .strip()
          )
        elif "```" in content:
          logger.debug(
            "Found generic code block in response"
          )
          content = (
            content.split("```")[1]
            .split("```")[0]
            .strip()
          )
        logger.debug(
          f"Extracted content length: {len(content)} characters"
        )

        logger.debug("Parsing JSON content")
        edit_operations_data = json.loads(content)
        logger.debug(
          f"Parsed {len(edit_operations_data)} edit operations from JSON"
        )

        edit_operations = [
          EditOperation.from_dict(op)
          for op in edit_operations_data
        ]

        # Log details about each operation
        for i, op in enumerate(edit_operations):
          logger.debug(
            f"Operation {i + 1}: action={op.action}, location={op.location}, "
            f"content_length={len(op.content) if op.content else 0}"
          )

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
    logger.debug(
      f"Output path: {output_path if output_path else "None (overwriting original)"}"
    )

    try:
      # Read the file content
      logger.debug(
        f"Reading content from file: {file_path}"
      )
      file_content = file_path.read_text()
      lines = file_content.splitlines()
      logger.debug(f"File has {len(lines)} lines")

      # Track original line numbers for each line in the current file
      # This helps handle line number changes due to insertions/deletions
      original_line_numbers = list(range(len(lines)))
      logger.debug(
        "Initialized original line number tracking"
      )

      # Apply edit operations
      for i, op in enumerate(edit_operations):
        logger.debug(
          f"Applying operation {i + 1}/{len(edit_operations)}: "
          f"action={op.action}, location={op.location}"
        )

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
            logger.debug(
              f"Found insert location at current index {current_index} "
              f"(original line {insert_after})"
            )
          except ValueError:
            # If the line number is not found, insert at the end
            current_index = len(lines) - 1
            logger.warning(
              f"Original line {insert_after} not found, inserting at end "
              f"(current index {current_index})"
            )

          # Insert the content
          new_content_lines = (
            op.content.splitlines()
            if op.content
            else []
          )
          logger.debug(
            f"Inserting {len(new_content_lines)} lines after index {current_index}"
          )
          lines[
            current_index + 1 : current_index + 1
          ] = new_content_lines

          # Update original line numbers
          # Lines after the insertion point need to be shifted
          original_line_numbers[
            current_index + 1 : current_index + 1
          ] = [-1] * len(new_content_lines)
          logger.debug(
            "Updated line number tracking after insertion"
          )

        elif op.action == "delete":
          # For delete, we need to find all indices in the current file
          # that correspond to original line numbers in the specified range
          if (
            isinstance(op.location, (list, tuple))
            and len(op.location) == 2
          ):
            start, end = op.location
            logger.debug(
              f"Delete range: original lines {start} to {end}"
            )
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
          logger.debug(
            f"Found {len(indices_to_delete)} lines to delete at current indices: {indices_to_delete}"
          )

          # Delete lines in reverse order to avoid index shifting
          for i in sorted(
            indices_to_delete, reverse=True
          ):
            logger.debug(
              f"Deleting line at current index {i}"
            )
            del lines[i]
            del original_line_numbers[i]

          logger.debug(
            "Updated line number tracking after deletion"
          )

        elif op.action == "replace":
          # For replace, first delete the lines, then insert the new content
          if (
            isinstance(op.location, (list, tuple))
            and len(op.location) == 2
          ):
            start, end = op.location
            logger.debug(
              f"Replace range: original lines {start} to {end}"
            )
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

          logger.debug(
            f"Found {len(indices_to_replace)} lines to replace at current indices: {indices_to_replace}"
          )

          # Get the index where replacement should start
          replace_start_index = min(indices_to_replace)
          logger.debug(
            f"Replacement will start at index {replace_start_index}"
          )

          # Delete lines in reverse order
          for i in sorted(
            indices_to_replace, reverse=True
          ):
            logger.debug(
              f"Deleting line at current index {i} for replacement"
            )
            del lines[i]
            del original_line_numbers[i]

          # Insert new content
          new_content_lines = (
            op.content.splitlines()
            if op.content
            else []
          )
          logger.debug(
            f"Inserting {len(new_content_lines)} new lines at index {replace_start_index}"
          )
          lines[
            replace_start_index:replace_start_index
          ] = new_content_lines
          original_line_numbers[
            replace_start_index:replace_start_index
          ] = [-1] * len(new_content_lines)

          logger.debug(
            "Updated line number tracking after replacement"
          )

      # Join lines back into a string
      edited_content = "\n".join(lines)
      logger.debug(
        f"Final edited content has {len(lines)} lines and {len(edited_content)} characters"
      )

      # Save the edited content
      if output_path:
        logger.debug(
          f"Saving edited content to output path: {output_path}"
        )
        if not output_path.parent.exists():
          logger.debug(
            f"Creating parent directory: {output_path.parent}"
          )
          output_path.parent.mkdir(
            parents=True, exist_ok=True
          )
        output_path.write_text(edited_content)
        logger.debug(
          f"Edited file saved to: {output_path}"
        )
      else:
        logger.debug(
          f"Overwriting original file: {file_path}"
        )
        file_path.write_text(edited_content)
        logger.debug(
          f"Original file updated: {file_path}"
        )

      # Store edit operations in history
      if file_path not in self._edit_history:
        logger.debug(
          f"Creating new edit history entry for {file_path}"
        )
        self._edit_history[file_path] = []
      self._edit_history[file_path].append(
        edit_operations
      )
      logger.debug(
        f"Edit history updated, now has {len(self._edit_history[file_path])} entries"
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
    logger.debug(
      f"Original content length: {len(original_content)} characters"
    )
    logger.debug(
      f"Edited content length: {len(edited_content)} characters"
    )
    logger.debug(f"Task: {task}")
    logger.debug(
      f"Number of edit operations: {len(edit_operations)}"
    )
    logger.debug(f"Agent type: {type(agent).__name__}")
    logger.debug(
      f"Using custom validation template: {validation_template is not None}"
    )

    try:
      # Prepare the prompt
      template_source = (
        validation_template
        or DEFAULT_EDIT_VALIDATION_TEMPLATE
      )
      template_type = (
        "custom" if validation_template else "default"
      )
      logger.debug(
        f"Using {template_type} validation template"
      )

      template = Template(template_source)

      # Convert edit operations to JSON
      logger.debug(
        "Converting edit operations to JSON"
      )
      edit_operations_json = json.dumps(
        [op.to_dict() for op in edit_operations]
        if edit_operations
        else [],
        indent=2,
      )
      logger.debug(
        f"JSON representation length: {len(edit_operations_json)} characters"
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
      logger.debug(
        f"Validation prompt length: {len(validation_prompt)} characters"
      )

      # Get the response from the agent
      logger.debug(
        "Sending validation prompt to agent for processing"
      )
      response = await agent.generate_response(
        Message(
          content=validation_prompt,
        )
      )
      logger.debug(
        f"Received response of length {len(response.content)} characters"
      )

      # Parse the response as JSON
      try:
        # Extract JSON from the response if it's wrapped in markdown code blocks
        logger.debug(
          "Extracting JSON from agent response"
        )
        content = response.content
        if "```json" in content:
          logger.debug(
            "Found JSON code block in response"
          )
          content = (
            content.split("```json")[1]
            .split("```")[0]
            .strip()
          )
        elif "```" in content:
          logger.debug(
            "Found generic code block in response"
          )
          content = (
            content.split("```")[1]
            .split("```")[0]
            .strip()
          )
        logger.debug(
          f"Extracted content length: {len(content)} characters"
        )

        logger.debug("Parsing JSON content")
        validation_result = json.loads(content)
        logger.debug(
          f"Validation result: {validation_result}"
        )

        # Log specific validation results
        logger.info(
          f"Validation valid: {validation_result.get("valid", False)}"
        )
        logger.info(
          f"Task accomplished: {validation_result.get("task_accomplished", False)}"
        )

        if validation_result.get("issues"):
          logger.warning(
            f"Validation issues: {validation_result.get("issues")}"
          )
        else:
          logger.debug("No validation issues found")

        logger.debug(
          f"Validation comments: {validation_result.get("comments", "")}"
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
