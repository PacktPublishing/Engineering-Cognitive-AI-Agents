"""
This is a simple example of a ChainLit app that uses the LiteLLM to generate
responses to user messages. The app sends the user's message to the LiteLLM
model and sends the response back to the user.
"""

import chainlit as cl
from litellm import completion

#

MODEL = "gpt-4o-mini"
# MODEL = "ollama_chat/llama3"


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
  response = completion(
    model=MODEL,
    messages=[
      {
        "content": message.content,
        "role": "user",
      }
    ],
  )

  content = (
    response.choices[0].message.content
    or "<no response>"
  )
  await cl.Message(content=content).send()
