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

from collections.abc import AsyncIterator
from enum import Enum, auto
from pathlib import Path

from winston.core.agent import (
  AgentConfig,
  AgentPaths,
  BaseAgent,
  Message,
  Response,
)
from winston.core.system import AgentSystem
from winston.core.workspace import WorkspaceManager

from .constants import AGENCY_WORKSPACE_KEY
from .hypothesis import HypothesisAgent
from .inquiry import InquiryAgent
from .validation import ValidationAgent


class ReasoningStage(Enum):
  """Current stage in the reasoning process."""

  INITIAL_ANALYSIS = auto()
  HYPOTHESIS_GENERATION = auto()
  INQUIRY_DESIGN = auto()
  VALIDATION = auto()
  NEEDS_USER_INPUT = auto()
  PROBLEM_SOLVED = auto()
  PROBLEM_UNSOLVABLE = auto()


class EnhancedReasoningCoordinator(BaseAgent):
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
      config,
      paths,
    )
    self.inquiry_agent = InquiryAgent(
      system,
      config,
      paths,
    )
    self.validation_agent = ValidationAgent(
      system,
      config,
      paths,
    )

  async def _determine_reasoning_stage(
    self,
    message: Message,
    workspace_content: str,
  ) -> ReasoningStage:
    """Determine current reasoning stage and next steps.

    Analyzes workspace content and message to determine:
    - If this is a new/different problem (context switch)
    - Current stage in reasoning process
    - Whether we need user input
    - If problem is solved or unsolvable
    """
    # TODO: Implement stage determination logic
    # For now, always start at initial analysis
    return ReasoningStage.INITIAL_ANALYSIS

  async def _prepare_reasoning_workspace(
    self,
    message: Message,
  ) -> None:
    """Prepare reasoning workspace for current stage.

    - Checks if current problem vs new problem
    - Maintains or resets workspace based on context
    - Updates reasoning state markers
    """
    current_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )

    # Determine if this is a new problem/context switch
    current_stage = (
      await self._determine_reasoning_stage(
        message,
        current_content,
      )
    )

    if (
      current_stage == ReasoningStage.INITIAL_ANALYSIS
    ):
      # Initialize fresh workspace using registered template
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
          stage=current_stage.name,
        ),
      )

  async def _gather_relevant_knowledge(
    self,
    message: Message,
    current_stage: ReasoningStage,
  ) -> AsyncIterator[Response]:
    """Get relevant knowledge based on reasoning stage."""
    # Customize query based on stage
    query = message.content
    if (
      current_stage == ReasoningStage.INITIAL_ANALYSIS
    ):
      query = f"Find similar problems and their solutions: {message.content}"
    elif (
      current_stage
      == ReasoningStage.HYPOTHESIS_GENERATION
    ):
      query = f"Find successful solution approaches for: {message.content}"
    elif (
      current_stage == ReasoningStage.INQUIRY_DESIGN
    ):
      query = f"Find effective validation strategies for: {message.content}"
    elif current_stage == ReasoningStage.VALIDATION:
      query = f"Find relevant success criteria and lessons learned for: {message.content}"

    memory_message = Message(
      content=query,
      metadata={
        "shared_workspace": self.workspace_path,
      },
    )

    async for (
      response
    ) in self.system.invoke_conversation(
      "memory_coordinator",
      memory_message.content,
      context=memory_message.metadata,
    ):
      yield response

  async def _needs_user_input(
    self,
    message: Message,
    workspace_content: str,
  ) -> bool:
    """Determine if we need to consult user.

    Checks:
    - If we have enough information to proceed
    - If we need clarification
    - If we need to validate approach
    - If we need to confirm success
    """
    # TODO: Implement user input determination logic
    return False

  async def _update_memory_with_learnings(
    self,
    message: Message,
    workspace_content: str,
    stage: ReasoningStage,
  ) -> None:
    """Update memory with insights based on stage.

    Different updates for:
    - New problem patterns identified
    - Successful solution approaches
    - Effective validation strategies
    - Final learnings when problem solved
    """
    if stage == ReasoningStage.PROBLEM_SOLVED:
      memory_message = Message(
        content=f"""Please analyze and store key learnings from this solved problem:
Problem: {message.content}
Solution Process: {workspace_content}""",
        metadata={
          "shared_workspace": self.workspace_path,
        },
      )
    else:
      memory_message = Message(
        content=f"""Please store interim learnings from reasoning stage {stage.name}:
Problem: {message.content}
Current State: {workspace_content}""",
        metadata={
          "shared_workspace": self.workspace_path,
        },
      )

    async for (
      response
    ) in self.system.invoke_conversation(
      "memory_coordinator",
      memory_message.content,
      context=memory_message.metadata,
    ):
      if not response.metadata.get("streaming"):
        break

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process with dynamic reasoning based on current stage."""

    # 1. Determine current reasoning stage
    current_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )
    current_stage = (
      await self._determine_reasoning_stage(
        message,
        current_content,
      )
    )

    # 2. Prepare/update workspace for current stage
    await self._prepare_reasoning_workspace(message)

    # 3. Get relevant knowledge for current stage
    async for (
      knowledge
    ) in self._gather_relevant_knowledge(
      message,
      current_stage,
    ):
      if knowledge.metadata.get("streaming"):
        yield knowledge
        continue
      # Update workspace with stage-appropriate knowledge
      current_content = (
        self.workspace_manager.load_workspace(
          self.agency_workspace
        )
      )
      self.workspace_manager.save_workspace(
        self.agency_workspace,
        current_content.replace(
          "[Knowledge from memory about similar problems/solutions]",
          knowledge.content,
        ),
      )

    # 4. Create agency message
    agency_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        AGENCY_WORKSPACE_KEY: self.agency_workspace,
      },
    )

    # 5. Dispatch to appropriate specialist based on stage
    if (
      current_stage
      == ReasoningStage.HYPOTHESIS_GENERATION
    ):
      async for (
        response
      ) in self.hypothesis_agent.process(
        agency_message
      ):
        yield response
    elif (
      current_stage == ReasoningStage.INQUIRY_DESIGN
    ):
      async for response in self.inquiry_agent.process(
        agency_message
      ):
        yield response
    elif current_stage == ReasoningStage.VALIDATION:
      async for (
        response
      ) in self.validation_agent.process(
        agency_message
      ):
        yield response

    # 6. Check if we need user input
    if await self._needs_user_input(
      message, current_content
    ):
      # Update workspace to indicate waiting for user
      self.workspace_manager.save_workspace(
        self.agency_workspace,
        current_content.replace(
          "# Next Steps",
          "# Next Steps\nWaiting for user input:",
        ),
      )
      return

    # 7. Update memory with stage-appropriate learnings
    await self._update_memory_with_learnings(
      message,
      current_content,
      current_stage,
    )
