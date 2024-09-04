# winston_advanced.py
"""
ChainLit-based Conversational AI Assistant with Intent Routing

This module extends the basic Winston assistant with intent classification
and routing capabilities. It features:
- Initialization of chat sessions with a personalized greeting
- Streaming responses from the LLM to the user interface
- Maintenance of conversation history
- Integration with custom prompts for system and greeting messages
- Asynchronous handling of user messages and LLM responses
- Intent classification and routing to specialized handlers
- Function calling for weather-related queries

Winston uses environment variables for configuration and provides a
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

from ch03.intent_classifiers import classify_intent
from ch03.llm import (
  LLMParams,
  call_llm,
  call_llm_streaming,
)
from ch03.prompt import Prompt, load_prompt

#

_ = load_dotenv()

WINSTON_PROMPT = load_prompt("ch03/persona/winston")
GREETING_PROMPT = load_prompt("ch03/persona/greeting")
FUNCTION_CALL_RESPONSE_PROMPT = load_prompt(
  "ch03/internal/function_call_response"
)
WEATHER_INTENT_PROMPT = load_prompt(
  "ch03/intent/weather"
)
TASK_INTENT_PROMPT = load_prompt("ch03/intent/task")
HELP_INTENT_PROMPT = load_prompt("ch03/intent/help")
GENERAL_INTENT_PROMPT = load_prompt(
  "ch03/intent/general"
)
MULTI_INTENT_SYNTHESIS_PROMPT = load_prompt(
  "ch03/internal/multi_intent_synthesis"
)

USER_NAME = os.getenv("USER_NAME", "User")
BASIC_INTENT_PROMPT = load_prompt(
  "ch03/intent/classifier/basic"
)
COT_INTENT_PROMPT = load_prompt(
  "ch03/intent/classifier/cot"
)
FEW_SHOT_INTENT_PROMPT = load_prompt(
  "ch03/intent/classifier/few_shot"
)
MULTI_INTENT_PROMPT = load_prompt(
  "ch03/intent/classifier/multi"
)


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
      _ = await ui_msg.update()
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

  greeting_messages = history.copy()
  greeting_messages.append(
    {
      "role": "user",
      "content": GREETING_PROMPT.render(
        user_name=USER_NAME,
        time_of_day=time_of_day,
      ),
    }
  )

  greeting_response = await call_llm_and_tool(
    messages=greeting_messages,
    params=GREETING_PROMPT.params,
  )
  history.append(
    {
      "role": "assistant",
      "content": str(greeting_response),
    }
  )
  cl.user_session.set("history", history)


@cl.on_message
async def handle_message(message: cl.Message) -> None:
  """
  Receive a message from the user, classify intent,
  and route to appropriate handler
  """
  history: list[dict[str, str]] = cl.user_session.get(
    "history"
  )  # type: ignore
  assert isinstance(history, list)
  history.append(
    {"role": "user", "content": message.content}
  )

  intents = await classify_intent(
    messages=history,
    prompt=MULTI_INTENT_PROMPT,
  )

  intent_handlers = {
    "weather": handle_weather_intent,
    "task": handle_task_intent,
    "help": handle_help_intent,
    "general": handle_general_intent,
  }

  all_responses = []
  for intent in intents:
    handler = intent_handlers.get(
      intent, handle_general_intent
    )
    intent_messages = await handler(
      history,
      suppress_output=True,
    )
    all_responses.extend(intent_messages)

  if len(intents) > 1:
    final_prompt = (
      MULTI_INTENT_SYNTHESIS_PROMPT.render(
        previous_responses="\n".join(
          [
            m["content"]
            for m in all_responses
            if m["role"] == "assistant"
          ]
        )
      )
    )
    final_messages = history + [
      {
        "role": "user",
        "content": final_prompt,
      }
    ]

    final_response = await call_llm_and_tool(
      messages=final_messages,
      params=MULTI_INTENT_SYNTHESIS_PROMPT.params,
    )
    history.append(
      {
        "role": "assistant",
        "content": str(final_response),
      }
    )
  else:
    history.extend(all_responses)


async def handle_intent(
  messages: list[dict[str, str]],
  prompt: Prompt,
  prompt_vars: dict[str, Any] | None = None,
  functions: list[dict[str, Any]] | None = None,
  suppress_output: bool = False,
) -> list[dict[str, str]]:
  """Generalized handler for intents"""
  user_message = messages[-1]["content"]

  # If no custom prompt variables are provided, use
  # the user_message
  if prompt_vars is None:
    prompt_vars = {"user_message": user_message}

  # Render the prompt with the provided variables
  response_prompt = prompt.render(**prompt_vars)
  new_messages = [
    {"role": "user", "content": response_prompt}
  ]

  # Call the LLM and execute a tool if selected
  response = await call_llm_and_tool(
    messages=messages[:-1] + new_messages,
    params=prompt.params,
    functions=functions,
    suppress_output=suppress_output,
  )

  # If a tool call was executed, update the chat
  # history with a prose response
  if isinstance(response, dict):
    # Create some temporary messages to provide
    # context to the LLM
    tmp_messages = new_messages + [
      response,
      {
        "role": "user",
        "content": FUNCTION_CALL_RESPONSE_PROMPT.template,
      },
    ]
    response = await call_llm_and_tool(
      messages=messages[:-1] + tmp_messages,
      params=FUNCTION_CALL_RESPONSE_PROMPT.params,
      suppress_output=suppress_output,
    )

  new_messages.append(
    {
      "role": "assistant",
      "content": str(response),
    }
  )
  return new_messages


async def handle_weather_intent(
  messages: list[dict[str, str]],
  suppress_output: bool = False,
) -> list[dict[str, str]]:
  """Handle the weather intent"""
  functions = [
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

  return await handle_intent(
    messages=messages,
    prompt=WEATHER_INTENT_PROMPT,
    functions=functions,
    suppress_output=suppress_output,
  )


async def handle_task_intent(
  messages: list[dict[str, str]],
  suppress_output: bool = False,
) -> list[dict[str, str]]:
  """Handle the task intent"""
  return await handle_intent(
    messages,
    TASK_INTENT_PROMPT,
    suppress_output=suppress_output,
  )


async def handle_help_intent(
  messages: list[dict[str, str]],
  suppress_output: bool = False,
) -> list[dict[str, str]]:
  """Handle the help intent"""
  return await handle_intent(
    messages,
    HELP_INTENT_PROMPT,
    suppress_output=suppress_output,
  )


async def handle_general_intent(
  messages: list[dict[str, str]],
  suppress_output: bool = False,
) -> list[dict[str, str]]:
  """Handle the general intent"""
  return await handle_intent(
    messages,
    GENERAL_INTENT_PROMPT,
    suppress_output=suppress_output,
  )
