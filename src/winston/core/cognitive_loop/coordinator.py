from typing import AsyncIterator

from loguru import logger

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import (
  Message,
  Response,
)
from winston.core.paths import AgentPaths
from winston.core.steps import ProcessingStep
from winston.core.system import AgentSystem


class CognitiveLoopCoordinator(BaseAgent):
  """Coordinates cognitive processing cycles."""

  def __init__(
    self,
    system: AgentSystem,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    logger.info("CognitiveLoopCoordinator initialized")

    # # Initialize OODA specialists
    # self.observer = ObserverAgent(
    #   system, observer_config, paths
    # )
    # self.orientation = OrientationAgent(
    #   system, orientation_config, paths
    # )
    # self.decision = DecisionAgent(
    #   system, decision_config, paths
    # )
    # self.action = ActionAgent(
    #   system, action_config, paths
    # )

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    """Run one OODA cycle using message as input."""

    # # Observe: Process input and integrate with memory
    # observation = await self.observer.process(message)

    # # Orient: Update internal model based on observation
    # orientation = await self.orientation.process(
    #   Message(
    #     content=observation,
    #     metadata={"memory": self.memory},
    #   )
    # )

    # # Decide: Determine next action based on orientation
    # decision = await self.decision.process(
    #   Message(
    #     content=orientation,
    #     metadata={"memory": self.memory},
    #   )
    # )

    # # Act: Execute decision and yield responses
    # async for response in self.action.process(
    #   Message(
    #     content=decision,
    #     metadata={"memory": self.memory},
    #   )
    # ):
    #   yield response
    logger.info(
      f"Delegating to memory coordinator: {message.content}"
    )

    # Delegate to memory coordinator
    async with ProcessingStep(
      name="Memory Coordinator agent", step_type="run"
    ):
      async for (
        response
      ) in self.system.invoke_conversation(
        agent_id="memory_coordinator",
        content=message.content,
        context=message.metadata,
      ):
        if response.metadata.get("streaming"):
          yield response
          continue
        logger.trace(
          f"Memory coordinator response: {response}"
        )
        updated_workspace = response.content
        message.metadata["current_workspace"] = (
          updated_workspace
        )

    async for (
      response
    ) in self.generate_streaming_response(message):
      yield response
