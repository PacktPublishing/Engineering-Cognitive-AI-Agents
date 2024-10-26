"""
LLM Interaction Module

This module provides functions for interacting with
Language Learning Models (LLMs) using the litellm
library. It includes functionality for making calls to
LLMs, processing responses, handling JSON-formatted
outputs, tool-calling, history management, streaming,
and chaining multiple LLM calls.
"""

import asyncio
import json
import os
from collections.abc import AsyncGenerator, Iterable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

from litellm import acompletion, completion
from litellm.exceptions import InternalServerError
from litellm.types.utils import (
  ChatCompletionDeltaToolCall,
  ChatCompletionMessageToolCall,
  Choices,
  Function,
  ModelResponse,
  StreamingChoices,
)
from litellm.utils import CustomStreamWrapper
from loguru import logger

#

DEFAULT_MODEL = os.getenv(
  "DEFAULT_MODEL", "gpt-4o-mini"
)
DEFAULT_MODEL_TEMPERATURE = float(
  os.getenv("DEFAULT_MODEL_TEMPERATURE", "0.7")
)
DEFAULT_MODEL_MAX_TOKENS = int(
  os.getenv("DEFAULT_MODEL_MAX_TOKENS", "2048")
)
DEFAULT_MODEL_TOP_P = float(
  os.getenv("DEFAULT_MODEL_TOP_P", "0.95")
)
DEFAULT_MODEL_FREQUENCY_PENALTY = float(
  os.getenv("DEFAULT_MODEL_FREQUENCY_PENALTY", "0")
)

#

RoleType = Literal["system", "assistant", "user"]


class Message(TypedDict):
  role: RoleType
  content: str | dict[str, Any] | list[dict[str, Any]]


@dataclass
class LLMParams:
  """
  Dataclass representing parameters for the language model.

  Attributes
  ----------
  model : str
      The name of the language model to use.
  temperature : float
      Controls randomness in the output.
  max_tokens : int
      Maximum number of tokens to generate.
  top_p : float
      Controls diversity via nucleus sampling.
  frequency_penalty : float
      Penalizes frequent token usage.
  response_format : dict[str, Any] | None
      The format of the response.
  extra_headers : dict[str, str]
      Additional headers to pass to the API.
  """

  model: str = DEFAULT_MODEL
  temperature: float = DEFAULT_MODEL_TEMPERATURE
  max_tokens: int = DEFAULT_MODEL_MAX_TOKENS
  top_p: float = DEFAULT_MODEL_TOP_P
  frequency_penalty: float = (
    DEFAULT_MODEL_FREQUENCY_PENALTY
  )
  response_format: dict[str, Any] | None = None
  extra_headers: dict[str, str] | None = None


def default_llm_params():
  return LLMParams()


async def call_llm(
  messages: Iterable[Message],
  params: LLMParams,
  tools: Iterable[dict[str, Any]] | None = None,
) -> str | ChatCompletionMessageToolCall:
  # Prepare the completion kwargs
  completion_kwargs: dict[str, Any] = {
    "model": params.model,
    "messages": messages,
    "temperature": params.temperature,
    "max_tokens": params.max_tokens,
    "top_p": params.top_p,
    "frequency_penalty": params.frequency_penalty,
    "response_format": params.response_format,
    "tools": tools,
    "extra_headers": params.extra_headers,
  }

  logger.trace(json.dumps(completion_kwargs, indent=2))

  max_retries = 3
  for attempt in range(max_retries):
    try:
      response = cast(
        ModelResponse,
        completion(**completion_kwargs),
      )
      choices_list = cast(
        list[Choices],
        response.choices,
      )
      choices = choices_list[0]
      message = choices.message
      result = message.content
      tool_calls = message.tool_calls
      logger.trace(
        f"LLM Response: {result}, tool_calls: {tool_calls}"
      )
      return (
        tool_calls[0] if tool_calls else str(result)
      )

    except InternalServerError as e:
      if (
        "Overloaded" in str(e)
        and attempt < max_retries - 1
      ):
        logger.warning(
          f"Attempt {attempt + 1} failed due to overload. Retrying..."
        )
        continue
      raise


async def call_llm_streaming(
  messages: Iterable[Message],
  params: LLMParams,
  tools: Iterable[dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
  dbg_msg = json.dumps(
    messages, separators=(",", ":"), indent=2
  )
  logger.debug(
    f"LLM streaming call: {params.model}, messages: {dbg_msg}"
  )

  completion_kwargs: dict[str, Any] = {
    "model": params.model,
    "messages": messages,
    "temperature": params.temperature,
    "max_tokens": params.max_tokens,
    "top_p": params.top_p,
    "frequency_penalty": params.frequency_penalty,
    "response_format": params.response_format,
    "tools": tools,
    "stream": True,
    "extra_headers": params.extra_headers,
  }

  tool_calls: list[ChatCompletionDeltaToolCall] = []

  response = cast(
    CustomStreamWrapper,
    await acompletion(**completion_kwargs),
  )
  async for chunk in response:
    choices_list = cast(
      list[StreamingChoices],
      chunk["choices"],
    )
    choices = choices_list[0]

    finish_reason = choices.finish_reason
    if finish_reason == "tool_calls":
      for tool_call in tool_calls:
        yield {
          "type": "tool_call",
          "data": ChatCompletionMessageToolCall(
            **tool_call.model_dump()
          ),
        }

    delta = choices.delta
    if delta.tool_calls:
      for tool_call in cast(
        list[ChatCompletionDeltaToolCall],
        delta["tool_calls"],
      ):
        if len(tool_calls) <= tool_call.index:
          assert len(tool_calls) == tool_call.index
          tool_calls.append(
            ChatCompletionDeltaToolCall(
              function=Function(
                arguments=None,
              ),
              index=tool_call.index,
            )
          )

        if tool_call.function.name:
          tool_calls[
            tool_call.index
          ].function.name = tool_call.function.name

        if tool_call.function.arguments:
          tool_calls[
            tool_call.index
          ].function.arguments += (
            tool_call.function.arguments
          )

    elif "content" in delta and delta["content"]:
      token = str(delta["content"])
      yield {"type": "token", "data": token}

    await asyncio.sleep(
      0
    )  # Allow other coroutines to run
