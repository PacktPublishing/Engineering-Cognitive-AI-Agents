"""
LLM Interaction Module

This module provides functions for interacting with
Language Learning Models (LLMs) using the litellm
library. It includes functionality for making calls to
LLMs, processing responses, handling JSON-formatted
outputs, function-calling, history management, streaming,
and chaining multiple LLM calls.
"""

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Literal

from dotenv import load_dotenv
from litellm import completion
from litellm.types.utils import FunctionCall
from loguru import logger

#

_ = load_dotenv()

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
  """

  model: str = DEFAULT_MODEL
  temperature: float = DEFAULT_MODEL_TEMPERATURE
  max_tokens: int = DEFAULT_MODEL_MAX_TOKENS
  top_p: float = DEFAULT_MODEL_TOP_P
  frequency_penalty: float = (
    DEFAULT_MODEL_FREQUENCY_PENALTY
  )
  response_format_type: Literal[
    "text", "json_object"
  ] = "text"


#


async def call_llm(
  messages: list[dict[str, str]],
  params: LLMParams = LLMParams(),
  functions: list[dict[str, Any]] | None = None,
) -> str | FunctionCall:
  """
  Call the LLM with the given messages and parameters.

  Parameters
  ----------
  messages : list[dict[str, str]]
      The conversation history and current message(s).
  params : LLMParams, optional
      The parameters for the LLM call.
  functions : list[dict[str, Any]], optional
      The functions available for the model to call.

  Yields
  ------
  Union[str, FunctionCall]:
      Tokens or function call from the completion.
  """
  dbg_msg = json.dumps(messages, separators=(",", ":"))
  logger.trace(
    f"LLM call: {params.model}, messages: {dbg_msg}"
  )

  response = completion(
    model=params.model,
    messages=messages,
    temperature=params.temperature,
    max_tokens=params.max_tokens,
    top_p=params.top_p,
    frequency_penalty=params.frequency_penalty,
    response_format={
      "type": params.response_format_type
    },
    functions=functions,
  )

  message = response.choices[0].message
  result = message.content
  function_call = message.function_call
  logger.trace(
    f"LLM Response: {result}, function_call: {function_call}"
  )
  return function_call or str(result)


async def call_llm_streaming(
  messages: list[dict[str, str]],
  params: LLMParams = LLMParams(),
  functions: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
  """
  Call the LLM with streaming enabled.

  Parameters
  ----------
  messages : list[dict[str, str]]
      The conversation history and current message(s).
  params : LLMParams, optional
      The parameters for the LLM call.
  functions : list[dict[str, Any]], optional
      The functions available for the model to call.

  Yields
  ------
  dict[str, Any]
      Tokens or function calls from the streaming response.
  """
  dbg_msg = json.dumps(messages, separators=(",", ":"))
  logger.trace(
    f"LLM streaming call: {params.model}, messages: {dbg_msg}"
  )

  response = completion(
    model=params.model,
    messages=messages,
    temperature=params.temperature,
    max_tokens=params.max_tokens,
    top_p=params.top_p,
    frequency_penalty=params.frequency_penalty,
    response_format={
      "type": params.response_format_type
    },
    functions=functions,
    stream=True,
  )

  is_func_call = False
  func_call = {
    "name": "",
    "arguments": "",
  }

  for part in response:
    deltas = part["choices"][0]["delta"]

    if deltas.get("function_call") is not None:
      is_func_call = True
      fc: FunctionCall = deltas["function_call"]

      if fc.name:
        func_call["name"] = fc.name
      else:
        func_call["arguments"] += fc.arguments

    if (
      is_func_call
      and part["choices"][0].get("finish_reason")
      == "function_call"
    ):
      yield {
        "type": "function_call",
        "data": FunctionCall(**func_call),
      }
    elif "content" in deltas and not is_func_call:
      token = deltas["content"] or ""
      yield {"type": "token", "data": token}

    await asyncio.sleep(
      0
    )  # Allow other coroutines to run
