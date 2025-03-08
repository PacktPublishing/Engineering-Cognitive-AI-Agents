"""Hypothesis Agent: Generates testable predictions about patterns and relationships.

The Hypothesis Agent is a key specialist in Winston's enhanced reasoning system,
responsible for analyzing workspace content and generating testable hypotheses about
patterns in observations and experiences. It operates as part of a coordinated
reasoning system alongside Inquiry and Validation agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by generating
testable predictions to reduce uncertainty. Through active inference, it:
1. Identifies areas of uncertainty in current understanding
2. Proposes specific, testable hypotheses with confidence and impact ratings
3. Provides evidence supporting each hypothesis
4. Defines clear test criteria for validation

Design Philosophy:
The agent implements systematic pattern analysis and hypothesis generation by:
1. Analyzing workspace content for relevant patterns and context
2. Forming specific, testable hypotheses about the current problem
3. Ranking hypotheses by potential impact and confidence
4. Providing clear validation criteria for testing

Output Format:
Each hypothesis is structured with:
- Hypothesis statement: A clear, testable prediction
- Confidence score: Numerical rating from 0.0 to 1.0
- Impact score: Potential significance rating from 0.0 to 1.0
- Evidence: Supporting points from workspace content
- Test Criteria: Specific tests to validate the hypothesis

Implementation Note:
The agent generates hypotheses in markdown format and returns the results
to the coordinator, which manages the workspace state centrally."""

from typing import Any

from winston.core.agent import (
  BaseAgent,
)
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System


class HypothesisAgent(BaseAgent):
  """Generates testable predictions about patterns in observations and experiences.

  Analyzes workspace content to form specific hypotheses with confidence ratings,
  impact assessments, supporting evidence, and validation criteria.
  """

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

  def _get_response_metadata(self) -> dict[str, Any]:
    """Get metadata for hypothesis responses.

    Returns
    -------
    dict[str, Any]
        Metadata for hypothesis responses
    """
    return {
      "is_reasoning_stage": True,
      "specialist_type": "hypothesis",
    }
