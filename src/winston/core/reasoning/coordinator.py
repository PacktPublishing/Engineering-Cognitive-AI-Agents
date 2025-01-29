"""Reasoning Coordinator: Orchestrates systematic problem-solving through prediction and learning.

The Reasoning Coordinator implements a problem-solving cycle by coordinating specialist
agents that work together to understand, solve, and learn from challenges. While this
process aligns with the Free Energy Principle's uncertainty reduction, its primary
purpose is pragmatic: solving real problems effectively.

Architecture Overview:
```mermaid
graph TD
    RC[Reasoning Coordinator] -->|State Management| WS[Workspace]
    RC -->|Problem Analysis| HA[Hypothesis Agent]
    HA -->|Solution Predictions| RC
    RC -->|Solution Testing| IA[Inquiry Agent]
    IA -->|Test Strategy| RC
    RC -->|Results Analysis| VA[Validation Agent]
    VA -->|Learning| RC
    RC <-->|Knowledge Exchange| MC[Memory Coordinator]
```

Design Philosophy:
The reasoning system implements an iterative problem-solving cycle that:
1. Maintains state through a workspace-based approach
2. Tracks reasoning progress through defined stages:
   - Initial Analysis
   - Hypothesis Generation
   - Inquiry Design
   - Validation
3. Integrates with memory for:
   - Retrieving relevant past experiences
   - Storing new insights and learnings
4. Recognizes when user input is needed

Core Process Flow:
1. State Determination
   - Check if continuing existing problem or starting new one
   - Determine current reasoning stage
   - Decide if user input needed

2. Knowledge Integration
   - Gather stage-appropriate knowledge from memory
   - Update workspace with relevant context
   - Track solution progress

3. Specialist Coordination
   - Dispatch to appropriate specialist based on stage
   - Hypothesis Agent: Solution generation
   - Inquiry Agent: Test design
   - Validation Agent: Results analysis

4. Learning Capture
   - Store stage-specific insights
   - Update memory with new learnings
   - Preserve solution patterns

The coordinator ensures these components work together in a dynamic cycle,
maintaining state between interactions and building a growing repertoire of
effective problem-solving strategies. It recognizes that complex problems
often require multiple iterations and user interactions to reach a solution.

Example Flow:
When facing a problem (e.g. "How to improve this system's performance?"):
1. Initialize workspace with problem statement
2. Gather relevant past experiences from memory
3. Generate initial hypotheses
4. Check if more information needed from user
5. Design and run tests when ready
6. Validate results and capture learnings
7. Either continue cycle or mark problem as solved

Key Principles:
- Maintain clear state through workspace
- Integrate memory at each stage
- Recognize need for user input
- Learn from both successes and failures
- Build solution patterns from experience
- Support iterative problem-solving
"""

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
    ...,
    description="Whether the current reasoning context needs to be reset for a new problem",
  )
  next_stage: ReasoningStage = Field(
    ...,
    description="The next reasoning stage to execute",
  )
  workspace_updates: str = Field(
    ...,
    description="Updates to make to workspace sections before proceeding",
  )
  explanation: str = Field(
    ...,
    description="Explanation of the reasoning behind this decision",
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

    # Use the workspace path initialized by the system
    self.workspace_manager = WorkspaceManager()
    self.agency_workspace = (
      Path(paths.workspaces) / f"{self.id}.md"
    )

    # Initialize reasoning specialists with agency workspace
    self.hypothesis_agent = HypothesisAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "hypothesis.yaml"
      ),
      paths,
    )
    self.inquiry_agent = InquiryAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "inquiry.yaml"
      ),
      paths,
    )
    self.validation_agent = ValidationAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "validation.yaml"
      ),
      paths,
    )

    # Register the reasoning decision tool
    tool = Tool(
      name="handle_reasoning_decision",
      description="Handle and apply a reasoning decision, including any workspace updates, and return the validated decision",
      handler=self._handle_reasoning_decision,
      input_model=ReasoningDecision,
      output_model=ReasoningDecision,
    )
    self.system.register_tool(tool)
    self.system.grant_tool_access(self.id, [tool.name])

  async def _apply_workspace_updates(
    self, updates: str
  ) -> None:
    """Apply updates to the workspace content.

    Parameters
    ----------
    updates : str
        String containing section updates in format:
        "section_name: content\n---\nsection_name2: content2"
    """
    if not updates.strip():
      return

    current_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )

    # Parse updates string into section updates
    sections = updates.split("\n---\n")
    for section in sections:
      if ":" not in section:
        continue
      section_name, content = section.split(":", 1)
      section_name = section_name.strip()
      content = content.strip()

      # Replace section placeholder with new content
      current_content = current_content.replace(
        f"[{section_name}]",
        content,
      )

    self.workspace_manager.save_workspace(
      self.agency_workspace,
      current_content,
    )

  async def _handle_reasoning_decision(
    self,
    decision: ReasoningDecision,
  ) -> ReasoningDecision:
    """Handle and apply a reasoning decision.

    Parameters
    ----------
    decision : ReasoningDecision
        The reasoning decision to process

    Returns
    -------
    ReasoningDecision
        The validated decision after processing
    """
    logger.debug(
      f"Handling reasoning decision: {decision.model_dump_json(indent=2)}"
    )

    if decision.workspace_updates:
      logger.debug(
        f"Applying workspace updates: {decision.workspace_updates}"
      )
      await self._apply_workspace_updates(
        decision.workspace_updates
      )
    return decision

  async def _cleanup_workspace(self) -> None:
    """Clean up workspace for a new problem context."""
    # TODO: Implement cleanup logic
    pass

  async def _prepare_reasoning_workspace(
    self,
    message: Message,
  ) -> None:
    """Prepare reasoning workspace for current stage.

    - Initializes fresh workspace using template
    - Sets up initial problem context
    """
    template = (
      self.workspace_manager.get_workspace_template(
        self.agency_workspace
      )
    )
    self.workspace_manager.initialize_workspace(
      self.agency_workspace,
      owner_id=self.id,
      content=template.format(
        problem_statement=message.content,
        stage=ReasoningStage.HYPOTHESIS_GENERATION.name,
      ),
    )

  async def _update_memory_with_learnings(
    self,
    message: Message,
    workspace_content: str,
    stage: ReasoningStage,
  ) -> None:
    """
    Update memory with learnings from the current stage.

    Parameters
    ----------
    message : Message
        The original user message
    workspace_content : str
        Current workspace content
    stage : ReasoningStage
        Current reasoning stage
    """
    if stage == ReasoningStage.PROBLEM_SOLVED:
      memory_message = Message(
        content=f"""Please analyze and store key learnings from this solved problem:
Problem: {message.content}
Solution Process: {workspace_content}""",
        metadata={
          "shared_workspace": self.workspace_path,
          "semantic_metadata": json.dumps(
            {
              "reasoning_stage": stage.name,
              "content_type": "solution",
              "problem_type": "solved",
            }
          ),
        },
      )
    else:
      memory_message = Message(
        content=f"""Please store interim learnings from reasoning stage {stage.name}:
Problem: {message.content}
Current State: {workspace_content}""",
        metadata={
          "shared_workspace": self.workspace_path,
          "semantic_metadata": json.dumps(
            {
              "reasoning_stage": stage.name,
              "content_type": "interim_learning",
              "problem_type": "in_progress",
            }
          ),
        },
      )

    # Process responses from memory coordinator
    async for response in cast(
      AsyncIterator[Response],
      self.system.invoke_conversation(
        "memory_coordinator",
        memory_message.content,
        context=memory_message.metadata,
      ),
    ):
      if not response.metadata.get("streaming", True):
        break

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process messages to coordinate reasoning operations.

    The LLM will automatically use the handle_reasoning_decision tool
    due to required_tool in config. The tool handler validates and applies
    workspace updates, while this method handles the flow control and
    specialist dispatching.
    """
    # Get current workspace content
    current_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )

    # Initial decision making phase
    async with ProcessingStep(
      name="Reasoning Decision",
      step_type="run",
    ) as step:
      # Let the LLM evaluate the message using system prompt and tools
      async for response in self._handle_conversation(
        Message(
          content=message.content,
          metadata={
            "current_workspace": current_content,
          },
        )
      ):
        if response.metadata.get("streaming"):
          yield response
          continue

        logger.debug(
          f"Reasoning decision: {response.content}"
        )

        # Tool has been executed, response contains the decision
        decision = (
          ReasoningDecision.model_validate_json(
            response.content
          )
        )

        # Get updated workspace content after decision
        updated_content = (
          self.workspace_manager.load_workspace(
            self.agency_workspace
          )
        )

        # Show decision in step
        await step.show_response(
          Response(
            content=dedent(f"""
```markdown
# Reasoning Decision:
- Next Stage: {decision.next_stage}
- Requires Reset: {decision.requires_context_reset}
- Explanation: {decision.explanation}
```""").strip(),
            metadata={
              "reasoning_stage": decision.next_stage,
              "requires_reset": decision.requires_context_reset,
              "explanation": decision.explanation,
              "workspace_content": updated_content,
            },
          )
        )

        # Handle context reset if needed
        if decision.requires_context_reset:
          logger.debug("Cleaning up workspace")
          await self._cleanup_workspace()
          logger.debug("Preparing reasoning workspace")
          await self._prepare_reasoning_workspace(
            message
          )
          yield Response(
            content="Workspace reset for new problem context",
            metadata={
              "action": "workspace_reset",
              "workspace_content": self.workspace_manager.load_workspace(
                self.agency_workspace
              ),
            },
          )

        # Create agency message with workspace context
        agency_message = Message(
          content=message.content,
          metadata={
            **message.metadata,
            AGENCY_WORKSPACE_KEY: self.agency_workspace,
          },
        )

        # Dispatch to appropriate specialist based on decided stage
        match decision.next_stage:
          case ReasoningStage.HYPOTHESIS_GENERATION:
            async with ProcessingStep(
              name="Hypothesis Generation",
              step_type="run",
            ) as hypothesis_step:
              async for (
                response
              ) in self.hypothesis_agent.process(
                agency_message
              ):
                if not response.metadata.get(
                  "streaming"
                ):
                  response.metadata[
                    "workspace_content"
                  ] = self.workspace_manager.load_workspace(
                    self.agency_workspace
                  )
                  await hypothesis_step.show_response(
                    response
                  )
                yield response

          case ReasoningStage.INQUIRY_DESIGN:
            async with ProcessingStep(
              name="Inquiry Design",
              step_type="run",
            ) as inquiry_step:
              async for (
                response
              ) in self.inquiry_agent.process(
                agency_message
              ):
                if not response.metadata.get(
                  "streaming"
                ):
                  response.metadata[
                    "workspace_content"
                  ] = self.workspace_manager.load_workspace(
                    self.agency_workspace
                  )
                  await inquiry_step.show_response(
                    response
                  )
                yield response

          case ReasoningStage.VALIDATION:
            async with ProcessingStep(
              name="Validation",
              step_type="run",
            ) as validation_step:
              async for (
                response
              ) in self.validation_agent.process(
                agency_message
              ):
                if not response.metadata.get(
                  "streaming"
                ):
                  response.metadata[
                    "workspace_content"
                  ] = self.workspace_manager.load_workspace(
                    self.agency_workspace
                  )
                  await validation_step.show_response(
                    response
                  )
                yield response

          case ReasoningStage.NEEDS_USER_INPUT:
            yield Response(
              content="Additional user input needed",
              metadata={
                "action": "request_user_input",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

          case ReasoningStage.PROBLEM_SOLVED:
            yield Response(
              content="Problem has been solved",
              metadata={
                "action": "problem_solved",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

          case ReasoningStage.PROBLEM_UNSOLVABLE:
            yield Response(
              content="Problem has been determined to be unsolvable",
              metadata={
                "action": "problem_unsolvable",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

        # Update memory with stage-appropriate learnings
        async with ProcessingStep(
          name="Memory Update",
          step_type="run",
        ) as memory_step:
          logger.debug(
            "Updating memory with learnings"
          )
          await self._update_memory_with_learnings(
            message,
            self.workspace_manager.load_workspace(
              self.agency_workspace
            ),
            decision.next_stage,
          )
          await memory_step.show_response(
            Response(
              content=dedent(f"""
```markdown
# Memory Update
- Stage: {decision.next_stage}
- Status: Complete
```""").strip(),
              metadata=message.metadata,
            )
          )
