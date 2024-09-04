"""
ChainLit-based Conversational AI Assistant

This module implements a conversational AI assistant using ChainLit and
custom LLM interaction functions. It features:
- Initialization of chat sessions with a personalized greeting
- Streaming responses from the LLM to the user interface
- Maintenance of conversation history
- Integration with custom prompts for system and greeting messages
- Asynchronous handling of user messages and LLM responses

Winston, uses environment variables for configuration and provides a
seamless, interactive chat experience with context-aware greetings and
responses. It utilizes a custom LLM module for language model
interactions and prompt templates for consistent messaging.
"""

import ast
import json
import os
from datetime import datetime
from typing import Any

import chainlit as cl
from dotenv import load_dotenv
from litellm.types.utils import FunctionCall

from ch03.llm import (
  LLMParams,
  call_llm,
  call_llm_streaming,
)
from ch03.prompt import load_prompt

#

_ = load_dotenv()

WINSTON_PROMPT = load_prompt("ch03/persona/winston")
GREETING_PROMPT = load_prompt("ch03/persona/greeting")
FUNCTION_CALL_RESPONSE_PROMPT = load_prompt(
  "ch03/internal/function_call_response"
)

USER_NAME = os.getenv("USER_NAME", "User")


# Example dummy function for weather
def get_current_weather(
  location: str,
  unit: str = "fahrenheit",
) -> str:
  """Get the current weather in a given location"""
  weather_info = {
    "location": location,
    "temperature": "72"
    if unit.lower() == "fahrenheit"
    else "22",
    "unit": unit,
    "forecast": ["sunny", "windy"],
  }
  return json.dumps(weather_info)


tools = [
  {
    "name": "get_current_weather",
    "description": "Get the current weather in a given location",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "The city and state, e.g. San Francisco, CA",
        },
        "unit": {
          "type": "string",
          "enum": [
            "celsius",
            "fahrenheit",
          ],
        },
      },
      "required": ["location"],
    },
  }
]


async def call_llm_and_tool(
  messages: list[dict[str, str]],
  params: LLMParams | None = None,
  functions: list[dict[str, Any]] | None = None,
  suppress_output: bool = False,
) -> str | dict[str, str]:
  """
  Call the LLM, optionally update the chat UI with streaming,
  execute a tool if selected, and return the response.

  Parameters
  ----------
  messages : list[dict[str, str]]
      The conversation history.
  params : LLMParams | None, optional
      The LLM parameters, by default None
  functions : list[dict[str, Any]] | None, optional
      The functions to call, by default None
  suppress_output : bool, optional
      Whether to suppress streaming output, by default False

  Returns
  -------
  Union[str, dict[str, str]]:
      Either the LLM response or the tool response
  """
  if params is None:
    params = LLMParams()

  if not suppress_output:
    response_generator = call_llm_streaming(
      messages=messages,
      params=params,
      functions=functions,
    )

    ui_msg = None
    function_msg: dict[str, str] | None = None
    async for chunk in response_generator:
      if chunk["type"] == "token":
        if not ui_msg:
          ui_msg = cl.Message(content="")
          _ = await ui_msg.send()
        await ui_msg.stream_token(chunk["data"])
      elif (
        chunk["type"] == "function_call" and functions
      ):
        tool_call = chunk["data"]
        function_msg = await call_tool(tool_call)

    if not function_msg and ui_msg:
      await ui_msg.update()
    return function_msg or (
      ui_msg.content if ui_msg else ""
    )

  response = await call_llm(
    messages=messages,
    params=params,
    functions=functions,
  )

  function_result = (
    await call_tool(response)
    if isinstance(response, FunctionCall)
    else None
  )
  return function_result or str(response)


@cl.step(type="tool")
async def call_tool(
  tool_call: FunctionCall,
) -> dict[str, str]:
  """
  Call the tool function and update the message history with the function

  Parameters
  ----------
  tool_call : FunctionCall
      The function call to make

  Returns
  -------
  dict[str, str]
      The function message
  """
  function_name = tool_call.name
  if not function_name:
    raise ValueError("Function name is required")

  arguments = ast.literal_eval(tool_call.arguments)

  current_step = cl.context.current_step
  if not current_step:
    raise ValueError("Current step is required")

  current_step.name = function_name
  current_step.input = arguments

  function_response = get_current_weather(
    location=arguments.get("location"),
    unit=arguments.get("unit", "fahrenheit"),
  )

  current_step.output = function_response
  current_step.language = "json"

  return {
    "role": "function",
    "name": function_name,
    "content": function_response,
  }


@cl.on_chat_start
async def start_chat() -> None:
  """
  Start the chat session by setting the initial
  history
  """
  history = [
    {
      "role": "system",
      "content": WINSTON_PROMPT.template,
    }
  ]
  cl.user_session.set("history", history)

  current_time = datetime.now()
  time_of_day = (
    "morning"
    if 0 <= current_time.hour < 12
    else "afternoon"
    if 12 <= current_time.hour < 18
    else "evening"
  )

  greeting_messsages = history.copy()
  greeting_messsages.append(
    {
      "role": "user",
      "content": GREETING_PROMPT.render(
        user_name=USER_NAME,
        time_of_day=time_of_day,
      ),
    }
  )

  greeting_response = await call_llm_and_tool(
    messages=greeting_messsages,
    params=GREETING_PROMPT.params,
  )
  assert isinstance(greeting_response, str)
  history.append(
    {
      "role": "assistant",
      "content": greeting_response,
    }
  )
  cl.user_session.set("history", history)


@cl.on_message
async def handle_message(message: cl.Message) -> None:
  """
  Receive a message from the user, send it to the
  LLM, and send a reply message

  Parameters
  ----------
  message : cl.Message
      The message from the user

  Returns
  -------
  None
  """
  history: list[dict[str, str]] = cl.user_session.get(
    "history"
  )  # type: ignore
  assert isinstance(history, list)
  history.append(
    {"role": "user", "content": message.content}
  )

  # Call the LLM and execute a tool if selected
  response = await call_llm_and_tool(
    messages=history,
    functions=tools,
  )

  # If a tool call was executed, update the chat
  # history with a prose response
  if isinstance(response, dict):
    messages = history + [
      response,
      {
        "role": "user",
        "content": FUNCTION_CALL_RESPONSE_PROMPT.template,
      },
    ]
    response = await call_llm_and_tool(
      messages=messages,
      params=FUNCTION_CALL_RESPONSE_PROMPT.params,
    )

  history.append(
    {
      "role": "assistant",
      "content": str(response),
    }
  )
