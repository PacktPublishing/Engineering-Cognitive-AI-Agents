# tests/core/test_workspace.py
# type: ignore
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from winston.core.messages import Message
from winston.core.workspace import (
  DEFAULT_INITIAL_TEMPLATE,
  EditOperation,
  WorkspaceManager,
)


class TestEditOperation:
  def test_init(self) -> None:
    # Test initialization with all parameters
    op = EditOperation("insert", 5, "New content")
    assert op.action == "insert"
    assert op.location == 5
    assert op.content == "New content"

    # Test initialization with default content
    op = EditOperation("delete", [1, 3])
    assert op.action == "delete"
    assert op.location == [1, 3]
    assert op.content == ""

  def test_to_dict(self) -> None:
    # Test with content
    op = EditOperation("insert", 5, "New content")
    result = op.to_dict()
    assert result == {
      "action": "insert",
      "location": 5,
      "content": "New content",
    }

    # Test without content
    op = EditOperation("delete", [1, 3])
    result = op.to_dict()
    assert result == {
      "action": "delete",
      "location": [1, 3],
    }

  def test_from_dict(self) -> None:
    # Test with content
    data = {
      "action": "insert",
      "location": 5,
      "content": "New content",
    }
    op = EditOperation.from_dict(data)
    assert op.action == "insert"
    assert op.location == 5
    assert op.content == "New content"

    # Test without content
    data = {
      "action": "delete",
      "location": [1, 3],
    }
    op = EditOperation.from_dict(data)
    assert op.action == "delete"
    assert op.location == [1, 3]
    assert op.content == ""


class TestWorkspaceManager:
  @pytest.fixture
  def workspace_manager(self) -> WorkspaceManager:
    # Reset the singleton instance before each test
    WorkspaceManager._instance = None  # type: ignore
    return WorkspaceManager()

  @pytest.fixture
  def mock_agent(self) -> AsyncMock:
    agent = AsyncMock()
    agent.generate_response = AsyncMock()
    return agent

  def test_singleton(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test that WorkspaceManager is a singleton
    another_instance = WorkspaceManager()
    assert workspace_manager is another_instance

  def test_initialize(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test initialization
    assert hasattr(workspace_manager, "_workspaces")
    assert hasattr(workspace_manager, "_templates")
    assert hasattr(
      workspace_manager, "_workspace_owners"
    )
    assert hasattr(workspace_manager, "_edit_history")

  @patch("winston.core.workspace.Path.exists")
  @patch("winston.core.workspace.Path.write_text")
  @patch("winston.core.workspace.Path.parent")
  def test_initialize_workspace_new(
    self,
    mock_parent: MagicMock,
    mock_write_text: MagicMock,
    mock_exists: MagicMock,
    workspace_manager: WorkspaceManager,
  ) -> None:
    # Test initializing a new workspace
    mock_exists.return_value = False
    mock_parent.mkdir = MagicMock()

    workspace_path = Path("/test/workspace.md")
    content = "Test content"
    template = "Test template"
    owner_id = "test_owner"

    workspace_manager.initialize_workspace(
      workspace_path, content, template, owner_id
    )

    # Check that the workspace was created
    mock_parent.mkdir.assert_called_once_with(
      parents=True, exist_ok=True
    )
    mock_write_text.assert_called_once_with(content)

    # Check that owner and template were stored
    assert (
      workspace_manager._workspace_owners[
        workspace_path
      ]
      == owner_id
    )
    assert (
      workspace_manager._templates[owner_id]
      == template
    )

  @patch("winston.core.workspace.Path.exists")
  def test_initialize_workspace_existing(
    self,
    mock_exists: MagicMock,
    workspace_manager: WorkspaceManager,
  ) -> None:
    # Test initializing an existing workspace
    mock_exists.return_value = True

    workspace_path = Path("/test/workspace.md")
    owner_id = "test_owner"

    workspace_manager.initialize_workspace(
      workspace_path, owner_id=owner_id
    )

    # Check that owner was stored but no file operations were performed
    assert (
      workspace_manager._workspace_owners[
        workspace_path
      ]
      == owner_id
    )

  def test_get_workspace_template(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test getting template for a workspace with owner
    workspace_path = Path("/test/workspace.md")
    owner_id = "test_owner"
    template = "Custom template"

    workspace_manager._workspace_owners[
      workspace_path
    ] = owner_id
    workspace_manager._templates[owner_id] = template

    result = workspace_manager.get_workspace_template(
      workspace_path
    )
    assert result == template

    # Test getting template for a workspace without owner
    workspace_path2 = Path("/test/workspace2.md")
    result = workspace_manager.get_workspace_template(
      workspace_path2
    )
    assert result == DEFAULT_INITIAL_TEMPLATE

  def test_get_workspace_owner(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test getting owner for a workspace
    workspace_path = Path("/test/workspace.md")
    owner_id = "test_owner"

    workspace_manager._workspace_owners[
      workspace_path
    ] = owner_id

    result = workspace_manager.get_workspace_owner(
      workspace_path
    )
    assert result == owner_id

    # Test getting owner for a workspace without owner
    workspace_path2 = Path("/test/workspace2.md")
    result = workspace_manager.get_workspace_owner(
      workspace_path2
    )
    assert result is None

  @patch("winston.core.workspace.Path.read_text")
  @patch.object(
    WorkspaceManager, "initialize_workspace"
  )
  def test_load_workspace(
    self,
    mock_initialize: MagicMock,
    mock_read_text: MagicMock,
    workspace_manager: WorkspaceManager,
  ) -> None:
    # Test loading a workspace
    workspace_path = Path("/test/workspace.md")
    mock_read_text.return_value = "Workspace content"

    result = workspace_manager.load_workspace(
      workspace_path
    )

    # Check that the workspace was initialized and loaded
    mock_initialize.assert_called_once_with(
      workspace_path
    )
    mock_read_text.assert_called_once()
    assert result == "Workspace content"
    assert (
      workspace_manager._workspaces[workspace_path]
      == "Workspace content"
    )

    # Test loading a cached workspace
    mock_initialize.reset_mock()
    mock_read_text.reset_mock()

    result = workspace_manager.load_workspace(
      workspace_path
    )

    # Check that the workspace was loaded from cache
    mock_initialize.assert_not_called()
    mock_read_text.assert_not_called()
    assert result == "Workspace content"

  @patch("winston.core.workspace.Path.write_text")
  @patch("winston.core.workspace.Path.parent")
  def test_save_workspace(
    self,
    mock_parent: MagicMock,
    mock_write_text: MagicMock,
    workspace_manager: WorkspaceManager,
  ) -> None:
    # Test saving a workspace
    workspace_path = Path("/test/workspace.md")
    content = "New content"
    mock_parent.mkdir = MagicMock()

    workspace_manager.save_workspace(
      workspace_path, content
    )

    # Check that the workspace was saved
    mock_parent.mkdir.assert_called_once_with(
      parents=True, exist_ok=True
    )
    mock_write_text.assert_called_once_with(content)
    assert (
      workspace_manager._workspaces[workspace_path]
      == content
    )

  @patch.object(WorkspaceManager, "load_workspace")
  @patch.object(WorkspaceManager, "save_workspace")
  @pytest.mark.asyncio
  async def test_update_workspace(
    self,
    mock_save: MagicMock,
    mock_load: MagicMock,
    workspace_manager: WorkspaceManager,
    mock_agent: AsyncMock,
  ) -> None:
    # Test updating a workspace
    workspace_path = Path("/test/workspace.md")
    message = Message(
      content="I like chocolate ice cream"
    )

    # Create a realistic original workspace content
    original_workspace = """# User Preferences

- Prefers dark mode in applications
- Enjoys reading science fiction

# Relevant Context

- Working on a project about AI ethics
- Recently mentioned interest in learning Python
"""
    mock_load.return_value = original_workspace

    # Create a realistic updated workspace that would be returned by the agent
    updated_workspace = """# User Preferences

- Prefers dark mode in applications
- Enjoys reading science fiction
- Likes chocolate ice cream

# Relevant Context

- Working on a project about AI ethics
- Recently mentioned interest in learning Python
"""
    mock_agent.generate_response.return_value = (
      MagicMock(content=updated_workspace)
    )

    result = await workspace_manager.update_workspace(
      workspace_path, message, mock_agent
    )

    # Check that the workspace was loaded, updated, and saved
    mock_load.assert_called_once_with(workspace_path)
    mock_agent.generate_response.assert_called_once()
    mock_save.assert_called_once_with(
      workspace_path, updated_workspace
    )
    assert result == updated_workspace

  @pytest.mark.asyncio
  async def test_generate_edit_delta(
    self,
    workspace_manager: WorkspaceManager,
    mock_agent: AsyncMock,
  ) -> None:
    # Test generating edit delta
    file_path = Path("/test/file.py")
    task = "Add a new function"

    with patch(
      "winston.core.workspace.Path.read_text",
      return_value="Original content",
    ):
      with patch(
        "json.loads",
        return_value=[
          {
            "action": "insert",
            "location": 5,
            "content": "New content",
          }
        ],
      ):
        # Set up the mock response for this specific test
        mock_agent.generate_response.return_value = MagicMock(
          content='```json\n[{"action": "insert", "location": 5, "content": "New content"}]\n```'
        )

        result = (
          await workspace_manager.generate_edit_delta(
            file_path, task, mock_agent
          )
        )

        # Check that the edit delta was generated
        assert len(result) == 1
        assert result[0].action == "insert"
        assert result[0].location == 5
        assert result[0].content == "New content"

  def test_apply_edit_delta(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test applying edit delta
    file_path = Path("/test/file.py")

    # Create edit operations
    operations = [
      EditOperation(
        "insert", 1, "New line 1\nNew line 2"
      ),
      EditOperation("delete", [4, 5]),
      EditOperation(
        "replace", [7, 8], "Replaced content"
      ),
    ]

    with patch(
      "winston.core.workspace.Path.read_text",
      return_value="Line 0\nLine 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9",
    ):
      with patch(
        "winston.core.workspace.Path.write_text"
      ) as mock_write:
        result = workspace_manager.apply_edit_delta(
          file_path, operations
        )

        # Check that the edit delta was applied
        expected = "Line 0\nLine 1\nNew line 1\nNew line 2\nLine 2\nLine 3\nLine 6\nReplaced content\nLine 9"
        assert result == expected
        mock_write.assert_called_once_with(expected)

        # Check that edit history was updated
        assert (
          file_path in workspace_manager._edit_history
        )
        assert (
          len(
            workspace_manager._edit_history[file_path]
          )
          == 1
        )
        assert (
          workspace_manager._edit_history[file_path][0]
          == operations
        )

  @pytest.mark.asyncio
  async def test_validate_edit(
    self,
    workspace_manager: WorkspaceManager,
    mock_agent: AsyncMock,
  ) -> None:
    # Test validating edit
    original_content = "Original content"
    edited_content = "Edited content"
    task = "Update content"
    edit_operations = [
      EditOperation(
        "replace", [0, 0], "Edited content"
      )
    ]

    validation_result: Dict[str, Any] = {
      "valid": True,
      "issues": [],
      "task_accomplished": True,
      "comments": "Edit was successful",
    }

    # Set up the mock response for this specific test
    mock_agent.generate_response.return_value = MagicMock(
      content=f"```json\n{json.dumps(validation_result)}\n```"
    )

    result = await workspace_manager.validate_edit(
      original_content,
      edited_content,
      task,
      edit_operations,
      mock_agent,
    )

    # Check that the edit was validated
    assert result == validation_result

  def test_get_edit_diff(
    self, workspace_manager: WorkspaceManager
  ) -> None:
    # Test getting edit diff
    original_content = "Line 1\nLine 2\nLine 3"
    edited_content = "Line 1\nModified Line\nLine 3"

    result = workspace_manager.get_edit_diff(
      original_content, edited_content
    )

    # Check that the diff was generated
    assert "Line 2" in result
    assert "Modified Line" in result

  @pytest.mark.asyncio
  async def test_edit_file(
    self,
    workspace_manager: WorkspaceManager,
    mock_agent: AsyncMock,
  ) -> None:
    # Test editing a file
    file_path = Path("/test/file.py")
    task = "Update content"

    # Mock all the component methods
    with patch.object(
      workspace_manager, "generate_edit_delta"
    ) as mock_generate:
      with patch.object(
        workspace_manager, "apply_edit_delta"
      ) as mock_apply:
        with patch.object(
          workspace_manager, "validate_edit"
        ) as mock_validate:
          with patch.object(
            workspace_manager, "get_edit_diff"
          ) as mock_diff:
            with patch(
              "winston.core.workspace.Path.read_text",
              return_value="Original content",
            ):
              # Set up return values
              edit_operations = [
                EditOperation(
                  "replace", [0, 0], "Edited content"
                )
              ]
              mock_generate.return_value = (
                edit_operations
              )
              mock_apply.return_value = (
                "Edited content"
              )
              mock_validate.return_value = {
                "valid": True,
                "issues": [],
                "task_accomplished": True,
                "comments": "Edit was successful",
              }
              mock_diff.return_value = "Diff content"

              result = (
                await workspace_manager.edit_file(
                  file_path, task, mock_agent
                )
              )

              # Check that all methods were called
              mock_generate.assert_called_once()
              mock_apply.assert_called_once()
              mock_validate.assert_called_once()
              mock_diff.assert_called_once()

              # Check the result
              assert (
                result["edited_content"]
                == "Edited content"
              )
              assert (
                len(result["edit_operations"]) == 1
              )
              assert (
                result["validation"]["valid"] is True
              )
              assert result["diff"] == "Diff content"
