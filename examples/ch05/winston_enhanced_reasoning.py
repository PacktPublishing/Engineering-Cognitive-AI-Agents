"""Winston with enhanced reasoning capabilities."""

from pathlib import Path
from typing import AsyncIterator, cast

from loguru import logger

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import (
  Message,
  Response,
)
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent
from winston.core.reasoning.coordinator import (
  ReasoningCoordinator,
)
from winston.core.steps import ProcessingStep
from winston.core.system import AgentSystem, System
from winston.ui.chainlit_app import AgentChat


class EnhancedReasoningWinston(BaseAgent):
  """Winston with enhanced reasoning capabilities."""

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    """Process message using reasoning coordinator.

    Parameters
    ----------
    message : Message
        The incoming message to process

    Yields
    ------
    Response
        Responses from processing the message
    """
    logger.info(
      f"Delegating to reasoning coordinator: {message.content}"
    )

    # Create message with shared workspace
    coordinator_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        "shared_workspace": self.workspace_path,
      },
    )

    # Delegate to reasoning coordinator
    async with ProcessingStep(
      name="Reasoning Coordinator agent",
      step_type="run",
    ) as step:
      # Get the response iterator
      responses = (
        await self.system.invoke_conversation(
          agent_id="reasoning_coordinator",
          content=coordinator_message.content,
          context=coordinator_message.metadata,
        )
      )
      # Iterate through responses
      async for response in responses:
        if response.metadata.get("streaming", False):
          yield response
          continue
        logger.trace(
          f"Reasoning coordinator response: {response}"
        )
        message.metadata["current_workspace"] = (
          response.content
        )
        await step.show_response(response)

    async for (
      response
    ) in self.generate_streaming_response(message):
      yield response


class EnhancedReasoningWinstonChat(AgentChat):
  """Chat interface for memory-enabled Winston."""

  def __init__(self) -> None:
    # Set up paths with both application and system roots
    example_root = Path(__file__).parent
    project_root = (
      example_root.parent.parent
    )  # Navigate up to project root
    self.paths = AgentPaths(
      root=example_root,  # For application-specific config
      system_root=project_root,  # For system-wide config
    )
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    """Create Winston instance with reasoning capabilities.

    Parameters
    ----------
    system : System
        The system instance

    Returns
    -------
    Agent
        The configured Winston agent
    """
    # Create and register reasoning coordinator
    coordinator_config = AgentConfig.from_yaml(
      self.paths.system_agents_config
      / "reasoning"
      / "coordinator.yaml"
    )
    system.register_agent(
      ReasoningCoordinator(
        system=cast(AgentSystem, system),
        config=coordinator_config,
        paths=self.paths,
      )
    )

    # Create Winston agent
    config = AgentConfig.from_yaml(
      self.paths.config
      / "agents"
      / "winston_enhanced_reasoning.yaml"
    )
    return EnhancedReasoningWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = EnhancedReasoningWinstonChat()
