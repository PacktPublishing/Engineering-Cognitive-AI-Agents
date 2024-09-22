# src/ch05/winston_converses.py
"""
Winston: A Knowledge-Driven Conversational AI Assistant
with Memory

This module implements Winston, an advanced AI
assistant with knowledge management and conversational
memory capabilities. Key features include:

1. Conversational Memory: Utilizes a
   ConversationalMemory system to maintain context
   across interactions, storing and retrieving
   conversation history.

2. Persistent Conversations: Each chat session is
   associated with a unique conversation ID, allowing
   for continuity between user interactions.

3. Message History Management: Stores and retrieves
   messages for each conversation, including system,
   user, and assistant messages.

4. Context-Aware Responses: Leverages conversation
   history to generate more contextually relevant and
   coherent responses.

5. Integration with Knowledge Management: Combines
   conversational memory with the existing Knowledge
   Management System (KMS) for more informed and
   contextually relevant responses.

6. Multi-Turn Interactions: Supports complex,
   multi-turn conversations by maintaining conversation
   state and history.

This implementation represents a significant
advancement in AI assistants, combining robust
knowledge management with sophisticated conversational
memory to create a more capable and context-aware
conversational agent.

Key Components:

- ConversationalMemory: Manages storage and retrieval
  of conversation history.

- KnowledgeManagementSystem: Handles storage,
  retrieval, and reasoning over information.

- Intent handlers: Specialized functions for different
  types of user intents, now utilizing conversation
  history.

Usage:
This module is designed to be run as a Chainlit
application, providing an interactive chat interface
for users to engage with Winston, maintaining
conversation context across multiple interactions.

Note: Ensure all required environment variables are set
and necessary prompt templates are available before
running the application.
"""

import ast
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

import chainlit as cl
from dotenv import load_dotenv
from litellm.types.utils import (
  ChatCompletionMessageToolCall,
  Function,
)
from loguru import logger

from ch03.intent_classifiers import classify_intent
from ch03.llm import (
  LLMParams,
  Message,
  call_llm,
  call_llm_streaming,
)
from ch03.prompt import Prompt, load_prompt
from ch04.kms import (
  Content,
  KnowledgeManagementSystem,
)
from ch05.conversational_memory import (
  ConversationalMemory,
  ConversationMessage,
)

#

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stdout, level="TRACE")

_ = load_dotenv()

USER_NAME = os.getenv("USER_NAME", "User")
DB_DIR = os.getenv("DB_DIR", "db")
QA_COLLECTION_NAME = os.getenv(
  "QA_COLLECTION_NAME", "qa_index"
)
MEMORY_DB_PATH = os.path.join(DB_DIR, "memory.db")

#

WINSTON_PROMPT = load_prompt("ch03/persona/winston")
GREETING_PROMPT = load_prompt("ch03/persona/greeting")
FUNCTION_CALL_RESPONSE_PROMPT = load_prompt(
  "ch03/internal/function_call_response"
)
WEATHER_INTENT_PROMPT = load_prompt(
  "ch03/intent/weather"
)
TASK_INTENT_PROMPT = load_prompt("ch03/intent/task")
GENERAL_INTENT_PROMPT = load_prompt(
  "ch03/intent/general"
)
MULTI_INTENT_SYNTHESIS_PROMPT = load_prompt(
  "ch03/internal/multi_intent_synthesis"
)
# New in Chapter 4
HELP_INTENT_PROMPT = load_prompt("ch04/intent/help")
REMEMBER_EXTRACT_PROMPT = load_prompt(
  "ch04/intent/remember_extract"
)
REMEMBER_CONFIRM_PROMPT = load_prompt(
  "ch04/intent/remember_confirm"
)
QUESTION_INTENT_PROMPT = load_prompt(
  "ch04/intent/question"
)
MULTI_INTENT_PROMPT = load_prompt(
  "ch04/intent/classifier/multi"
)

#

kms = KnowledgeManagementSystem(
  db_dir=DB_DIR,
  qa_collection_name=QA_COLLECTION_NAME,
)
cm = ConversationalMemory(
  kms=kms,
  db_path=MEMORY_DB_PATH,
)
#


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
    await call_tool(response.function)
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
  """Start the chat session by creating a new conversation and setting the initial history"""
  conversation_id = cm.create_conversation()
  cl.user_session.set(
    "conversation_id", conversation_id
  )

  current_time = datetime.now()
  time_of_day = (
    "morning"
    if 0 <= current_time.hour < 12
    else "afternoon"
    if 12 <= current_time.hour < 18
    else "evening"
  )

  system_message = cast(
    Message,
    {
      "role": "system",
      "content": WINSTON_PROMPT.template,
    },
  )
  await cm.add_message(
    conversation_id,
    cast(
      ConversationMessage,
      {
        "id": uuid4(),
        "conversation_id": conversation_id,
        **system_message,
      },
    ),
    bypass_ingestion=True,
  )

  greeting_message = cast(
    Message,
    {
      "role": "user",
      "content": GREETING_PROMPT.render(
        user_name=USER_NAME, time_of_day=time_of_day
      ),
    },
  )

  greeting_messages: list[Message] = [
    system_message,
    greeting_message,
  ]

  greeting_response = await call_llm_and_tool(
    messages=greeting_messages,
    params=GREETING_PROMPT.params,
  )
  assert isinstance(greeting_response, str)

  assistant_message = cast(
    ConversationMessage,
    {
      "id": uuid4(),
      "conversation_id": conversation_id,
      "role": "assistant",
      "content": greeting_response,
    },
  )
  await cm.add_message(
    conversation_id=conversation_id,
    message=assistant_message,
  )


@cl.on_message
async def handle_message(message: cl.Message) -> None:
  """
  Receive a message from the user, classify intent,
  and route to appropriate handler
  """
  conversation_id = cl.user_session.get(
    "conversation_id"
  )
  assert isinstance(conversation_id, UUID)

  # Add user message to conversational memory
  user_message = cast(
    ConversationMessage,
    {
      "id": uuid4(),
      "conversation_id": conversation_id,
      "role": "user",
      "content": message.content,
    },
  )
  cm.add_message_background(
    conversation_id=conversation_id,
    message=user_message,
  )

  # Retrieve conversation history
  history = [
    cast(
      Message,
      {
        "role": cm["role"],
        "content": cm["content"],
      },
    )
    for cm in cm.get_last_n_messages(
      conversation_id=conversation_id,
    )
  ]
  # Add the current user message to the history
  history.append(
    Message(
      role=user_message["role"],
      content=user_message["content"],
    )
  )

  # Classify user intent
  intents = await classify_intent(
    messages=history,
    prompt=MULTI_INTENT_PROMPT,
  )

  # Handle the user intent
  intent_handlers = {
    "weather": handle_weather_intent,
    "task": handle_task_intent,
    "help": handle_help_intent,
    "general": handle_general_intent,
    "remember": handle_remember_intent,
    "question": handle_question_intent,
  }

  all_responses: list[Message] = []
  for intent in intents:
    handler = intent_handlers.get(
      intent, handle_general_intent
    )
    intent_messages = await handler(
      messages=history,
      suppress_output=len(intents) > 1,
    )
    all_responses.extend(intent_messages)

  if len(all_responses) > 1:
    final_prompt = (
      MULTI_INTENT_SYNTHESIS_PROMPT.render(
        previous_responses="\n".join(
          [
            str(m["content"])
            for m in all_responses
            if m["role"] == "assistant"
          ]
        )
      )
    )
    final_message = cast(
      Message,
      {"role": "user", "content": final_prompt},
    )
    final_response = await call_llm_and_tool(
      messages=history + [final_message],
      params=MULTI_INTENT_SYNTHESIS_PROMPT.params,
    )
    assert isinstance(final_response, str)
  else:
    final_response = all_responses[0]["content"]

  final_assistant_message = cast(
    ConversationMessage,
    {
      "id": uuid4(),
      "conversation_id": conversation_id,
      "role": "assistant",
      "content": final_response,
    },
  )
  cm.add_message_background(
    conversation_id=conversation_id,
    message=final_assistant_message,
  )


async def handle_intent(
  messages: list[Message],
  prompt: Prompt,
  prompt_vars: dict[str, Any] | None = None,
  tools: list[dict[str, Any]] | None = None,
  suppress_output: bool = False,
) -> list[Message]:
  """Generalized handler for intents"""

  # If no custom prompt variables are provided, use
  # the user_message
  if prompt_vars is None:
    user_message = messages[-1]["content"]
    prompt_vars = {"user_message": user_message}

  # Render the prompt with the provided variables
  response_prompt = prompt.render(**prompt_vars)

  # Generate a new list of messages, dropping the last
  # (actual) user message since it's already been
  # incorporated into the prompt and add the prompt
  # into the list
  tmp_messages = messages[:-1] + [
    cast(
      Message,
      {
        "role": "user",
        "content": response_prompt,
      },
    )
  ]

  # Call the LLM and execute a tool if selected
  response = await call_llm_and_tool(
    messages=tmp_messages,
    params=prompt.params,
    tools=tools,
    suppress_output=suppress_output,
  )

  # If a tool call was executed, update the chat
  # history with a prose response
  if isinstance(response, dict):
    # Create some temporary messages to provide
    # context to the LLM
    tmp_messages = tmp_messages + [
      response,
      cast(
        Message,
        {
          "role": "user",
          "content": FUNCTION_CALL_RESPONSE_PROMPT.template,
        },
      ),
    ]
    response = await call_llm_and_tool(
      messages=messages[:-1] + tmp_messages,
      params=FUNCTION_CALL_RESPONSE_PROMPT.params,
      suppress_output=suppress_output,
    )

  return [
    cast(
      Message,
      {
        "role": "assistant",
        "content": str(response),
      },
    )
  ]


async def handle_weather_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the weather intent"""
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

  return await handle_intent(
    messages=messages,
    prompt=WEATHER_INTENT_PROMPT,
    tools=tools,
    suppress_output=suppress_output,
  )


async def handle_task_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the task intent"""
  return await handle_intent(
    messages,
    TASK_INTENT_PROMPT,
    suppress_output=suppress_output,
  )


async def handle_help_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the help intent"""
  return await handle_intent(
    messages,
    HELP_INTENT_PROMPT,
    suppress_output=suppress_output,
  )


async def handle_general_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the general intent"""
  return await handle_intent(
    messages,
    GENERAL_INTENT_PROMPT,
    suppress_output=suppress_output,
  )


async def handle_remember_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the remember intent"""
  user_message = messages[-1]["content"]

  # Extract the information to remember from the user message
  extraction_response = str(
    await REMEMBER_EXTRACT_PROMPT.call_llm(
      user_message=user_message
    )
  )
  assert isinstance(extraction_response, str)
  extracted_info = json.loads(extraction_response)
  content = Content(
    id=str(uuid4()),
    type="memory",
    content=extracted_info["content"],
    metadata=extracted_info.get("metadata", {}),
  )

  # Ingest the content into KMS
  report = await kms.ingest_content(content)
  report_text = json.dumps(asdict(report), indent=2)

  # Create a Chainlit Step to display the ingestion report
  async with cl.Step(
    name="Memory Ingestion Report", type="tool"
  ) as step:
    step.input = content.content
    step.output = report_text
    step.language = "json"

  return await handle_intent(
    messages,
    REMEMBER_CONFIRM_PROMPT,
    prompt_vars={"user_message": content.content},
    suppress_output=suppress_output,
  )


async def handle_question_intent(
  messages: list[Message],
  suppress_output: bool = False,
) -> list[Message]:
  """Handle the question intent"""
  user_message = messages[-1]["content"]

  # Retrieve relevant information from the KMS
  retrieved_content = await kms.retrieve_content(
    str(user_message)
  )

  # Prepare the context for the response
  context = str(retrieved_content)
  print(f"Retrieved context: {context}")

  # Calculate the confidence level
  confidence = sum(
    item.similarity for item in retrieved_content
  ) / len(retrieved_content)

  # Prepare the prompt variables
  prompt_vars = {
    "user_question": user_message,
    "retrieved_context": context,
    "confidence": confidence,
  }

  return await handle_intent(
    messages,
    QUESTION_INTENT_PROMPT,
    prompt_vars=prompt_vars,
    suppress_output=suppress_output,
  )
