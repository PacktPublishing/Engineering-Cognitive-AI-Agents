"""Test hypothesis generation capabilities."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from loguru import logger
from pydantic import BaseModel

from winston.core.agent import AgentConfig
from winston.core.memory.storage import Knowledge
from winston.core.messages import Message
from winston.core.paths import AgentPaths
from winston.core.reasoning.hypothesis import (
  HypothesisAgent,
)
from winston.core.reasoning.types import (
  MemoryContext,
  ReasoningContext,
)
from winston.core.system import AgentSystem


# Mock types for testing
class MockEpisodeContext(BaseModel):
  """Mock episode context for testing."""

  summary: str


class MockWorkspaceState(BaseModel):
  """Mock workspace state for testing."""

  summary: str


@pytest.mark.asyncio
async def test_hypothesis_generation():
  """Test hypothesis generation and pattern analysis."""
  # Setup
  logger.info("Starting test_hypothesis_generation")
  with tempfile.TemporaryDirectory() as temp_dir:
    temp_root = Path(temp_dir)
    project_root = Path(__file__).parent.parent.parent
    paths = AgentPaths(
      root=temp_root,
      system_root=project_root,
    )

    system = AgentSystem()
    config = AgentConfig.from_yaml(
      paths.system_agents_config
      / "reasoning"
      / "hypothesis.yaml"
    )
    agent = HypothesisAgent(system, config, paths)

    # Create mock knowledge entries
    now = datetime.now()
    similar_experiences = [
      Knowledge(
        id="exp1",
        content="User shows higher engagement in evening sessions",
        context={},
        created_at=now,
        updated_at=now,
      ),
      Knowledge(
        id="exp2",
        content="Creative writing quality peaks after 8pm",
        context={},
        created_at=now,
        updated_at=now,
      ),
      Knowledge(
        id="exp3",
        content="Morning sessions focus more on technical tasks",
        context={},
        created_at=now,
        updated_at=now,
      ),
    ]

    # Mock memory context
    memory_context = MemoryContext(
      similar_experiences=similar_experiences,
      current_episode=MockEpisodeContext(
        summary="User working on creative writing task at 9pm"
      ),
      working_memory=MockWorkspaceState(
        summary="High engagement and flow state observed"
      ),
    )

    # Test 1: Pattern Detection
    pattern_msg = Message(
      content="Analyze time-of-day impact on creative performance",
      metadata={
        "reasoning_context": ReasoningContext(
          memory=memory_context, metadata={}
        )
      },
    )

    logger.debug("Starting Test 1: Pattern Detection")
    hypotheses = []  # Store hypotheses for comparison
    async for response in agent.process(pattern_msg):
      logger.info(
        f"Pattern analysis response: {response.content}"
      )
      logger.debug(f"Metadata: {response.metadata}")

      # Verify hypotheses structure
      assert "hypotheses" in response.metadata
      hypotheses = response.metadata["hypotheses"]
      assert len(hypotheses) > 0

      # Verify hypothesis fields
      for hypothesis in hypotheses:
        assert "statement" in hypothesis
        assert "confidence" in hypothesis
        assert "impact" in hypothesis
        assert "evidence" in hypothesis
        assert isinstance(
          hypothesis["confidence"], float
        )
        assert isinstance(hypothesis["impact"], float)
        assert isinstance(hypothesis["evidence"], list)

    # Test 2: Alternative Hypothesis
    alternative_msg = Message(
      content="Consider alternative factors beyond time-of-day",
      metadata={
        "reasoning_context": ReasoningContext(
          memory=memory_context, metadata={}
        )
      },
    )

    logger.debug(
      "Starting Test 2: Alternative Hypothesis"
    )
    async for response in agent.process(
      alternative_msg
    ):
      logger.info(
        f"Alternative analysis response: {response.content}"
      )
      logger.debug(f"Metadata: {response.metadata}")

      # Verify different hypotheses are generated
      new_hypotheses = response.metadata["hypotheses"]
      assert len(new_hypotheses) > 0
      # Verify at least some hypotheses are different
      assert any(
        h1["statement"] != h2["statement"]
        for h1 in hypotheses
        for h2 in new_hypotheses
      )
