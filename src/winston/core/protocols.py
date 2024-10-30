"""Core protocol definitions to avoid circular dependencies."""

from abc import abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from pathlib import Path
from typing import (
  Any,
  Generic,
  Protocol,
  TypeVar,
)

from pydantic import BaseModel

from winston.core.messages import Message, Response

T = TypeVar("T", bound=BaseModel)


class MessagePattern(StrEnum):
  """Valid message patterns."""

  CONVERSATION = "conversation"
  FUNCTION = "function"
  EVENT = "event"


class Tool(Protocol, Generic[T]):
  """Protocol for tool implementations."""

  name: str
  description: str
  handler: Any  # Callable[[BaseModel], T]
  input_model: type[BaseModel]
  output_model: type[T]

  def to_openai_schema(self) -> dict[str, Any]:
    """Convert tool to OpenAI function schema.

    Returns
    -------
    dict[str, Any]
        OpenAI-compatible function schema
    """
    ...


class Agent(Protocol):
  """Core agent interface."""

  @property
  @abstractmethod
  def id(self) -> str:
    """Read-only agent identifier."""
    ...

  @property
  @abstractmethod
  def workspace_path(self) -> Path:
    """Get path to this agent's workspace."""
    ...

  @classmethod
  @abstractmethod
  def can_handle(cls, message: Message) -> bool:
    """Check if this agent can handle the message."""
    ...

  @abstractmethod
  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process an incoming message and stream responses.

    Parameters
    ----------
    message : Message
        The message to process

    Returns
    -------
    AsyncIterator[Response]
        Stream of responses generated from the message
    """
    ...

  @abstractmethod
  async def generate_response(
    self,
    message: Message,
  ) -> Response:
    """Generate a single response from the agent.

    Unlike process(), this method returns a single response rather than
    streaming multiple responses.

    Parameters
    ----------
    message : Message
        The message to generate a response for

    Returns
    -------
    Response
        The generated response
    """
    ...

  @abstractmethod
  async def generate_vision_response(
    self,
    prompt: str,
    image_path: str | Path,
  ) -> Response:
    """Generate a single response from the vision model.

    Parameters
    ----------
    prompt : str
        Text prompt for the vision model
    image_path : str | Path
        Path to image file

    Returns
    -------
    Response
        The generated response from the vision model
    """
    ...

  @abstractmethod
  async def generate_streaming_vision_response(
    self,
    prompt: str,
    image_path: str | Path,
  ) -> AsyncIterator[Response]:
    """Generate a streaming response from the vision model.

    Parameters
    ----------
    prompt : str
        Text prompt for the vision model
    image_path : str | Path
        Path to image file

    Returns
    -------
    AsyncIterator[Response]
        Stream of responses from the vision model
    """
    ...


class System(Protocol):
  """Core system interface."""

  def register_agent(
    self,
    agent: Agent,
    subscribed_events: list[str] | None = None,
  ) -> None:
    """Register an agent with the system.

    Parameters
    ----------
    agent : Agent
        The agent to register
    subscribed_events : list[str] | None, optional
        List of event types the agent should subscribe to, by default None
    """
    ...

  def register_tool(
    self,
    tool: Tool[Any],
  ) -> None:
    """Register a tool with the system.

    Parameters
    ----------
    tool : Tool[Any]
        The tool to register
    """
    ...

  def grant_tool_access(
    self,
    agent_id: str,
    tool_names: list[str],
  ) -> None:
    """Grant an agent access to specific tools.

    Parameters
    ----------
    agent_id : str
        ID of the agent to grant access to
    tool_names : list[str]
        Names of tools to grant access to
    """
    ...

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
    """Invoke a function with the given arguments.

    Parameters
    ----------
    agent_id : str
        ID of the agent invoking the function
    function_name : str
        Name of the function to invoke
    args : dict[str, Any]
        Arguments to pass to the function

    Returns
    -------
    Response
        Response from the function invocation
    """
    ...

  async def invoke_conversation(
    self,
    agent_id: str,
    message: str,
    context: dict[str, Any] | None = None,
  ) -> AsyncIterator[Response]:
    """Invoke a conversation with an agent."""
    ...
