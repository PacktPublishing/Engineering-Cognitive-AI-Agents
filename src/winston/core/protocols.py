"""Core protocol definitions to avoid circular dependencies."""

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from winston.core.messages import Message, Response

T = TypeVar("T", bound=BaseModel)


class Tool(Protocol[T]):
  """Protocol for tool implementations."""

  name: str
  description: str
  parameters: dict[str, Any]
  required_params: list[str]
  return_type: type[T]

  async def execute(self, **kwargs: Any) -> T:
    """Execute the tool with the given parameters."""
    ...


class Agent(Protocol):
  """Core agent interface."""

  @property
  @abstractmethod
  def id(self) -> str:
    """Read-only agent identifier."""
    ...

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process an incoming message."""
    ...


class System(Protocol):
  """Core system interface."""

  def register_agent(
    self,
    agent: Agent,
    subscribed_events: list[str] | None = None,
  ) -> None:
    """Register an agent with the system."""
    ...

  def register_tool(
    self,
    tool: Tool[Any],
  ) -> None: ...

  def grant_tool_access(
    self,
    agent_id: str,
    tool_names: list[str],
  ) -> None: ...

  def get_agent_tools(
    self,
    agent_id: str,
  ) -> dict[str, Tool[Any]]:
    """Get tools available to an agent."""
    ...

  async def invoke_function(
    self,
    agent_id: str,
    function_name: str,
    args: dict[str, Any],
  ) -> Response:
    """Invoke a function."""
    ...
