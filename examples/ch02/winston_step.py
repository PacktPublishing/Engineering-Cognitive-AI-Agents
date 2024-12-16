# examples/ch02/winston_steps.py

from pathlib import Path
from typing import AsyncIterator

from litellm import acompletion

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.core.steps import ProcessingStep
from winston.ui.chainlit_app import AgentChat


class StepTestAgent(BaseAgent):
  """Minimal agent to test step functionality."""

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process with single step to test streaming."""
    async with ProcessingStep(
      name="Test Step", step_type="llm"
    ) as step:
      # Mirror the working example
      response = await acompletion(
        model=self.config.model,
        messages=[
          message.to_chat_completion_message()
        ],
        temperature=self.config.temperature,
        stream=True,
      )

      async for chunk in response:
        delta = chunk["choices"][0].delta
        if delta.content:
          await step.stream_token(delta.content)

      yield Response(
        content="Done!",
        metadata={"streaming": False},
      )


class StepTestChat(AgentChat):
  """Minimal chat interface for testing steps."""

  def __init__(self) -> None:
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston.yaml"
    )
    return StepTestAgent(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = StepTestChat()
