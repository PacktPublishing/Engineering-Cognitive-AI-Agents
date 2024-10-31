"""Winston with cognitive workspace and planning capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class PlanningAgent(BaseAgent):
  """Winston with planning capabilities."""

  @classmethod
  def can_handle(cls, message: Message) -> bool:
    """Check if this agent can handle the message."""
    return cls._needs_planning(
      message
    ) or cls._is_execution(message)

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Develop initial plan in private workspace."""
    print(
      f"PlanningWinston processing: {message.content}"
    )

    # Check if planning/execution needed
    needs_planning = self._needs_planning(message)
    is_execution = self._is_execution(message)

    if not (needs_planning or is_execution):
      return

    private_workspace, shared_workspace = (
      self._get_workspaces(message)
    )

    shared_context = ""
    if shared_workspace:
      shared_context = f"""
      And considering the shared context:
      {shared_workspace}
      """

    accumulated_content: list[str] = []

    if needs_planning:
      async for result in self._develop_plan(
        message,
        private_workspace,
        shared_context,
      ):
        accumulated_content.append(result.content)
        yield result
    else:
      async for result in self._execute_step(
        message,
        private_workspace,
        shared_context,
      ):
        accumulated_content.append(result.content)
        yield result

    if not accumulated_content:
      return

    await self._update_workspaces(
      Message(
        content="".join(accumulated_content),
        metadata={
          **message.metadata,
          "type": "Planning",
        },
      ),
    )

  async def _develop_plan(
    self,
    message: Message,
    private_workspace: str,
    shared_context: str,
  ) -> AsyncIterator[Response]:
    """Develop initial plan privately."""
    response_prompt = f"""
    Create an initial plan for:
    {message.content}

    Using your private context:
    {private_workspace}

    {shared_context}

    Develop a draft plan including:
    1. Initial goal analysis
    2. Preliminary steps
    3. Potential challenges
    4. Resource requirements
    """

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=response_prompt,
        metadata={"type": "Private Planning"},
      )
    ):
      yield response

  async def _execute_step(
    self,
    message: Message,
    private_workspace: str,
    shared_context: str,
  ) -> AsyncIterator[Response]:
    """Prepare for plan execution privately."""

    print(f"Executing step: {message.content}")

    execution_prompt = f"""
    Regarding execution request:
    {message.content}

    Review private execution context:
    {private_workspace}

    {shared_context}

    Prepare execution by:
    1. Identifying relevant plan steps
    2. Checking prerequisites
    3. Noting potential issues
    """

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=execution_prompt,
        metadata={"type": "Private Execution Prep"},
      )
    ):
      yield response

  @classmethod
  def _needs_planning(cls, message: Message) -> bool:
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

  @classmethod
  def _is_execution(cls, message: Message) -> bool:
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
    return PlanningAgent(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = PlanningWinstonChat()
