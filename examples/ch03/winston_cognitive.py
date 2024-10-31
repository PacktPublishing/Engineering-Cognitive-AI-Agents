"""Winston with comprehensive cognitive capabilities."""

from pathlib import Path
from typing import AsyncIterator

from metacog import MetacognitionAgent
from winston_memory import MemoryAgent
from winston_multimodal import (
  MultimodalAgent,
)
from winston_plan import PlanningAgent
from winston_reason import (
  ReasoningAgent,
)

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class CognitiveAgent(BaseAgent):
  """Agent with comprehensive cognitive capabilities."""

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
    metacog_config = AgentConfig.from_yaml(
      paths.config / "agents/metacog.yaml"
    )

    # Initialize sub-agents
    self.memory_agent = MemoryAgent(
      system, memory_config, paths
    )
    self.reasoning_agent = ReasoningAgent(
      system, reasoning_config, paths
    )
    self.planning_agent = PlanningAgent(
      system, planning_config, paths
    )
    self.multimodal_agent = MultimodalAgent(
      system, multimodal_config, paths
    )
    self.metacog_agent = MetacognitionAgent(
      system, metacog_config, paths
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process in private workspace first."""
    print(
      f"CognitiveWinston processing: {message.content}"
    )

    # Create message with shared workspace ID for sub-agents
    sub_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        "shared_workspace": self.workspace_path,
      },
    )

    # Route to appropriate agent
    if self.multimodal_agent.can_handle(message):
      print("Routing to multimodal agent")
      agent = self.multimodal_agent
    elif self.reasoning_agent.can_handle(message):
      print("Routing to reasoning agent")
      agent = self.reasoning_agent
    elif self.planning_agent.can_handle(message):
      print("Routing to planning agent")
      agent = self.planning_agent
    else:
      print("Routing to memory agent")
      agent = self.memory_agent

    # Process with selected agent
    async for response in agent.process(sub_message):
      yield response

    # Process with metacognition agent
    async for _ in self.metacog_agent.process(
      sub_message
    ):
      pass


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
    return CognitiveAgent(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = CognitiveWinstonChat()
