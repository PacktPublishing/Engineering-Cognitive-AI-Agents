"""Winston with comprehensive cognitive capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston_memory import MemoryWinston
from winston_multimodal import (
  MultimodalWinston,
)
from winston_plan import PlanningWinston
from winston_reason import (
  ReasoningWinston,
)

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class CognitiveWinston(BaseAgent):
  """Winston with comprehensive cognitive capabilities."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    # Register self first
    super().__init__(system, config, paths)

    # Initialize sub-agents with their own configs
    memory_config = AgentConfig.from_yaml(
      paths.config / "agents/winston_memory.yaml"
    )
    reasoning_config = AgentConfig.from_yaml(
      paths.config / "agents/winston_reason.yaml"
    )
    planning_config = AgentConfig.from_yaml(
      paths.config / "agents/winston_plan.yaml"
    )
    multimodal_config = AgentConfig.from_yaml(
      paths.config / "agents/winston_multimodal.yaml"
    )

    # Initialize sub-agents
    self.memory_agent = MemoryWinston(
      system, memory_config, paths
    )
    self.reasoning_agent = ReasoningWinston(
      system, reasoning_config, paths
    )
    self.planning_agent = PlanningWinston(
      system, planning_config, paths
    )
    self.multimodal_agent = MultimodalWinston(
      system, multimodal_config, paths
    )

  async def _process_private(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Process in private workspace first."""
    print(
      f"CognitiveWinston processing: {message.content}"
    )

    # Create message with shared workspace context for sub-agents
    sub_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        "shared_workspace": workspace,
      },
    )

    # Determine which agent should handle the message and stream responses
    if "image_path" in message.metadata:
      print("Routing to multimodal agent")
      async for (
        response
      ) in self.multimodal_agent.process(sub_message):
        yield workspace, response

    elif any(
      trigger in message.content.lower()
      for trigger in [
        "analyze",
        "understand",
        "explain why",
        "what's causing",
        "help me understand",
        "struggling with",
        "having trouble",
      ]
    ):
      print("Routing to reasoning agent")
      async for (
        response
      ) in self.reasoning_agent.process(sub_message):
        yield workspace, response

    elif any(
      trigger in message.content.lower()
      for trigger in [
        "plan",
        "organize",
        "schedule",
        "steps to",
        "how should i",
        "what's the best way to",
        "help me figure out how to",
        "execute",
        "start",
        "begin",
        "do",
        "implement",
        "carry out",
        "perform",
        "complete step",
      ]
    ):
      print("Routing to planning agent")
      async for (
        response
      ) in self.planning_agent.process(sub_message):
        yield workspace, response

    else:
      print("Routing to memory agent")
      async for response in self.memory_agent.process(
        sub_message
      ):
        yield workspace, response


class CognitiveWinstonChat(AgentChat):
  """Chat interface for cognitive Winston."""

  def __init__(self) -> None:
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config
      / "agents/winston_cognitive.yaml"
    )
    return CognitiveWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = CognitiveWinstonChat()
