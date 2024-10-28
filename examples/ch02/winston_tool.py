"""Winston chat implementation with tool support."""

from pathlib import Path

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.paths import AgentPaths
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
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    """Initialize tool-enabled Winston agent.

    Parameters
    ----------
    system : System
        The system instance.
    config : AgentConfig
        The agent configuration.
    paths : AgentPaths
        The agent paths configuration.
    """
    super().__init__(
      system=system, config=config, paths=paths
    )
    self.tools: dict[str, Tool[WeatherResponse]] = {}

    # Register weather tool
    system.register_tool(weather_tool)
    system.grant_tool_access(
      config.id, ["get_current_weather"]
    )


class ToolEnabledWinstonChat(AgentChat):
  """Winston chat interface with tool support."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    """Create tool-enabled Winston agent instance.

    Returns
    -------
    Agent
        The Winston agent instance with tool support.
    """
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston.yaml"
    )
    return ToolEnabledWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = ToolEnabledWinstonChat()
