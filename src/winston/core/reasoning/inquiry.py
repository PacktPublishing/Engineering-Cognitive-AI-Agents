"""Inquiry Agent: Specialist agent for investigation design.

The Inquiry Agent plays a crucial role in Winston's reasoning system by designing
targeted investigations to validate hypotheses. This specialist analyzes hypotheses
and plans specific actions to gather evidence, ensuring efficient and meaningful
testing of predictions.

Architecture Overview:
```mermaid
graph TD
    IA[Inquiry Agent] -->|Analyzes| H[Hypotheses]
    IA -->|Considers| T[Available Tools]

    subgraph "Design Process"
        H -->|Uncertainty Analysis| UA[Key Uncertainties]
        H -->|Tool Selection| TS[Tool Planning]
        H -->|Information Gaps| IG[Gap Analysis]

        UA --> ID[Investigation Design]
        TS --> ID
        IG --> ID
    end

    ID -->|Produces| IP[Investigation Plan]
    ID -->|Optimizes| IG[Information Gain]

    IP -->|Guides| VC[Validation Coordinator]
    IG -->|Informs| PR[Priority Order]
```

Design Philosophy:
The Inquiry Agent addresses a fundamental challenge in cognitive architectures:
designing efficient and effective investigations to validate hypotheses. This
mirrors human cognitive processes where we plan specific actions to test our
predictions and gather evidence.

Example Scenarios:

1. Direct Investigation
   Input: Hypothesis about evening creativity peaks
   Analysis: Need for time-based creativity metrics
   Plan: "Track writing output quality across different times"
   Tools: Writing prompts, style analysis

2. Comparative Analysis
   Input: Hypothesis about emotional engagement
   Analysis: Need to compare different topic types
   Plan: "Test writing responses to varied emotional stimuli"
   Tools: Topic generation, engagement metrics

3. Pattern Validation
   Input: Hypothesis about tool effectiveness
   Analysis: Need to isolate tool impact
   Plan: "Compare ideation with/without visual aids"
   Tools: Visual brainstorming, text-only exercises

Key Architectural Principles:
- Focus purely on investigation design (single responsibility)
- Optimize for information gain
- Consider available tool capabilities
- Structure clear, actionable plans

The specialist's system prompt guides the LLM to:
1. Analyze hypotheses for key uncertainties
2. Identify optimal investigation methods
3. Plan specific tool usage
4. Structure clear validation criteria

This design enables sophisticated investigation planning while maintaining:
- Clean separation of concerns
- Efficient resource usage
- Maximum information gain
- Clear success criteria

Implementation Note:
While the Inquiry Agent designs sophisticated investigation plans, it performs
no direct hypothesis generation or validation. It simply creates structured
plans for gathering evidence, leaving the actual validation to the Validation
Agent. This separation of concerns ensures the agent can focus purely on its
investigation design role while leaving other aspects to appropriate specialists.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from winston.core.agent import BaseAgent

from ..agent import Message, Response
from .types import ReasoningContext


@dataclass
class InvestigationStep:
  """A single step in an investigation plan."""

  description: str
  expected_outcome: str
  tools_needed: list[str]


@dataclass
class InvestigationPlan:
  """A plan to investigate a hypothesis."""

  hypothesis_statement: str
  steps: list[InvestigationStep]
  information_gain: float  # 0.0 to 1.0
  resource_cost: float  # 0.0 to 1.0


@dataclass
class InvestigationDesignResult:
  """Result of investigation design process."""

  plans: list[InvestigationPlan]
  reasoning: str


class InquiryAgent(BaseAgent):
  """Designs investigations informed by memory and experience."""

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    """Process with memory-enhanced investigation design."""

    # Extract reasoning context
    context: ReasoningContext = message.metadata[
      "reasoning_context"
    ]
    hypotheses = message.metadata.get("hypotheses", [])

    # Design investigations using memory context
    result = await self._design_investigations(
      message,
      context,
      hypotheses,
    )

    # Yield the structured result
    yield Response(
      content=result.reasoning,
      metadata={
        **message.metadata,
        "investigation_plans": [
          vars(p) for p in result.plans
        ],
      },
    )

  async def _design_investigations(
    self,
    message: Message,
    context: ReasoningContext,
    hypotheses: list[dict[str, Any]],
  ) -> InvestigationDesignResult:
    """Design investigations using memory context."""

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
      similar_experiences,
      current_episode,
      workspace,
    )

    # Get completion from LLM
    completion = await self.system.llm.complete(prompt)

    # Parse completion into investigation plans
    plans = self._parse_investigation_plans(completion)

    return InvestigationDesignResult(
      plans=plans,
      reasoning=completion,
    )

  def _build_memory_enhanced_prompt(
    self,
    query: str,
    hypotheses: list[dict[str, Any]],
    similar_experiences: list[Any],
    current_episode: Any,
    workspace: Any,
  ) -> str:
    """Build prompt incorporating memory context."""

    # Format hypotheses
    hypothesis_context = "\n".join(
      f"- Hypothesis: {h['statement']} (Confidence: {h['confidence']}, Impact: {h['impact']})"
      for h in hypotheses
    )

    # Format similar experiences
    experience_context = "\n".join(
      f"- Previous similar investigation: {exp.content}"
      for exp in similar_experiences
    )

    # Format current episode context
    episode_context = (
      f"Current context: {current_episode.summary}"
    )

    # Format workspace state
    workspace_context = (
      f"Working memory state: {workspace.summary}"
    )

    # Combine into full prompt
    return f"""Given the following context:

Current Hypotheses:
{hypothesis_context}

Previous Experiences:
{experience_context}

{episode_context}

{workspace_context}

And the current query:
{query}

Design investigation plans that:
1. Test each hypothesis effectively
2. Leverage available tools and resources
3. Consider past investigation approaches
4. Maximize information gain vs cost
5. Account for current context

For each investigation plan, provide:
- Hypothesis being tested
- Investigation steps (with tools needed)
- Expected outcomes
- Information gain score (0-1)
- Resource cost score (0-1)

Format as:
Hypothesis: <statement>
Information Gain: <score>
Resource Cost: <score>
Steps:
1. <description>
   Tools: <tool1>, <tool2>
   Expected: <outcome>
2. <description>
   Tools: <tool3>
   Expected: <outcome>
...

Design investigation plans for the top 2-3 hypotheses by impact * confidence."""

  def _parse_investigation_plans(
    self, completion: str
  ) -> list[InvestigationPlan]:
    """Parse completion into structured investigation plans."""

    plans = []
    current_plan = None
    current_steps = []

    for line in completion.split("\n"):
      line = line.strip()

      if line.startswith("Hypothesis:"):
        # Save previous plan if exists
        if current_plan:
          plans.append(
            InvestigationPlan(
              hypothesis_statement=current_plan[
                "hypothesis"
              ],
              steps=current_steps,
              information_gain=current_plan[
                "information_gain"
              ],
              resource_cost=current_plan[
                "resource_cost"
              ],
            )
          )

        # Start new plan
        current_plan = {
          "hypothesis": line.replace(
            "Hypothesis:", ""
          ).strip()
        }
        current_steps = []

      elif line.startswith("Information Gain:"):
        if current_plan:
          current_plan["information_gain"] = float(
            line.replace(
              "Information Gain:", ""
            ).strip()
          )

      elif line.startswith("Resource Cost:"):
        if current_plan:
          current_plan["resource_cost"] = float(
            line.replace("Resource Cost:", "").strip()
          )

      elif line.strip().isdigit() and current_plan:
        # Start of new step
        current_step = {
          "description": "",
          "tools": [],
          "expected": "",
        }

      elif line.startswith("Tools:") and current_plan:
        if current_step:
          current_step["tools"] = [
            t.strip()
            for t in line.replace("Tools:", "").split(
              ","
            )
          ]

      elif (
        line.startswith("Expected:") and current_plan
      ):
        if current_step:
          current_step["expected"] = line.replace(
            "Expected:", ""
          ).strip()
          current_steps.append(
            InvestigationStep(
              description=current_step["description"],
              tools_needed=current_step["tools"],
              expected_outcome=current_step[
                "expected"
              ],
            )
          )

      elif (
        current_plan
        and current_step
        and not line.startswith(
          ("Tools:", "Expected:")
        )
      ):
        current_step["description"] = line

    # Add final plan
    if current_plan:
      plans.append(
        InvestigationPlan(
          hypothesis_statement=current_plan[
            "hypothesis"
          ],
          steps=current_steps,
          information_gain=current_plan[
            "information_gain"
          ],
          resource_cost=current_plan["resource_cost"],
        )
      )

    return plans
