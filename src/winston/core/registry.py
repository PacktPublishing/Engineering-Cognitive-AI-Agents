# src/winston/core/registry.py
from winston.core.agent import Agent


class AgentRegistry:
  """
  Central registry for agent discovery and management.

  This class provides functionality to register agents, retrieve agents by ID,
  and find agents based on their capabilities.

  Attributes:
      agents: A dictionary mapping agent IDs to Agent instances.
      capability_index: A dictionary mapping capabilities to sets of agent IDs.
  """

  def __init__(self) -> None:
    self.agents: dict[str, Agent] = {}
    self.capability_index: dict[str, set[str]] = {}

  async def register(self, agent: Agent) -> None:
    """
    Register an agent in the registry.

    This method adds the agent to the main registry and updates the capability index.

    Parameters
    ----------
    agent : Agent
        The agent to be registered.

    Returns
    -------
    None
    """
    self.agents[agent.id] = agent
    for capability in agent.capabilities:
      if capability not in self.capability_index:
        self.capability_index[capability] = set()
      self.capability_index[capability].add(agent.id)

  async def get_agent(
    self, agent_id: str
  ) -> Agent | None:
    """
    Retrieve an agent by its ID.

    Parameters
    ----------
    agent_id : str
        The ID of the agent to retrieve.

    Returns
    -------
    Agent | None
        The agent with the specified ID, or None if not found.
    """
    return self.agents.get(agent_id)

  async def find_agents_by_capability(
    self, capability: str
  ) -> list[Agent]:
    """
    Find agents that have a specific capability.

    Parameters
    ----------
    capability : str
        The capability to search for.

    Returns
    -------
    list[Agent]
        A list of agents that have the specified capability.
    """
    agent_ids = self.capability_index.get(
      capability, set()
    )
    return [self.agents[aid] for aid in agent_ids]
