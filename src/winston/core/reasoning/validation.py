"""Validation Agent: Specialist agent for hypothesis validation.

The Validation Agent plays a crucial role in Winston's reasoning system by evaluating
evidence against hypotheses and updating confidence levels. This specialist analyzes
investigation results to validate predictions and refine Winston's understanding.

Architecture Overview:
```mermaid
graph TD
    VA[Validation Agent] -->|Analyzes| E[Evidence]
    VA -->|References| H[Hypotheses]

    subgraph "Validation Process"
        E -->|Evidence Analysis| EA[Evidence Evaluation]
        H -->|Criteria Check| CC[Success Criteria]
        H -->|Confidence Update| CU[Confidence Scoring]

        EA --> VD[Validation Decision]
        CC --> VD
        CU --> VD
    end

    VD -->|Updates| CM[Confidence Models]
    VD -->|Refines| IS[Investigation Strategy]

    CM -->|Informs| HA[Hypothesis Agent]
    IS -->|Guides| IA[Inquiry Agent]
```

Design Philosophy:
The Validation Agent addresses a fundamental challenge in cognitive architectures:
evaluating evidence to validate or refute hypotheses. This mirrors human cognitive
processes where we assess new information against our predictions and update our
understanding accordingly.

Example Scenarios:

1. Direct Validation
   Input: Evening writing samples show consistent quality increase
   Hypothesis: "User's creative peak occurs in evening hours"
   Analysis: Strong correlation between time and quality
   Result: Increased confidence, refined timing model

2. Pattern Confirmation
   Input: Emotional topic responses show deeper engagement
   Hypothesis: "Emotional topics trigger deeper engagement"
   Analysis: Consistent pattern across multiple samples
   Result: Hypothesis supported, engagement model updated

3. Tool Impact Assessment
   Input: Comparative analysis of tool usage
   Hypothesis: "Visual tools improve ideation process"
   Analysis: Mixed results across different contexts
   Result: Hypothesis refined with context specificity

Key Architectural Principles:
- Focus purely on validation analysis (single responsibility)
- Provide clear confidence updates
- Support investigation refinement
- Enable continuous learning

The specialist's system prompt guides the LLM to:
1. Evaluate evidence against success criteria
2. Update confidence levels based on results
3. Identify investigation improvements
4. Refine understanding models

This design enables sophisticated validation while maintaining:
- Clean separation of concerns
- Evidence-based decisions
- Continuous improvement
- Clear confidence tracking

Implementation Note:
While the Validation Agent makes sophisticated evaluations of evidence and
hypotheses, it performs no direct hypothesis generation or investigation
design. It simply validates results and updates confidence levels, leaving
other aspects to appropriate specialists. This separation of concerns ensures
the agent can focus purely on its validation role while maintaining system
cohesion.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from winston.core.agent import BaseAgent

from ..agent import Message, Response
from .types import ReasoningContext


class ValidationEvidence(BaseModel):
  """Evidence collected from an investigation."""

  hypothesis_statement: str = Field(
    description="The hypothesis being validated"
  )
  investigation_results: list[str] = Field(
    description="Results from the investigation",
    default_factory=list,
  )
  success_criteria_met: list[bool] = Field(
    description="Whether each success criterion was met",
    default_factory=list,
  )
  unexpected_findings: list[str] = Field(
    description="Any unexpected observations",
    default_factory=list,
  )


@dataclass
class ValidationResult:
  """Result of validating a single hypothesis."""

  hypothesis_statement: str
  is_supported: bool
  confidence_update: (
    float  # Change in confidence (-1.0 to 1.0)
  )
  evidence_for: list[str]
  evidence_against: list[str]


@dataclass
class ValidationAnalysisResult:
  """Result of validation analysis process."""

  validations: list[ValidationResult]
  reasoning: str


class ValidationAgent(BaseAgent):
  """Validates hypotheses using memory and investigation results."""

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    """Process with memory-enhanced validation."""

    # Extract reasoning context
    context: ReasoningContext = message.metadata[
      "reasoning_context"
    ]
    hypotheses = message.metadata.get("hypotheses", [])
    investigation_plans = message.metadata.get(
      "investigation_plans", []
    )

    # Validate hypotheses using memory context
    result = await self._validate_hypotheses(
      message,
      context,
      hypotheses,
      investigation_plans,
    )

    # Yield the structured result
    yield Response(
      content=result.reasoning,
      metadata={
        **message.metadata,
        "validation_results": [
          vars(v) for v in result.validations
        ],
      },
    )

  async def _validate_hypotheses(
    self,
    message: Message,
    context: ReasoningContext,
    hypotheses: list[dict[str, Any]],
    investigation_plans: list[dict[str, Any]],
  ) -> ValidationAnalysisResult:
    """Validate hypotheses using memory context."""

    # Extract relevant experiences
    similar_experiences = (
      context.memory.similar_experiences
    )
    current_episode = context.memory.current_episode
    workspace = context.memory.working_memory

    # Build prompt incorporating memory context
    prompt = self._build_memory_enhanced_prompt(
      message.content,
      hypotheses,
      investigation_plans,
      similar_experiences,
      current_episode,
      workspace,
    )

    # Get completion from LLM
    completion = await self.system.llm.complete(prompt)

    # Parse completion into validation results
    validations = self._parse_validations(completion)

    return ValidationAnalysisResult(
      validations=validations,
      reasoning=completion,
    )

  def _build_memory_enhanced_prompt(
    self,
    query: str,
    hypotheses: list[dict[str, Any]],
    investigation_plans: list[dict[str, Any]],
    similar_experiences: list[Any],
    current_episode: Any,
    workspace: Any,
  ) -> str:
    """Build prompt incorporating memory context."""

    # Format hypotheses and investigations
    context_sections = []

    # Add hypotheses
    hypothesis_context = "\n".join(
      f"- Hypothesis: {h['statement']} (Confidence: {h['confidence']}, Impact: {h['impact']})"
      for h in hypotheses
    )
    context_sections.append(
      f"Current Hypotheses:\n{hypothesis_context}"
    )

    # Add investigation plans
    if investigation_plans:
      plan_context = "\n".join(
        f"- Plan for '{p['hypothesis_statement']}':\n  "
        f"Steps: {len(p['steps'])}, "
        f"Info Gain: {p['information_gain']}, "
        f"Cost: {p['resource_cost']}"
        for p in investigation_plans
      )
      context_sections.append(
        f"Investigation Plans:\n{plan_context}"
      )

    # Add similar experiences
    experience_context = "\n".join(
      f"- Previous similar validation: {exp.content}"
      for exp in similar_experiences
    )
    context_sections.append(
      f"Previous Experiences:\n{experience_context}"
    )

    # Add current episode context
    context_sections.append(
      f"Current context: {current_episode.summary}"
    )

    # Add workspace state
    context_sections.append(
      f"Working memory state: {workspace.summary}"
    )

    # Combine all context sections
    full_context = "\n\n".join(context_sections)

    # Build full prompt
    return f"""Given the following context:

{full_context}

And the current query:
{query}

Validate each hypothesis considering:
1. Evidence from investigations
2. Similar past experiences
3. Current context
4. Logical consistency
5. Alternative explanations

For each hypothesis, provide:
- Whether it is supported
- Change in confidence (-1 to +1)
- Supporting evidence
- Contradicting evidence

Format as:
Hypothesis: <statement>
Supported: <yes/no>
Confidence Change: <score>
Evidence For:
- <point 1>
- <point 2>
Evidence Against:
- <point 1>
- <point 2>
...

Validate all hypotheses, ordered by original impact * confidence."""

  def _parse_validations(
    self, completion: str
  ) -> list[ValidationResult]:
    """Parse completion into structured validation results."""

    validations = []
    current_validation = None
    evidence_for = []
    evidence_against = []

    for line in completion.split("\n"):
      line = line.strip()

      if line.startswith("Hypothesis:"):
        # Save previous validation if exists
        if current_validation:
          validations.append(
            ValidationResult(
              hypothesis_statement=current_validation[
                "statement"
              ],
              is_supported=current_validation[
                "supported"
              ],
              confidence_update=current_validation[
                "confidence_change"
              ],
              evidence_for=evidence_for,
              evidence_against=evidence_against,
            )
          )

        # Start new validation
        current_validation = {
          "statement": line.replace(
            "Hypothesis:", ""
          ).strip()
        }
        evidence_for = []
        evidence_against = []

      elif line.startswith("Supported:"):
        if current_validation:
          current_validation["supported"] = (
            line.replace("Supported:", "")
            .strip()
            .lower()
            == "yes"
          )

      elif line.startswith("Confidence Change:"):
        if current_validation:
          current_validation["confidence_change"] = (
            float(
              line.replace(
                "Confidence Change:", ""
              ).strip()
            )
          )

      elif line == "Evidence For:":
        collecting_for = True
        collecting_against = False

      elif line == "Evidence Against:":
        collecting_for = False
        collecting_against = True

      elif line.startswith("-"):
        evidence = line.replace("-", "").strip()
        if collecting_for:
          evidence_for.append(evidence)
        elif collecting_against:
          evidence_against.append(evidence)

    # Add final validation
    if current_validation:
      validations.append(
        ValidationResult(
          hypothesis_statement=current_validation[
            "statement"
          ],
          is_supported=current_validation["supported"],
          confidence_update=current_validation[
            "confidence_change"
          ],
          evidence_for=evidence_for,
          evidence_against=evidence_against,
        )
      )

    return validations
