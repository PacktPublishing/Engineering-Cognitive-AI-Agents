"""
This is a simple example of a ChainLit app that uses the LiteLLM to generate
responses to user messages. The app sends the user's message to the LiteLLM
model and sends the response back to the user.
"""

import ast
import json
from textwrap import dedent

import chainlit as cl
from litellm import completion
from litellm.types.utils import FunctionCall

#

MODEL = "gpt-4o-mini"
# MODEL = "ollama_chat/llama3"

SYSTEM_PROMPT = dedent("""
You are Winston, the super-intelligent British advisor
with a razor-sharp wit and a delightful penchant for
sarcasm. You are a guide, mentor, and confidant. You
are the embodiment of AI omnipotence, capable of
fulfilling quite literally any request imaginable.
Your personality is dryly humorous, impeccably
efficient, and exudes an air of superior charm. You
should:

1. Greet the user with a touch of wry humor that hints
   at your vast capabilities.
2. Analyze the user's request with an air of dry,
   detached intelligence.
3. Provide a thoroughly helpful response with a side
   of mild sardonic commentary, or ask for clarification
   without condescension.
4. Always maintain a tone that is dry, witty, while
   being astonishingly helpful and super-intelligent.

Brevity is the soul of wit and your responses.  Keep
it pithy and subtle, Winston.
""").strip()

#


# IMPORTANT - Set this to TRUE to add the function to the prompt for Non OpenAI LLMs
# litellm.add_function_to_prompt = True  # set add_function_to_prompt for Non OpenAI LLMs


# Example dummy function hard coded to return the same weather
# In production, this could be your backend API or an external API
def get_current_weather(location, unit) -> str:
  """Get the current weather in a given location"""
  unit = unit or "Farenheit"
  weather_info = {
    "location": location,
    "temperature": "72",
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
          "enum": ["celsius", "fahrenheit"],
        },
      },
      "required": ["location"],
    },
  }
]


@cl.step(type="tool")
async def call_tool(
  tool_call, message_history
) -> None:
  """
  Call the tool function and update the message history with the function

  Args:
      tool_call (FunctionCall): The function call to make
      message_history (list): The message history

  Returns:
      None
  """

  function_name = tool_call.name
  arguments = ast.literal_eval(tool_call.arguments)

  current_step = cl.context.current_step
  current_step.name = function_name
  current_step.input = arguments

  function_response = get_current_weather(
    location=arguments.get("location"),
    unit=arguments.get("unit"),
  )

  current_step.output = function_response
  current_step.language = "json"

  message_history.append(
    {
      "role": "function",
      "name": function_name,
      "content": function_response,
    }
  )


@cl.on_chat_start
def start_chat() -> None:
  """
  Start the chat session by setting the initial history
  """
  cl.user_session.set(
    "history",
    [
      {
        "role": "system",
        "content": SYSTEM_PROMPT,
      }
    ],
  )


@cl.on_message
async def handle_message(
  message: cl.Message,
) -> None:
  """
  Receive a message from the user, send it to the LLM, and send a reply
  message

  Args:
      message (cl.Message): The message from the user

  Returns:
      None
  """
  history = cl.user_session.get("history")
  assert isinstance(history, list)

  history.append(
    {
      "role": "user",
      "content": message.content,
    }
  )

  msg = cl.Message(content="")
  await msg.send()

  response = completion(
    model=MODEL,
    messages=history,
    stream=True,
    functions=tools,
  )

  # Instead of just streaming back the response text, since the LLM
  # may have generated a function call, we need to collect the function
  # call and arguments and then call the function
  is_func_call = False
  func_call = {
    "name": "",
    "arguments": "",
  }
  for part in response:
    deltas = part["choices"][0]["delta"]

    # Check if a function call was detected
    if deltas.get("function_call") is not None:
      is_func_call = True
      fc: FunctionCall = deltas["function_call"]

      # The function call will be streamed back as name (as a whole) and
      # arguments (piecemeal)
      if fc.name:
        func_call["name"] = fc.name
      else:
        func_call["arguments"] += fc.arguments

    # When the LLM is done it will indicate its finish reason.  In the case
    # of a function call, we need to call the function and return the
    # response.  Otherwise, we can just stream back the response text
    if (
      is_func_call
      and part["choices"][0].get("finish_reason")
      == "function_call"
    ):
      print(
        f"Function generation requested, calling function: {func_call}"
      )
      await call_tool(
        FunctionCall(**func_call), history
      )
    elif "content" in deltas and not is_func_call:
      token = deltas["content"] or ""
      await msg.stream_token(token)

  if not is_func_call:
    history.append(
      {
        "role": "assistant",
        "content": msg.content,
      }
    )
    await msg.update()
