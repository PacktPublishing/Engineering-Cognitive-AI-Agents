"""Winston chat implementation with Chainlit."""

from pathlib import Path

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class Winston(BaseAgent):
  """Winston agent implementation."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    """Initialize Winston agent.

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


class WinstonChat(AgentChat):
  """Winston chat interface implementation."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    """Create Winston agent instance."""
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston.yaml"
    )
    return Winston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = WinstonChat()
