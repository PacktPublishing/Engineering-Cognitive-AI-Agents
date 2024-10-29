# src/winston/core/vision.py
import base64
from pathlib import Path

from litellm.types.completion import (
  ChatCompletionMessageParam,
)


def image_to_base64(image_path: str | Path) -> str:
  """Convert image file to base64 string.

  Parameters
  ----------
  image_path : str | Path
      Path to image file

  Returns
  -------
  str
      Base64 encoded image string
  """
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode(
      "utf-8"
    )


def create_vision_messages(
  prompt: str,
  image_path: str | Path,
) -> list[ChatCompletionMessageParam]:
  """Create messages for vision model.

  Parameters
  ----------
  prompt : str
      Text prompt for the vision model
  image_path : str | Path
      Path to image file

  Returns
  -------
  list[ChatCompletionMessageParam]
      Messages formatted for vision model
  """
  image_base64 = image_to_base64(image_path)

  return [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": prompt},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{image_base64}"
          },
        },
      ],
    }
  ]
