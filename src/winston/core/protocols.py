"""Core protocol definitions to avoid circular dependencies."""

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

from winston.core.messages import Message, Response

T = TypeVar("T", bound=BaseModel)


class Tool(Protocol, Generic[T]):
  """Protocol for tool implementations."""

  name: str
  description: str
  handler: Any  # Callable[[BaseModel], T]
  input_model: type[BaseModel]
  output_model: type[T]

  def to_openai_schema(self) -> dict[str, Any]: ...


class Agent(Protocol):
  """Core agent interface."""

  @property
  @abstractmethod
  def id(self) -> str:
    """Read-only agent identifier."""
    ...

  @abstractmethod
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
