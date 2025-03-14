"""Test hypothesis generation capabilities for LLM distillation use case."""

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
from winston.core.reasoning.hypothesis import (
  HypothesisAgent,
)
from winston.core.system import AgentSystem
from winston.core.workspace import WorkspaceManager


class TestArtifacts:
  """Container for test artifacts that need to be saved."""

  def __init__(self, artifacts_dir: Path):
    self.artifacts_dir = artifacts_dir
    self.initial_workspace = ""
    self.generated_hypotheses = ""
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

    if self.generated_hypotheses:
      path = (
        self.artifacts_dir / "generated_hypotheses.md"
      )
      path.write_text(self.generated_hypotheses)
      logger.info(
        f"Saved generated hypotheses to: {path}"
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
    Path(__file__).parent / "artifacts" / "hypothesis"
  )
  return artifacts  # Remove yield and teardown


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
async def test_llm_distillation_hypothesis(
  test_artifacts: TestArtifacts,
  temp_workspace: Path,
) -> None:
  """Test hypothesis generation for LLM distillation problem."""
  # Setup
  logger.info(
    "Starting test_llm_distillation_hypothesis"
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
    / "hypothesis.yaml"
  )
  agent = HypothesisAgent(system, config, paths)
  workspace_manager = WorkspaceManager()

  # Setup shared agency workspace using coordinator's template
  agency_workspace = (
    Path(paths.workspaces) / "reasoning_agency.md"
  )
  workspace_content = """# Current Problem
Exploring approaches for distilling reasoning capabilities from large language models into smaller, efficient versions.

# Reasoning Stage
HYPOTHESIS_GENERATION

# Background Knowledge
- DeepSeek's 800K sample success in preserving reasoning capabilities
- Previous attempts showed degraded reasoning in compressed models
- Successful preservation of language capabilities through staged reduction

## Generated Hypotheses
[Hypotheses will be added here]

## Investigation Design
[To be designed by inquiry agent]

## Validation Results
[To be validated]

## Learning Capture
[To be captured]

## Next Steps
Generate initial solution hypotheses
"""
  workspace_manager.initialize_workspace(
    agency_workspace,
    owner_id="reasoning_coordinator",
    content=workspace_content,
  )

  # Save initial workspace and save immediately
  test_artifacts.initial_workspace = workspace_content
  test_artifacts.save_artifacts()

  # Test initial hypothesis generation
  query = (
    "I want to explore approaches for distilling reasoning capabilities "
    "from large language models into smaller, more efficient versions. "
    "Let's analyze DeepSeek's recent breakthrough and design our own approach."
  )

  initial_msg = Message(
    content=query,
    metadata={
      AGENCY_WORKSPACE_KEY: agency_workspace,
    },
  )

  logger.debug(
    "Starting hypothesis generation for LLM distillation"
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

  # Save generated hypotheses and streaming content
  test_artifacts.generated_hypotheses = (
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
    "## Generated Hypotheses" in updated_content
  ), "Should have Generated Hypotheses section"
  assert (
    "[Hypotheses will be added here]"
    not in updated_content
  ), "Should have replaced placeholder"
  assert final_response.content in updated_content, (
    "Final response should be in workspace"
  )

  # Verify hypothesis structure
  assert "**Hypothesis:**" in updated_content, (
    "Should have at least one hypothesis"
  )
  assert "**Confidence:**" in updated_content, (
    "Should include confidence scores"
  )
  assert "**Evidence:**" in updated_content, (
    "Should include supporting evidence"
  )
  assert "**Test Criteria:**" in updated_content, (
    "Should include test criteria"
  )
