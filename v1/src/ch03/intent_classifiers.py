"""
User Intent Classifiers
"""

import json

from loguru import logger

#
from ch03.llm import Message
from ch03.prompt import Prompt

#


async def classify_intent(
  messages: list[Message],
  prompt: Prompt,
) -> list[str]:
  """
  Classify the user's intent(s) using prompt
  engineering techniques.
  """
  response = str(
    await prompt.call_llm(
      history=messages,
    )
  )
  if isinstance(prompt.params.response_format, dict):
    try:
      intent_obj = json.loads(response)
      return intent_obj.get("intents", [])
    except json.JSONDecodeError:
      logger.error(
        "Failed to parse JSON response from LLM"
      )
      return [
        "general"
      ]  # Fallback to general intent if parsing fails

  return [response.strip().lower()]
