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

  msg = cl.Message(content="")
  await msg.send()

  response = completion(
    model=MODEL,
    messages=[
      {
        "content": message.content,
        "role": "user",
      }
    ],
    stream=True,
  )

  for part in response:
    if token := part.choices[0].delta.content or "":
      await msg.stream_token(token)

  await msg.update()
