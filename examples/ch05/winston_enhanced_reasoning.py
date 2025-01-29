"""Winston with enhanced reasoning capabilities."""

from pathlib import Path
from typing import AsyncIterator, cast

from loguru import logger

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.memory.coordinator import (
  MemoryCoordinator,
)
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
    self,
    message: Message,
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
      f"Delegating to reasoning coordinator: {message.content}",
    )

    # Create message with shared workspace
    coordinator_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        "shared_workspace": self.workspace_path,
      },
    )

    # Main reasoning flow
    async with ProcessingStep(
      name="Reasoning Coordinator agent",
      step_type="run",
    ) as reasoning_step:
      # Track current phase for UI organization
      current_specialist: str | None = None
      memory_update_active = False
      final_workspace_content: str | None = None

      # Get the response iterator and iterate through responses
      async for response in cast(
        AsyncIterator[Response],
        self.system.invoke_conversation(
          agent_id="reasoning_coordinator",
          content=coordinator_message.content,
          context=coordinator_message.metadata,
        ),
      ):
        # Skip streaming responses
        if response.metadata.get("streaming", False):
          continue

        # Handle reasoning flow
        if response.metadata.get("reasoning_stage"):
          # Show decision in reasoning step
          logger.trace(
            f"Reasoning decision: {response.content}",
          )
          await reasoning_step.show_response(response)

          # Start specialist phase if needed
          specialist_type = str(
            response.metadata.get(
              "specialist_type", ""
            )
          )
          if (
            specialist_type
            and specialist_type != current_specialist
          ):
            current_specialist = specialist_type
            async with ProcessingStep(
              name=f"{specialist_type} agent",
              step_type="run",
            ) as specialist_step:
              await specialist_step.show_response(
                response
              )
              # Update workspace content from specialist
              if response.content:
                final_workspace_content = str(
                  response.content
                )

          # Start memory update phase if needed
          if (
            response.metadata.get("memory_update")
            and not memory_update_active
          ):
            memory_update_active = True
            # Just show the memory update response in our step
            # The memory coordinator will handle its own nested steps
            await reasoning_step.show_response(
              response
            )
            memory_update_active = False

          continue

        # Handle final response
        if not response.metadata.get(
          "streaming", False
        ):
          logger.trace(
            f"Reasoning coordinator final response: {response}",
          )
          if response.content:
            final_workspace_content = str(
              response.content
            )

      # Show final workspace content in reasoning step
      if final_workspace_content:
        await reasoning_step.show_response(
          Response(
            content=final_workspace_content,
            metadata={
              "final_workspace": True,
              "workspace": self.workspace_path,
            },
          )
        )

    # After all steps complete, generate streaming final response
    if final_workspace_content:
      async for (
        response
      ) in self.generate_streaming_response(
        Message(
          content=final_workspace_content,
          metadata=message.metadata,
        )
      ):
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
    # Create and register memory coordinator
    memory_config = AgentConfig.from_yaml(
      self.paths.system_agents_config
      / "memory"
      / "coordinator.yaml"
    )
    system.register_agent(
      MemoryCoordinator(
        system=cast(AgentSystem, system),
        config=memory_config,
        paths=self.paths,
      )
    )

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
