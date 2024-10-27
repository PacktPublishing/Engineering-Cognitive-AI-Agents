"""Winston chat implementation with Chainlit."""

from pathlib import Path

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class Winston(BaseAgent):
  """Winston agent implementation."""

  def __init__(
    self, system: System, config: AgentConfig
  ) -> None:
    """Initialize Winston agent.

    Parameters
    ----------
    system : System
        The system instance.
    config : AgentConfig
        The agent configuration.
    """
    super().__init__(system=system, config=config)


class WinstonChat(AgentChat):
  """Winston chat interface implementation."""

  def create_agent(self, system: System) -> Agent:
    """Create Winston agent instance."""
    config_path = Path(
      "examples/ch03/config/agents/winston.json"
    )
    config = AgentConfig.model_validate_json(
      config_path.read_text()
    )

    return Winston(system=system, config=config)


# Create the application
app = WinstonChat()
