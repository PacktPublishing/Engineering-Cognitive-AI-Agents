"""Test inquiry design capabilities for LLM distillation use case."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from loguru import logger

from winston.core.agent import AgentConfig
from winston.core.messages import Message
from winston.core.paths import AgentPaths
from winston.core.reasoning.constants import (
  AGENCY_WORKSPACE_KEY,
)
from winston.core.reasoning.inquiry import (
  InquiryAgent,
)
from winston.core.system import AgentSystem
from winston.core.workspace import WorkspaceManager


class TestArtifacts:
  """Container for test artifacts that need to be saved."""

  def __init__(self, artifacts_dir: Path):
    self.artifacts_dir = artifacts_dir
    self.initial_workspace = ""
    self.generated_investigation = ""
    self.final_workspace = ""
    self.streaming_content = ""

  def save_artifacts(self) -> None:
    """Save all collected artifacts."""
    logger.info("Saving test artifacts...")
    self.artifacts_dir.mkdir(
      parents=True, exist_ok=True
    )

    if self.initial_workspace:
      path = (
        self.artifacts_dir / "initial_workspace.md"
      )
      path.write_text(self.initial_workspace)
      logger.info(
        f"Saved initial workspace to: {path}"
      )

    if self.generated_investigation:
      path = (
        self.artifacts_dir
        / "generated_investigation.md"
      )
      path.write_text(self.generated_investigation)
      logger.info(
        f"Saved generated investigation to: {path}"
      )

    if self.final_workspace:
      path = self.artifacts_dir / "final_workspace.md"
      path.write_text(self.final_workspace)
      logger.info(f"Saved final workspace to: {path}")

    if self.streaming_content:
      path = (
        self.artifacts_dir / "streaming_content.md"
      )
      path.write_text(self.streaming_content)
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
    Path(__file__).parent / "artifacts" / "inquiry"
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
async def test_llm_distillation_inquiry(
  test_artifacts: TestArtifacts,
  temp_workspace: Path,
) -> None:
  """Test investigation design for LLM distillation problem."""
  # Setup
  logger.info("Starting test_llm_distillation_inquiry")

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
  config = AgentConfig.from_yaml(
    paths.system_agents_config
    / "reasoning"
    / "inquiry.yaml"
  )
  agent = InquiryAgent(system, config, paths)
  workspace_manager = WorkspaceManager()

  # Load the hypothesis test artifacts to get the workspace with hypotheses
  hypothesis_artifacts_dir = (
    Path(__file__).parent / "artifacts" / "hypothesis"
  )
  hypothesis_workspace = (
    hypothesis_artifacts_dir / "final_workspace.md"
  )

  # Setup shared agency workspace using the hypothesis workspace content
  agency_workspace = (
    Path(paths.workspaces) / "reasoning_agency.md"
  )
  workspace_content = hypothesis_workspace.read_text()

  workspace_manager.initialize_workspace(
    agency_workspace,
    owner_id="reasoning_coordinator",
    content=workspace_content,
  )

  # Save initial workspace
  test_artifacts.initial_workspace = workspace_content
  test_artifacts.save_artifacts()

  # Test investigation design
  query = (
    "Based on the generated hypotheses about LLM distillation, "
    "please design specific tests to validate these approaches."
  )

  initial_msg = Message(
    content=query,
    metadata={
      AGENCY_WORKSPACE_KEY: agency_workspace,
    },
  )

  logger.debug(
    "Starting investigation design for LLM distillation"
  )

  response_count = 0
  final_response = None
  streaming_content: list[str] = []

  async for response in agent.process(initial_msg):
    response_count += 1

    # Accumulate all responses for debugging
    if response.content:
      streaming_content.append(response.content)

    if not response.metadata.get("streaming"):
      # This is the final response, after workspace has been updated
      final_response = response
      break

  assert final_response is not None, (
    "No final response received"
  )
  assert response_count > 0, "No responses processed"

  # Save generated investigation and streaming content
  test_artifacts.generated_investigation = (
    final_response.content
  )
  test_artifacts.streaming_content = "".join(
    streaming_content
  )
  test_artifacts.save_artifacts()

  # Get the updated workspace content
  updated_content = workspace_manager.load_workspace(
    agency_workspace
  )
  test_artifacts.final_workspace = updated_content
  test_artifacts.save_artifacts()

  # Verify the updates
  assert (
    "## Investigation Design" in updated_content
  ), "Should have Investigation Design section"
  assert (
    "[To be designed by inquiry agent]"
    not in updated_content
  ), "Should have replaced placeholder"
  assert final_response.content in updated_content, (
    "Final response should be in workspace"
  )

  # Verify investigation structure
  assert "Test Design:" in updated_content, (
    "Should have at least one test design"
  )
  assert "Priority:" in updated_content, (
    "Should include priority scores"
  )
  assert "Requirements:" in updated_content, (
    "Should include requirements"
  )
  assert "Success Metrics:" in updated_content, (
    "Should include success metrics"
  )
  assert "Execution Steps:" in updated_content, (
    "Should include execution steps"
  )
