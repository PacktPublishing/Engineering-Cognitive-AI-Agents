"""Inquiry Agent: Specialist agent for solution validation test design.

The Inquiry Agent is a key specialist in Winston's enhanced reasoning system,
responsible for designing tests to validate proposed solutions. It operates
as part of a coordinated reasoning system alongside Hypothesis and Validation agents.

Theoretical Foundation:
The agent implements a core aspect of the Free Energy Principle (FEP) by designing
empirical tests to reduce uncertainty. Through active inference, it:
1. Analyzes hypotheses to identify key validation points
2. Designs specific, practical tests
3. Defines clear success criteria
4. Enables systematic validation

Design Philosophy:
The agent implements systematic test design by:
1. Analyzing hypotheses and their test criteria from workspace content
2. Drawing on relevant testing patterns through memory integration
3. Generating practical validation approaches
4. Providing clear execution guidelines

Implementation Note:
The agent generates test designs in markdown format and returns the results
to the coordinator, which manages the workspace state centrally."""

from typing import Any

from winston.core.agent import (
  BaseAgent,
)
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System


class InquiryAgent(BaseAgent):
  """Designs validation tests informed by workspace state."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

  def _get_response_metadata(self) -> dict[str, Any]:
    """Get metadata for inquiry responses.

    Returns
    -------
    dict[str, Any]
        Metadata for inquiry responses
    """
    return {
      "is_reasoning_stage": True,
      "specialist_type": "inquiry",
    }
