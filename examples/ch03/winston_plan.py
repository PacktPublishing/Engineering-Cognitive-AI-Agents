"""Winston with cognitive workspace and planning capabilities."""

from collections.abc import AsyncIterator
from pathlib import Path
from textwrap import dedent

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class PlanningWinston(BaseAgent):
  """Winston with memory and planning capabilities."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = (
      system.get_workspace_manager(
        agent_id=self.id,
      )
    )

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    # Add metadata check to prevent recursion
    if message.metadata.get("type") in [
      "planning",
      "execution",
    ]:
      # If this is already a planning/execution request, process normally
      async for response in super().process(message):
        yield response
      return

    # First update workspace with new information
    updated_workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Detect if this message needs planning
    needs_planning = any(
      trigger in message.content.lower()
      for trigger in [
        "plan",
        "organize",
        "schedule",
        "steps to",
        "how should i",
        "what's the best way to",
        "help me figure out how to",
      ]
    )

    # Detect if this is a plan execution request
    is_execution = any(
      trigger in message.content.lower()
      for trigger in [
        "execute",
        "start",
        "begin",
        "do",
        "implement",
        "carry out",
        "perform",
        "complete step",
      ]
    )

    if needs_planning:
      # Create and execute plan
      async for response in self.create_plan(message):
        yield response
      return
    elif is_execution:
      # Execute plan step
      async for response in self.execute_plan_step(
        message
      ):
        yield response
      return

    # Otherwise generate normal response using workspace context
    response_prompt = f"""
            Given this user message:
            {message.content}

            And your cognitive workspace:
            {updated_workspace}

            Provide a response that:
            1. Demonstrates awareness of previous interactions
            2. Shows understanding of user preferences
            3. Maintains conversation context
            4. Is helpful and engaging
            """

    async for response in super().process(
      Message(
        content=response_prompt,
        context={"workspace": updated_workspace},
      )
    ):
      yield response

  async def create_plan(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    # First update the workspace with the new information
    workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Generate plan using the full context
    planning_prompt = dedent(
      f"""
            Create a detailed plan for this request:
            {message.content}

            Using the context from your workspace:
            {workspace}

            Develop a comprehensive plan that includes:
            1. Clear goal definition
            2. Step-by-step breakdown of actions
            3. Dependencies and prerequisites
            4. Success criteria and milestones
            5. Potential challenges and mitigation strategies

            Structure the plan clearly in markdown format, using:
            - Headers for major sections
            - Lists for steps and details
            - Checkboxes for trackable items
            - Notes for important considerations
            """
    ).strip()

    # Stream the planning response
    accumulated_plan = ""
    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=planning_prompt,
        metadata={"type": "Planning Request"},
      ),
    ):
      accumulated_plan += response.content
      yield response

    # Update workspace with the complete plan
    _ = await self.workspace_manager.update_workspace(
      Message(
        content=accumulated_plan,
        metadata={"type": "New Plan"},
      ),
      self,
    )

  async def execute_plan_step(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Execute a step in the current plan."""
    # Get current workspace state
    workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Generate execution analysis and updates
    execution_prompt = dedent(
      f"""
            Regarding this execution request:
            {message.content}

            And the current workspace state:
            {workspace}

            Analyze the execution request and:
            1. Identify which plan step is being executed
            2. Evaluate any prerequisites or dependencies
            3. Determine appropriate actions
            4. Consider potential challenges
            5. Define success criteria for this step

            Then execute the step by:
            1. Providing clear instructions or actions
            2. Noting any important considerations
            3. Suggesting specific approaches
            4. Identifying next steps

            Structure your response in markdown format.
            """
    ).strip()

    # Stream the execution response
    accumulated_execution = ""
    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=execution_prompt,
        metadata={"type": "Plan Execution Request"},
      ),
    ):
      accumulated_execution += response.content
      yield response

    # Update workspace with execution results
    _ = await self.workspace_manager.update_workspace(
      Message(
        content=accumulated_execution,
        metadata={"type": "Plan Step Executed"},
      ),
      self,
    )


class PlanningWinstonChat(AgentChat):
  """Chat interface for planning Winston."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston_plan.yaml"
    )
    return PlanningWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = PlanningWinstonChat()
