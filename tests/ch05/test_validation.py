"""Test validation capabilities for LLM distillation use case."""

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
from winston.core.reasoning.validation import (
  ValidationAgent,
)
from winston.core.system import AgentSystem
from winston.core.workspace import WorkspaceManager


class TestArtifacts:
  """Container for test artifacts that need to be saved."""

  def __init__(self, artifacts_dir: Path):
    self.artifacts_dir = artifacts_dir
    self.initial_workspace = ""
    self.generated_validation = ""
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

    if self.generated_validation:
      path = (
        self.artifacts_dir / "generated_validation.md"
      )
      path.write_text(self.generated_validation)
      logger.info(
        f"Saved generated validation to: {path}"
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
    Path(__file__).parent / "artifacts" / "validation"
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
async def test_llm_distillation_validation(
  test_artifacts: TestArtifacts,
  temp_workspace: Path,
) -> None:
  """Test validation analysis for LLM distillation problem."""
  # Setup
  logger.info(
    "Starting test_llm_distillation_validation"
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
  config = AgentConfig.from_yaml(
    paths.system_agents_config
    / "reasoning"
    / "validation.yaml"
  )
  agent = ValidationAgent(system, config, paths)
  workspace_manager = WorkspaceManager()

  # Load the inquiry test artifacts to get the workspace with test designs
  inquiry_artifacts_dir = (
    Path(__file__).parent / "artifacts" / "inquiry"
  )
  inquiry_workspace = (
    inquiry_artifacts_dir / "final_workspace.md"
  )

  # Setup shared agency workspace using the inquiry workspace content
  agency_workspace = (
    Path(paths.workspaces) / "reasoning_agency.md"
  )
  workspace_content = inquiry_workspace.read_text()

  # Add simulated test results to the workspace
  workspace_content += """
## Test Results
Performance Metrics:
- Model size reduced by 75% through progressive stages
- Reasoning capability retention:
  - Stage 1: 95% of baseline
  - Stage 2: 92% of baseline
  - Stage 3: 88% of baseline
- Resource utilization:
  - Memory: 65% reduction
  - Compute: 55% reduction
  - Inference time: 40% improvement

Qualitative Observations:
- Progressive transfer maintained core reasoning patterns
- Some degradation in edge case handling
- Significant improvements in deployment efficiency
- Successful preservation of key architectural components
"""

  workspace_manager.initialize_workspace(
    agency_workspace,
    owner_id="reasoning_coordinator",
    content=workspace_content,
  )

  # Save initial workspace
  test_artifacts.initial_workspace = workspace_content
  test_artifacts.save_artifacts()

  # Test validation analysis
  query = (
    "Based on the test results for our LLM distillation approaches, "
    "please analyze the evidence and validate our hypotheses."
  )

  initial_msg = Message(
    content=query,
    metadata={
      AGENCY_WORKSPACE_KEY: agency_workspace,
    },
  )

  logger.debug(
    "Starting validation analysis for LLM distillation"
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

  # Save generated validation and streaming content
  test_artifacts.generated_validation = (
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
  assert "## Validation Results" in updated_content, (
    "Should have Validation Results section"
  )
  assert "[To be validated]" not in updated_content, (
    "Should have replaced placeholder"
  )
  assert final_response.content in updated_content, (
    "Final response should be in workspace"
  )

  # Verify validation structure
  assert "Hypothesis:" in updated_content, (
    "Should reference original hypothesis"
  )
  assert "Evidence Quality:" in updated_content, (
    "Should include evidence quality score"
  )
  assert "Results Analysis:" in updated_content, (
    "Should include results analysis"
  )
  assert "Confidence Update:" in updated_content, (
    "Should include confidence updates"
  )
  assert "Refinements Needed:" in updated_content, (
    "Should include needed refinements"
  )
  assert "Learning Capture:" in updated_content, (
    "Should include captured learnings"
  )
