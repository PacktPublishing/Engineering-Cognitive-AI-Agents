"""Test reasoning coordinator's ability to orchestrate the full problem-solving cycle."""

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


class TestArtifacts:
  """Container for test artifacts that need to be saved."""

  def __init__(self, artifacts_dir: Path):
    self.artifacts_dir = artifacts_dir
    self.initial_workspace = ""
    self.stage_outputs: dict[str, str] = {}
    self.final_workspace = ""
    self.streaming_content: list[str] = []

  def save_artifacts(self) -> None:
    """Save all collected artifacts."""
    logger.info("Saving test artifacts...")
    self.artifacts_dir.mkdir(
      parents=True,
      exist_ok=True,
    )

    if self.initial_workspace:
      path = (
        self.artifacts_dir / "initial_workspace.md"
      )
      path.write_text(self.initial_workspace)
      logger.info(
        f"Saved initial workspace to: {path}"
      )

    for stage, content in self.stage_outputs.items():
      path = self.artifacts_dir / f"{stage}_output.md"
      path.write_text(content)
      logger.info(f"Saved {stage} output to: {path}")

    if self.final_workspace:
      path = self.artifacts_dir / "final_workspace.md"
      path.write_text(self.final_workspace)
      logger.info(f"Saved final workspace to: {path}")

    if self.streaming_content:
      path = (
        self.artifacts_dir / "streaming_content.md"
      )
      path.write_text(
        "\n".join(self.streaming_content)
      )
      logger.info(
        f"Saved streaming content to: {path}"
      )


@pytest.fixture
def test_artifacts() -> TestArtifacts:
  """Fixture to provide test artifacts.

  Returns
  -------
  TestArtifacts
      Container for collecting artifacts during the test
  """
  artifacts = TestArtifacts(
    Path(__file__).parent
    / "artifacts"
    / "coordinator",
  )
  return artifacts


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
async def test_llm_distillation_reasoning_cycle(
  test_artifacts: TestArtifacts,
  temp_workspace: Path,
) -> None:
  """Test full reasoning cycle coordination for LLM distillation problem."""
  # Setup
  logger.info(
    "Starting test_llm_distillation_reasoning_cycle"
  )

  # Clean up any existing artifacts
  if test_artifacts.artifacts_dir.exists():
    import shutil

    shutil.rmtree(test_artifacts.artifacts_dir)

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

  # Send problem to solve
  query = (
    "I want to explore approaches for distilling reasoning capabilities "
    "from large language models into smaller, more efficient versions. "
    "Let's analyze DeepSeek's recent breakthrough and design our own approach."
  )

  # Process responses and collect results
  response_count = 0
  final_response = None
  async for response in coordinator.process(
    Message(content=query),
  ):
    response_count += 1

    # Accumulate all responses for debugging
    if response.content:
      test_artifacts.streaming_content.append(
        response.content
      )

    if response.metadata.get("reasoning_stage"):
      test_artifacts.stage_outputs[
        response.metadata["reasoning_stage"]
      ] = response.content

    # Store workspace content from response metadata
    if response.metadata.get("workspace_content"):
      test_artifacts.final_workspace = (
        response.metadata["workspace_content"]
      )

    if not response.metadata.get("streaming"):
      final_response = response

  assert final_response is not None, (
    "No final response received"
  )
  assert response_count > 0, "No responses processed"

  # Save artifacts
  test_artifacts.save_artifacts()

  # Verify the updates using the final workspace content from metadata
  assert test_artifacts.final_workspace, (
    "No workspace content found in response metadata"
  )
  assert (
    "## Generated Hypotheses"
    in test_artifacts.final_workspace
  ), "Should have Generated Hypotheses section"
  assert (
    "## Investigation Design"
    in test_artifacts.final_workspace
  ), "Should have Investigation Design section"
  assert (
    "## Validation Results"
    in test_artifacts.final_workspace
  ), "Should have Validation Results section"
  assert (
    "## Learning Capture"
    in test_artifacts.final_workspace
  ), "Should have Learning Capture section"
  assert (
    "## Next Steps" in test_artifacts.final_workspace
  ), "Should have Next Steps section"

  # Verify we have outputs from different stages
  assert len(test_artifacts.stage_outputs) > 0, (
    "Should have outputs from different reasoning stages"
  )
  assert len(test_artifacts.streaming_content) > 0, (
    "Should have streaming content"
  )
