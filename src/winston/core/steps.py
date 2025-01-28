"""Step management utilities for Winston's processing pipeline."""

import json
from contextvars import ContextVar, Token
from typing import Any, Literal

from loguru import logger

# Try importing chainlit, but don't fail if not available
try:
  import chainlit as cl
  from chainlit.context import get_context

  _chainlit_get_context = get_context  # Keep reference to avoid unbound issues
except ImportError:
  cl = None  # type: ignore
  _chainlit_get_context = None  # type: ignore

from winston.core.messages import (
  Response,
)

StepType = Literal[
  "run",
  "tool",
  "llm",
  "embedding",
  "retrieval",
  "rerank",
]

current_step: ContextVar["ProcessingStep | None"] = (
  ContextVar(
    "current_step",
    default=None,
  )
)


class ProcessingStep:
  """Context manager for handling processing steps."""

  def __init__(
    self,
    name: str,
    step_type: StepType,
    show_input: bool = True,
  ) -> None:
    """
    Initialize a processing step.

    Parameters
    ----------
    name : str
        Name of the step
    step_type : StepType
        Type of the step (must be one of Chainlit's supported types)
    show_input : bool
        Whether to show input in UI
    """
    self.name = name
    self.step_type = step_type
    self.show_input = show_input
    self.cl_step: Any = None  # type: Any to handle both Chainlit Step and None
    self.token: Token[Any] | None = None
    logger.debug(f"Starting {step_type} step: {name}")

  async def __aenter__(self) -> "ProcessingStep":
    """
    Enter the context manager.

    Returns
    -------
    ProcessingStep
        The processing step instance
    """
    # Try to get Chainlit context - if this fails, we're not in a Chainlit app
    try:
      if (
        cl is not None
        and _chainlit_get_context is not None
      ):
        _chainlit_get_context()  # This will raise if no context
        self.cl_step = cl.Step(
          name=self.name,
          type=self.step_type,  # type: ignore # Chainlit's type system is different
          show_input=self.show_input,
        )
        await self.cl_step.__aenter__()
    except Exception:
      # Not in Chainlit context or other error, just continue without Chainlit
      pass

    self.token = current_step.set(self)
    return self

  async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: Any | None,
  ) -> None:
    """Exit the context manager."""
    if self.cl_step:
      await self.cl_step.__aexit__(
        exc_type,
        exc_val,
        exc_tb,
      )

    if self.token:
      current_step.reset(self.token)

    logger.debug(
      f"Completed {self.step_type} step: {self.name}"
    )

  async def show_response(
    self, response: Response
  ) -> None:
    """
    Stream response based on its type.

    Parameters
    ----------
    response : Response
        Response to stream
    """
    if self.cl_step:
      if response.metadata:
        self.cl_step.input = (
          "```json\n"
          + json.dumps(
            response.metadata, indent=2, default=str
          )
          + "\n```"
        ).strip()
      if response.streaming and response.content:
        await self.cl_step.stream_token(
          response.content
        )
      elif response.content:
        self.cl_step.output = response.content
    else:
      # Log the response when Chainlit isn't available
      if response.metadata:
        logger.debug(
          f"Step {self.name} metadata:\n{json.dumps(response.metadata, indent=2, default=str)}"
        )
      if response.content:
        if response.streaming:
          logger.debug(
            f"Step {self.name} streaming: {response.content}"
          )
        else:
          logger.debug(
            f"Step {self.name} output: {response.content}"
          )
