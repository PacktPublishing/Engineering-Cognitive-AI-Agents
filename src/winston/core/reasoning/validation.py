"""Validation Agent: Specialist agent for evaluating test results and validating hypotheses.

The Validation Agent is a key specialist in Winston's enhanced reasoning system,
responsible for evaluating test results against hypotheses. It operates
as part of a coordinated reasoning system alongside Hypothesis and Inquiry agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by evaluating
empirical evidence to update beliefs. Through active inference, it:
1. Analyzes test results against predictions
2. Updates confidence levels based on evidence
3. Identifies needed refinements
4. Guides learning from outcomes

Design Philosophy:
The agent implements systematic validation by:
1. Analyzing test results against success criteria
2. Evaluating evidence quality and relevance
3. Updating hypothesis confidence levels
4. Identifying refinement opportunities

Implementation Note:
The agent generates validation analyses in markdown format and returns the results
to the coordinator, which manages the workspace state centrally."""

from typing import Any

from winston.core.agent import (
  BaseAgent,
)
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System


class ValidationAgent(BaseAgent):
  """Evaluates test results and validates hypotheses."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

  def _get_response_metadata(self) -> dict[str, Any]:
    """Get metadata for validation responses.

    Returns
    -------
    dict[str, Any]
        Metadata for validation responses
    """
    return {
      "is_reasoning_stage": True,
      "specialist_type": "validation",
    }
