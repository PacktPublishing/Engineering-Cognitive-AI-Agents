"""Test reasoning coordinator's ability to properly reset context for new problems."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from loguru import logger

from winston.core.agent import AgentConfig
from winston.core.memory.coordinator import (
  MemoryCoordinator,
)
from winston.core.messages import Message
from winston.core.paths import AgentPaths
from winston.core.reasoning.coordinator import (
  ReasoningCoordinator,
)
from winston.core.system import AgentSystem


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
  """Fixture to provide a temporary workspace that persists through the test.

  Returns
  -------
  Generator[Path, None, None]
      Generator yielding path to temporary workspace directory
  """
  temp_dir = tempfile.mkdtemp()
  yield Path(temp_dir)
  # Clean up after test is completely done
  import shutil

  shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_context_reset_between_problems(
  temp_workspace: Path,
) -> None:
  """Test that the coordinator properly resets context when switching to a new problem."""
  # Setup
  logger.info(
    "Starting test_context_reset_between_problems"
  )

  project_root = Path(__file__).parent.parent.parent
  paths = AgentPaths(
    root=temp_workspace,
    system_root=project_root,
  )
  system = AgentSystem()

  # Create and register memory coordinator
  memory_config = AgentConfig.from_yaml(
    paths.system_agents_config
    / "memory"
    / "coordinator.yaml"
  )
  _ = MemoryCoordinator(
    system,
    memory_config,
    paths,
  )

  # Create coordinator
  config = AgentConfig.from_yaml(
    paths.system_agents_config
    / "reasoning"
    / "coordinator.yaml"
  )
  coordinator = ReasoningCoordinator(
    system,
    config,
    paths,
  )

  # First problem
  first_problem = "I am having a terrible time deciding whether or not to switch jobs."
  first_workspace_content = None

  # Process first problem
  async for response in coordinator.process(
    Message(content=first_problem)
  ):
    # Store the workspace content from the last response
    if response.metadata.get("workspace_content"):
      first_workspace_content = response.metadata[
        "workspace_content"
      ]

    # We don't need to process all responses for this test
    if (
      "job" in response.content
      and not response.metadata.get("streaming")
    ):
      break

  # Verify first problem workspace content
  assert first_workspace_content is not None, (
    "No workspace content found for first problem"
  )
  assert "switch jobs" in first_workspace_content, (
    "Workspace should contain content related to first problem"
  )

  # Second problem (completely different topic)
  second_problem = "How does the color of light affect the growth rate of plants?"
  second_workspace_content = None

  # Process second problem
  async for response in coordinator.process(
    Message(content=second_problem)
  ):
    # Store the workspace content from the last response
    if response.metadata.get("workspace_content"):
      second_workspace_content = response.metadata[
        "workspace_content"
      ]

    # We don't need to process all responses for this test
    if (
      "light" in response.content
      and not response.metadata.get("streaming")
    ):
      break

  # Verify second problem workspace content
  assert second_workspace_content is not None, (
    "No workspace content found for second problem"
  )
  assert (
    "color of light" in second_workspace_content
  ), (
    "Workspace should contain content related to second problem"
  )
  assert (
    "switch jobs" not in second_workspace_content
  ), (
    "Workspace should not contain content from first problem"
  )

  # Verify workspace was reset
  assert (
    first_workspace_content != second_workspace_content
  ), (
    "Workspace content should be different after context reset"
  )

  logger.info(
    "Context reset test completed successfully"
  )
