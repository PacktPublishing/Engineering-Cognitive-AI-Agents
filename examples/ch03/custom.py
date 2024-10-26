# examples/ch03/custom.py
import json
from pathlib import Path

from winston.core.agent import AgentConfig
from winston.core.behavior import Behavior
from winston.ui.chainlit_app import AgentChat


class CustomWinstonChat(AgentChat):
  def load_config(self) -> AgentConfig:
    # Load custom configuration
    config_path = (
      Path(__file__).parent
      / "config"
      / "agents"
      / "winston.json"
    )
    with open(config_path) as f:
      config_data = json.load(f)

    # Convert behaviors to Behavior objects
    behaviors = [
      Behavior(**behavior)
      for behavior in config_data.get("behaviors", [])
    ]

    # Create AgentConfig with properly instantiated Behavior objects
    return AgentConfig(
      id=config_data["id"],
      type=config_data["type"],
      capabilities=set(config_data["capabilities"]),
      behaviors=behaviors,
      prompts=config_data["prompts"],
    )


# Create the application with custom configuration
app = CustomWinstonChat()
