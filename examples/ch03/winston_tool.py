"""Winston chat implementation with tool support."""

from pathlib import Path

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.protocols import Agent, System
from winston.core.tools import Tool
from winston.tools.weather import (
  WeatherResponse,
  weather_tool,
)
from winston.ui.chainlit_app import AgentChat


class ToolEnabledWinston(BaseAgent):
  """Winston agent implementation with tool support."""

  def __init__(
    self, system: System, config: AgentConfig
  ) -> None:
    """Initialize tool-enabled Winston agent.

    Parameters
    ----------
    system : System
        The system instance.
    config : AgentConfig
        The agent configuration.
    """
    super().__init__(system=system, config=config)
    self.tools: dict[str, Tool[WeatherResponse]] = {}

    # Register weather tool
    system.register_tool(weather_tool)
    system.grant_tool_access(
      config.id, ["get_current_weather"]
    )


class ToolEnabledWinstonChat(AgentChat):
  """Winston chat interface with tool support."""

  def create_agent(self, system: System) -> Agent:
    """Create tool-enabled Winston agent instance.

    Returns
    -------
    Agent
        The Winston agent instance with tool support.
    """
    config_path = Path(
      "examples/ch03/config/agents/winston.json"
    )
    config = AgentConfig.model_validate_json(
      config_path.read_text()
    )

    return ToolEnabledWinston(
      system=system,
      config=config,
    )


# Create the application
app = ToolEnabledWinstonChat()
