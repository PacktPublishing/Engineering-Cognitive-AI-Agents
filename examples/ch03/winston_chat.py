# examples/ch03/custom.py
import json
from pathlib import Path

from winston.core.agent import AgentConfig
from winston.core.behavior import (
  Behavior,
  BehaviorType,
)
from winston.core.models import ModelType
from winston.ui.chainlit_app import AgentChat


class WinstonChat(AgentChat):
  def load_config(self) -> AgentConfig:
    """
    Load custom configuration.

    Returns
    -------
    AgentConfig
        Configuration for the Winston agent.
    """
    # Load custom configuration
    config_path = (
      Path(__file__).parent
      / "config"
      / "agents"
      / "winston.json"
    )
    with open(config_path) as f:
      config_data = json.load(f)

    # Ensure conversation behavior exists
    behaviors = config_data.get("behaviors", [])
    if not any(
      b.get("type") == BehaviorType.CONVERSATION
      for b in behaviors
    ):
      behaviors.append(
        {
          "type": BehaviorType.CONVERSATION,
          "model": "gpt-4o-mini",
          "temperature": 0.7,
          "stream": True,
        }
      )

    # Convert behaviors to Behavior objects
    behaviors = [
      Behavior(
        type=BehaviorType(
          behavior.get("type", "conversation")
        ),
        model=ModelType(
          behavior.get("model", "gpt-4o-mini")
        ),
        temperature=behavior.get("temperature", 0.7),
        stream=behavior.get("stream", True),
        tool_ids=None,
      )
      for behavior in behaviors
    ]

    # Create AgentConfig with properly instantiated Behavior objects
    return AgentConfig(
      id=config_data["id"],
      type=config_data["type"],
      capabilities=set(config_data["capabilities"]),
      behaviors=behaviors,
      prompts=config_data.get("prompts", {}),
    )


# Create the application with custom configuration
app = WinstonChat()
