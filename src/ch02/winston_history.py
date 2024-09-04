"""
This is a simple example of a ChainLit app that uses the LiteLLM to generate
responses to user messages. The app sends the user's message to the LiteLLM
model and sends the response back to the user.
"""

from textwrap import dedent

import chainlit as cl
from litellm import completion

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
  )

  for part in response:
    if token := part.choices[0].delta.content or "":
      await msg.stream_token(token)

  history.append(
    {"role": "assistant", "content": msg.content}
  )
  await msg.update()
