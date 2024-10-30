"""Winston with cognitive workspace and planning capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class PlanningWinston(BaseAgent):
  """Winston with planning capabilities."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = (
      system.get_workspace_manager(self.id)
    )

  async def _process_private(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Develop initial plan in private workspace."""
    # Check if planning/execution needed
    needs_planning = self._needs_planning(message)
    is_execution = self._is_execution(message)

    if not (needs_planning or is_execution):
      return

    if needs_planning:
      async for result in self._develop_private_plan(
        message, workspace
      ):
        yield result
    else:
      async for (
        result
      ) in self._prepare_private_execution(
        message, workspace
      ):
        yield result

  async def _develop_private_plan(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Develop initial plan privately."""
    planning_prompt = f"""
    Create an initial plan for:
    {message.content}

    Using your private context:
    {workspace}

    Develop a draft plan including:
    1. Initial goal analysis
    2. Preliminary steps
    3. Potential challenges
    4. Resource requirements
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=planning_prompt,
        metadata={"type": "Private Planning"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield (
        workspace,
        response,
      )  # Stream response with current workspace

    # After processing, update private workspace with complete plan
    if accumulated_content:
      updated_workspace = (
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={"type": "Private Plan Draft"},
          ),
          self,
        )
      )
      # Final yield with updated workspace
      yield updated_workspace, Response(content="")

  async def _prepare_private_execution(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Prepare for plan execution privately."""
    execution_prompt = f"""
    Regarding execution request:
    {message.content}

    Review private execution context:
    {workspace}

    Prepare execution by:
    1. Identifying relevant plan steps
    2. Checking prerequisites
    3. Noting potential issues
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=execution_prompt,
        metadata={"type": "Private Execution Prep"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield (
        workspace,
        response,
      )  # Stream response with current workspace

    # After processing, update private workspace with execution notes
    if accumulated_content:
      updated_workspace = (
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={
              "type": "Private Execution Notes"
            },
          ),
          self,
        )
      )
      # Final yield with updated workspace
      yield updated_workspace, Response(content="")

  async def _process_shared(
    self,
    message: Message,
    private_workspace: str,
    shared_workspace: str,
  ) -> AsyncIterator[Response]:
    """Process in shared context."""
    if self._needs_planning(message):
      async for (
        response
      ) in self._refine_plan_with_context(
        private_workspace, shared_workspace
      ):
        yield response
    else:
      async for (
        response
      ) in self._execute_plan_with_context(
        private_workspace, shared_workspace
      ):
        yield response

  def _needs_planning(self, message: Message) -> bool:
    """Check if message needs planning."""
    return any(
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

  def _is_execution(self, message: Message) -> bool:
    """Check if message is execution request."""
    return any(
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
