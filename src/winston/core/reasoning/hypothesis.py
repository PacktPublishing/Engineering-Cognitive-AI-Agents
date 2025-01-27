"""Hypothesis Agent: Specialist agent for prediction generation.

The Hypothesis Agent implements a key aspect of the Free Energy Principle (FEP) by generating
testable predictions to reduce uncertainty. When faced with new situations or unclear
relationships, it proposes explanatory hypotheses that can be tested to improve understanding.

Design Philosophy:
The Hypothesis Agent addresses a fundamental challenge in cognitive architectures: reducing
uncertainty through testable predictions. Following FEP, it generates predictions that:
1. Identify areas of uncertainty in current understanding
2. Propose specific, testable explanations
3. Enable active inference through the Inquiry Agent
4. Support learning through the Validation Agent

Example Scenarios:

1. Technical Understanding
   Input: New approach to LLM distillation shows unexpected performance
   Uncertainty: Why the approach works better than previous methods
   Hypothesis: "Preserving reasoning traces during distillation maintains key capabilities"
   Testable via: Comparing reasoning path preservation across methods

2. User Interaction
   Input: User consistently modifies suggested code in particular ways
   Uncertainty: Underlying preferences in code style/approach
   Hypothesis: "User prefers explicit error handling over concise code"
   Testable via: Varying code suggestion styles

3. System Behavior
   Input: Certain tool combinations yield better results
   Uncertainty: Why these combinations are more effective
   Hypothesis: "Sequential tool use allows refinement of intermediate results"
   Testable via: Controlled tool sequence experiments

Key Principles:
- Focus on identifying and reducing uncertainty
- Generate specific, testable predictions
- Enable empirical validation
- Support continuous learning

The specialist's system prompt guides the LLM to:
1. Identify areas of uncertainty
2. Generate testable predictions
3. Specify validation criteria
4. Prioritize by potential impact

This design enables systematic uncertainty reduction while maintaining:
- Clear testability of predictions
- Empirical validation paths
- Learning opportunities
- Integration with FEP-based cognition

Implementation Note:
The Hypothesis Agent focuses purely on generating testable predictions about areas
of uncertainty. It works with the Inquiry Agent (which designs investigations) and
the Validation Agent (which evaluates evidence) to implement the full FEP cycle
of prediction, testing, and learning."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel, Field

from winston.core.agent import BaseAgent
from winston.core.agent_config import AgentConfig
from winston.core.paths import AgentPaths
from winston.core.protocols import System
from winston.core.tools import Tool

from ..agent import Message, Response
from .types import ReasoningContext


@dataclass
class Hypothesis:
  """A testable proposition with confidence and impact scores."""

  statement: str
  confidence: float  # 0.0 to 1.0
  impact: float  # 0.0 to 1.0
  evidence: list[str]


class GenerateHypothesesRequest(BaseModel):
  """Request to generate hypotheses."""

  query: str = Field(
    description="The query to generate hypotheses for"
  )
  similar_experiences: list[str] = Field(
    description="List of similar past experiences"
  )
  current_context: str = Field(
    description="Current episode context"
  )
  workspace_state: str = Field(
    description="Current workspace state"
  )


class GenerateHypothesesResponse(BaseModel):
  """Response containing generated hypotheses."""

  hypotheses: list[Hypothesis]
  reasoning: str


class HypothesisAgent(BaseAgent):
  """Generates hypotheses informed by memory and experience."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

    # Register the hypothesis generation tool
    tool = Tool(
      name="generate_hypotheses",
      description="Generate testable hypotheses based on context and experiences",
      handler=self._handle_generate_hypotheses,
      input_model=GenerateHypothesesRequest,
      output_model=GenerateHypothesesResponse,
    )
    self.system.register_tool(tool)
    self.system.grant_tool_access(self.id, [tool.name])

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    """Process with memory-enhanced hypothesis generation."""
    # Extract reasoning context
    context: ReasoningContext = message.metadata[
      "reasoning_context"
    ]

    # Prepare the request
    request = GenerateHypothesesRequest(
      query=message.content,
      similar_experiences=[
        exp.content
        for exp in context.memory.similar_experiences
      ],
      current_context=context.memory.current_episode.summary,
      workspace_state=context.memory.working_memory.summary,
    )

    # Let BaseAgent handle the conversation using system prompt
    async for response in self._handle_conversation(
      message
    ):
      yield response

  async def _handle_generate_hypotheses(
    self, request: GenerateHypothesesRequest
  ) -> GenerateHypothesesResponse:
    """Handle hypothesis generation request."""
    # Parse the LLM completion into structured hypotheses
    hypotheses = self._parse_hypotheses(
      self.state.last_response
    )

    return GenerateHypothesesResponse(
      hypotheses=hypotheses,
      reasoning=self.state.last_response,
    )

  def _parse_hypotheses(
    self, completion: str
  ) -> list[Hypothesis]:
    """Parse completion into structured hypotheses."""
    hypotheses = []
    current_hypothesis = None
    current_evidence = []

    for line in completion.split("\n"):
      line = line.strip()

      if line.startswith("Hypothesis:"):
        # Save previous hypothesis if exists
        if current_hypothesis:
          hypotheses.append(
            Hypothesis(
              statement=current_hypothesis[
                "statement"
              ],
              confidence=current_hypothesis[
                "confidence"
              ],
              impact=current_hypothesis["impact"],
              evidence=current_evidence,
            )
          )

        # Start new hypothesis
        current_hypothesis = {
          "statement": line.replace(
            "Hypothesis:", ""
          ).strip()
        }
        current_evidence = []

      elif line.startswith("Confidence:"):
        if current_hypothesis:
          current_hypothesis["confidence"] = float(
            line.replace("Confidence:", "").strip()
          )

      elif line.startswith("Impact:"):
        if current_hypothesis:
          current_hypothesis["impact"] = float(
            line.replace("Impact:", "").strip()
          )

      elif line.startswith("-") and current_hypothesis:
        current_evidence.append(
          line.replace("-", "").strip()
        )

    # Add final hypothesis
    if current_hypothesis:
      hypotheses.append(
        Hypothesis(
          statement=current_hypothesis["statement"],
          confidence=current_hypothesis["confidence"],
          impact=current_hypothesis["impact"],
          evidence=current_evidence,
        )
      )

    return hypotheses
