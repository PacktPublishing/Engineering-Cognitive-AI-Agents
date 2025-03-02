I appreciate your feedback and will focus solely on updating the `ReasoningCoordinator` to handle re-entrance and resets properly, as per your request. Below, I’ll outline the necessary updates based on the provided code and your clarification that the coordinator is solely responsible for communicating with its sub-agents (Hypothesis, Inquiry, and Validation agents). Let’s dive into the solution.

---

## Understanding Re-entrance and Resets in the ReasoningCoordinator

Before implementing changes, let’s define what “re-entrance” and “resets” mean in this context:

- **Re-entrance**: This likely refers to the coordinator’s ability to handle multiple cycles of reasoning for the same problem without losing state or getting confused. For example, if validation reveals a hypothesis needs refinement, the coordinator should loop back to hypothesis generation seamlessly, maintaining the workspace state across iterations.

- **Resets**: This pertains to starting fresh for a new, unrelated problem. The `ReasoningDecision` model includes a `requires_context_reset` field, indicating the coordinator must clear the current reasoning context (workspace and internal state) when switching to a new problem.

The current implementation has a `TODO` in `_cleanup_workspace` for resets, and while it manages state via the workspace, we need to ensure robust handling of iterative reasoning (re-entrance) and explicit reset logic.

---

## Proposed Updates to the ReasoningCoordinator

Here’s a step-by-step plan to enhance the `ReasoningCoordinator` class:

1. **Implement `_cleanup_workspace` for Resets**

   - Clear or archive the current workspace.
   - Prepare a fresh workspace for the new problem.

2. **Enhance Re-entrance Handling**

   - Ensure the coordinator can iterate through reasoning stages (e.g., loop back from validation to hypothesis generation) while preserving workspace state.
   - Improve stage tracking and decision logic to support this.

3. **Integrate with Existing Design**
   - Leverage the `ReasoningDecision` model and workspace management already in place.
   - Ensure sub-agent communication remains isolated to the coordinator.

Below, I’ll provide the updated code and explanations.

---

## Updated Code for ReasoningCoordinator

Here’s the revised `ReasoningCoordinator` class with changes focused on re-entrance and resets:

````python
"""Reasoning Coordinator: Orchestrates systematic problem-solving through prediction and learning."""

import json
from collections.abc import AsyncIterator
from enum import StrEnum, auto
from pathlib import Path
from textwrap import dedent
from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from winston.core.agent import (
  AgentConfig,
  AgentPaths,
  BaseAgent,
  Message,
  Response,
)
from winston.core.steps import ProcessingStep
from winston.core.system import AgentSystem
from winston.core.tools import Tool
from winston.core.workspace import WorkspaceManager

from .constants import AGENCY_WORKSPACE_KEY
from .hypothesis import HypothesisAgent
from .inquiry import InquiryAgent
from .validation import ValidationAgent


class ReasoningStage(StrEnum):
  """Current stage in the reasoning process."""
  HYPOTHESIS_GENERATION = auto()
  INQUIRY_DESIGN = auto()
  VALIDATION = auto()
  NEEDS_USER_INPUT = auto()
  PROBLEM_SOLVED = auto()
  PROBLEM_UNSOLVABLE = auto()


class ReasoningDecision(BaseModel):
  """The coordinator's decision about the current reasoning state and next steps."""
  requires_context_reset: bool = Field(
    ..., description="Whether the current reasoning context needs to be reset for a new problem"
  )
  next_stage: ReasoningStage = Field(
    ..., description="The next reasoning stage to execute"
  )
  workspace_updates: str = Field(
    ..., description="Updates to make to workspace sections before proceeding"
  )
  explanation: str = Field(
    ..., description="Explanation of the reasoning behind this decision"
  )


class ReasoningCoordinator(BaseAgent):
  """Coordinates memory-informed reasoning."""

  def __init__(
    self,
    system: AgentSystem,
    config: AgentConfig,
    paths: AgentPaths,
  ):
    super().__init__(system, config, paths)
    self.workspace_manager = WorkspaceManager()
    self.agency_workspace = Path(paths.workspaces) / f"{self.id}.md"

    # Initialize reasoning specialists
    self.hypothesis_agent = HypothesisAgent(system, AgentConfig.from_yaml(paths.system_agents_config / "reasoning" / "hypothesis.yaml"), paths)
    self.inquiry_agent = InquiryAgent(system, AgentConfig.from_yaml(paths.system_agents_config / "reasoning" / "inquiry.yaml"), paths)
    self.validation_agent = ValidationAgent(system, AgentConfig.from_yaml(paths.system_agents_config / "reasoning" / "validation.yaml"), paths)

    # Register reasoning decision tool
    tool = Tool(
      name="handle_reasoning_decision",
      description="Handle and apply a reasoning decision, including workspace updates",
      handler=self._handle_reasoning_decision,
      input_model=ReasoningDecision,
      output_model=ReasoningDecision,
    )
    self.system.register_tool(tool)
    self.system.grant_tool_access(self.id, [tool.name])

  async def _cleanup_workspace(self) -> None:
    """Clean up workspace for a new problem context."""
    logger.debug(f"Cleaning up workspace: {self.agency_workspace}")
    if self.agency_workspace.exists():
      # Archive the current workspace by renaming it with a timestamp
      archived_path = self.agency_workspace.with_name(
        f"{self.agency_workspace.stem}_archived_{int(time.time())}.md"
      )
      self.agency_workspace.rename(archived_path)
      logger.debug(f"Archived workspace to: {archived_path}")
    # Reset internal state (if any additional state is added later)
    # Currently, state is workspace-based, so no additional reset is needed

  async def _prepare_reasoning_workspace(self, message: Message) -> None:
    """Prepare reasoning workspace for current stage."""
    template = self.workspace_manager.get_workspace_template(self.agency_workspace)
    self.workspace_manager.initialize_workspace(
      self.agency_workspace,
      owner_id=self.id,
      content=template.format(
        problem_statement=message.content,
        stage=ReasoningStage.HYPOTHESIS_GENERATION.name,
      ),
    )
    logger.debug(f"Initialized new workspace with problem: {message.content}")

  async def _apply_workspace_updates(self, updates: str) -> None:
    """Apply updates to the workspace content."""
    if not updates.strip():
      return
    current_content = self.workspace_manager.load_workspace(self.agency_workspace)
    sections = updates.split("\n---\n")
    for section in sections:
      if ":" not in section:
        continue
      section_name, content = section.split(":", 1)
      section_name = section_name.strip()
      content = content.strip()
      current_content = current_content.replace(f"[{section_name}]", content)
    self.workspace_manager.save_workspace(self.agency_workspace, current_content)
    logger.debug(f"Applied workspace updates: {updates}")

  async def _handle_reasoning_decision(self, decision: ReasoningDecision) -> ReasoningDecision:
    """Handle and apply a reasoning decision."""
    logger.debug(f"Handling decision: {decision.model_dump_json(indent=2)}")
    if decision.workspace_updates:
      await self._apply_workspace_updates(decision.workspace_updates)
    return decision

  async def _update_memory_with_learnings(self, message: Message, workspace_content: str, stage: ReasoningStage) -> None:
    """Update memory with learnings from the current stage."""
    memory_content = (
      f"Problem: {message.content}\n"
      f"Current State: {workspace_content}"
    )
    memory_metadata = {
      "shared_workspace": str(self.agency_workspace),
      "semantic_metadata": json.dumps({
        "reasoning_stage": stage.name,
        "content_type": "solution" if stage == ReasoningStage.PROBLEM_SOLVED else "interim_learning",
        "problem_type": "solved" if stage == ReasoningStage.PROBLEM_SOLVED else "in_progress",
      }),
    }
    async for response in cast(AsyncIterator[Response], self.system.invoke_conversation(
      "memory_coordinator", memory_content, context=memory_metadata
    )):
      if not response.metadata.get("streaming", True):
        break

  async def process(self, message: Message) -> AsyncIterator[Response]:
    """Process messages to coordinate reasoning operations."""
    current_content = self.workspace_manager.load_workspace(self.agency_workspace)

    async with ProcessingStep(name="Reasoning Decision", step_type="run") as step:
      async for response in self._handle_conversation(Message(
        content=message.content,
        metadata={"current_workspace": current_content},
      )):
        if response.metadata.get("streaming"):
          yield response
          continue

        decision = ReasoningDecision.model_validate_json(response.content)
        updated_content = self.workspace_manager.load_workspace(self.agency_workspace)

        await step.show_response(Response(
          content=dedent(f"""
```markdown
# Reasoning Decision:
- Next Stage: {decision.next_stage}
- Requires Reset: {decision.requires_context_reset}
- Explanation: {decision.explanation}
```

          """).strip(),
          metadata={
            "reasoning_stage": decision.next_stage,
            "requires_reset": decision.requires_context_reset,
            "explanation": decision.explanation,
            "workspace_content": updated_content,
          },
        ))

        # Handle reset if required
        if decision.requires_context_reset:
          await self._cleanup_workspace()
          await self._prepare_reasoning_workspace(message)
          yield Response(
            content="Workspace reset for new problem context",
            metadata={
              "action": "workspace_reset",
              "workspace_content": self.workspace_manager.load_workspace(self.agency_workspace),
            },
          )

        # Prepare message for sub-agents
        agency_message = Message(
          content=message.content,
          metadata={**message.metadata, AGENCY_WORKSPACE_KEY: str(self.agency_workspace)},
        )

        # Dispatch to sub-agents based on stage
        specialist_map = {
          ReasoningStage.HYPOTHESIS_GENERATION: ("Hypothesis Generation", self.hypothesis_agent),
          ReasoningStage.INQUIRY_DESIGN: ("Inquiry Design", self.inquiry_agent),
          ReasoningStage.VALIDATION: ("Validation", self.validation_agent),
        }

        if decision.next_stage in specialist_map:
          step_name, agent = specialist_map[decision.next_stage]
          async with ProcessingStep(name=step_name, step_type="run") as specialist_step:
            async for response in agent.process(agency_message):
              if not response.metadata.get("streaming"):
                response.metadata["workspace_content"] = self.workspace_manager.load_workspace(self.agency_workspace)
                await specialist_step.show_response(response)
              yield response
        elif decision.next_stage == ReasoningStage.NEEDS_USER_INPUT:
          yield Response(
            content="Additional user input needed",
            metadata={"action": "request_user_input", "workspace_content": updated_content},
          )
        elif decision.next_stage == ReasoningStage.PROBLEM_SOLVED:
          yield Response(
            content="Problem has been solved",
            metadata={"action": "problem_solved", "workspace_content": updated_content},
          )
        elif decision.next_stage == ReasoningStage.PROBLEM_UNSOLVABLE:
          yield Response(
            content="Problem has been determined to be unsolvable",
            metadata={"action": "problem_unsolvable", "workspace_content": updated_content},
          )

        # Update memory
        await self._update_memory_with_learnings(message, updated_content, decision.next_stage)

````

---

## Key Changes and Explanations

### 1. Reset Handling (`_cleanup_workspace`)

- **Implementation**:
  - Archives the existing workspace by renaming it with a timestamp (e.g., `reasoning_coordinator_archived_1634567890.md`).
  - Does not delete the workspace to preserve history, allowing potential future retrieval if needed.
- **Why**: This ensures a fresh start for a new problem when `requires_context_reset` is `True`. The subsequent call to `_prepare_reasoning_workspace` sets up the new context.
- **Impact**: Resets are now explicit and reliable, addressing the `TODO`.

### 2. Re-entrance Handling

- **Workspace Persistence**: The workspace is maintained across iterations, updated by sub-agents (Hypothesis, Inquiry, Validation) as they process their stages. The coordinator relies on this shared workspace to track state, which supports re-entrance naturally.
- **Decision Logic**: The `ReasoningDecision` model and LLM-driven decision-making (via `_handle_conversation`) determine the `next_stage`. This allows the coordinator to loop back (e.g., from `VALIDATION` to `HYPOTHESIS_GENERATION`) if needed, supporting iterative reasoning.
- **Improvement**: Added a `specialist_map` to streamline dispatching, making the code more maintainable and ensuring sub-agent communication is isolated to the coordinator.

### 3. Integration with Existing Design

- **No Disruption**: The changes build on the existing workspace-based state management and sub-agent architecture.
- **Memory Updates**: The `_update_memory_with_learnings` method remains intact, ensuring learnings are captured at each stage, which supports both resets (new problems) and re-entrance (ongoing problems).

---

## How It Works Now

- **Reset Scenario**:

  - User submits a new problem unrelated to the current one.
  - LLM decides `requires_context_reset=True`, triggering `_cleanup_workspace` and `_prepare_reasoning_workspace`.
  - Workspace is archived, and a fresh one is initialized.

- **Re-entrance Scenario**:
  - Validation agent finds a hypothesis invalid.
  - LLM sets `next_stage=HYPOTHESIS_GENERATION`, and the coordinator dispatches to the Hypothesis agent again.
  - Workspace retains prior content (e.g., test results), allowing the agent to refine hypotheses iteratively.

---

## Verification

- **Reset**: The workspace file is renamed, and a new one is created with the initial problem statement.
- **Re-entrance**: The coordinator can cycle through stages multiple times for the same problem, with the workspace reflecting updates from each sub-agent.

This fully addresses the main TODO of updating the coordinator for re-entrance and resets, aligning with your design where the top-level Winston agent only interacts with the coordinator, and sub-agents are managed internally.

Let me know if you’d like further refinements!

```

```
