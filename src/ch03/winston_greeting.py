"""
ChainLit-based Conversational AI Assistant

This module implements an advanced conversational AI
assistant using ChainLit and custom LLM interaction
functions. Key enhancements and differences include:

1. Modularization: Utilizes separate modules for LLM
   interactions and prompt management.

2. Environment Variables: Uses environment variables
   for configuration, improving flexibility.

3. Personalization: Implements a context-aware greeting
   system based on time of day.

4. Improved Prompt Handling: Employs custom prompt
   templates for system and greeting messages.

5. Enhanced Function Calling: Implements a more robust
   system for function calls and tool usage.

6. Asynchronous Design: Fully embraces asynchronous
   programming for better performance.

7. Type Hinting: Incorporates extensive type hinting
   for improved code clarity and maintainability.

8. Logging: Integrates logging for better debugging and
   monitoring.

9. Streaming Responses: Implements streaming responses
   from the LLM to the user interface.

10. Error Handling: Includes more comprehensive error
    checking and handling.

The assistant, Winston, provides a seamless,
interactive chat experience with context-aware
greetings and responses. It leverages custom LLM
modules for language model interactions and uses prompt
templates for consistent messaging.

This version represents a significant evolution from
the earlier, simpler implementation, offering more
features, better structure, and improved
maintainability.
"""

import ast
import json
import os
from datetime import datetime
from typing import Any, cast

import chainlit as cl
from dotenv import load_dotenv
from litellm.types.utils import (
  ChatCompletionMessageToolCall,
  Function,
)

from ch03.llm import (
  LLMParams,
  Message,
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
    "type": "function",  # Add this line
    "function": {  # Wrap the existing content in a 'function' key
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
            "enum": ["celsius", "fahrenheit"],
          },
        },
        "required": ["location"],
      },
    },
  }
]


async def call_llm_and_tool(
  messages: list[Message],
  params: LLMParams | None = None,
  tools: list[dict[str, Any]] | None = None,
  suppress_output: bool = False,
) -> str | Message:
  """
  Call the LLM, optionally update the chat UI with streaming,
  execute a tool if selected, and return the response.

  Parameters
  ----------
  messages : list[Message]
      The conversation history.
  params : LLMParams | None, optional
      The LLM parameters, by default None
  tools : list[dict[str, Any]] | None, optional
      The tools to call, by default None
  suppress_output : bool, optional
      Whether to suppress streaming output, by default False

  Returns
  -------
  Union[str, Message]:
      Either the LLM response or the tool response
  """
  if params is None:
    params = LLMParams()

  if not suppress_output:
    response_generator = call_llm_streaming(
      messages=messages,
      params=params,
      tools=tools,
    )

    ui_msg = None
    function_msg: Message | None = None
    async for chunk in response_generator:
      if chunk["type"] == "token":
        if not ui_msg:
          ui_msg = cl.Message(content="")
          _ = await ui_msg.send()
        await ui_msg.stream_token(chunk["data"])
      elif chunk["type"] == "tool_call" and tools:
        tool_call = cast(
          ChatCompletionMessageToolCall,
          chunk["data"],
        )
        function_msg = await call_tool(
          tool_call.function
        )

    if not function_msg and ui_msg:
      await ui_msg.update()
    return function_msg or (
      ui_msg.content if ui_msg else ""
    )

  response = await call_llm(
    messages=messages,
    params=params,
    tools=tools,
  )

  function_result = (
    await call_tool(response)
    if isinstance(
      response, ChatCompletionMessageToolCall
    )
    else None
  )
  return function_result or str(response)


@cl.step(type="tool")
async def call_tool(
  function: Function,
) -> Message:
  """
  Call the tool function and update the message history with the function

  Parameters
  ----------
  tool_call : FunctionCall
      The function call to make

  Returns
  -------
  Message
      The function message
  """
  function_name = function.name
  if not function_name:
    raise ValueError("Function name is required")

  arguments = ast.literal_eval(function.arguments)

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

  return cast(
    Message,
    {
      "role": "function",
      "name": function_name,
      "content": function_response,
    },
  )


@cl.on_chat_start
async def start_chat() -> None:
  """
  Start the chat session by setting the initial
  history
  """
  history = [
    cast(
      Message,
      {
        "role": "system",
        "content": WINSTON_PROMPT.template,
      },
    )
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
    cast(
      Message,
      {
        "role": "user",
        "content": GREETING_PROMPT.render(
          user_name=USER_NAME,
          time_of_day=time_of_day,
        ),
      },
    )
  )

  greeting_response = await call_llm_and_tool(
    messages=greeting_messsages,
    params=GREETING_PROMPT.params,
  )
  assert isinstance(greeting_response, str)
  history.append(
    cast(
      Message,
      {
        "role": "assistant",
        "content": greeting_response,
      },
    )
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
  history: list[Message] = cl.user_session.get(
    "history"
  )  # type: ignore
  assert isinstance(history, list)
  history.append(
    cast(
      Message,
      {
        "role": "user",
        "content": message.content,
      },
    )
  )

  # Call the LLM and execute a tool if selected
  response = await call_llm_and_tool(
    messages=history,
    tools=tools,
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
    cast(
      Message,
      {
        "role": "assistant",
        "content": str(response),
      },
    )
  )
