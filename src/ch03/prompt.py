import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv
from jinja2 import Template
from loguru import logger

from ch03.llm import (
  ChatCompletionMessageToolCall,
  LLMParams,
  Message,
  RoleType,
  call_llm,
  call_llm_streaming,
)

#

_ = load_dotenv()

PROMPT_DIR = os.getenv("PROMPT_DIR", "prompts")
if not os.path.exists(PROMPT_DIR):
  raise ValueError(
    f"Prompt directory {PROMPT_DIR} does not exist."
  )

#


def parse_frontmatter(
  content: str,
) -> tuple[dict[str, Any], str]:
  """
  Parse frontmatter from a string content.

  Parameters
  ----------
  content : str
      The input string containing potential frontmatter.

  Returns
  -------
  tuple[dict, str]
      A tuple containing two elements:
      - dict: The parsed frontmatter as a dictionary.
      - str: The remaining content after frontmatter.

  Notes
  -----
  Frontmatter should be enclosed in triple dashes
  (---) at the beginning of the content. If no
  frontmatter is found, an empty dictionary is
  returned along with the original content.
  """
  metadata: dict[str, Any] = {}
  if content.startswith("---"):
    end = content.find("---", 3)
    if end != -1:
      metadata = yaml.safe_load(content[3:end])
      if not isinstance(metadata, dict):
        metadata = {}
      content = content[end + 3 :].strip()
  return metadata, content


#


@dataclass
class Prompt:
  """
  A class representing a prompt for the LLM with
  parameters and Jinja2 templating support.
  """

  template: str
  role: RoleType = "user"
  params: LLMParams = field(default_factory=LLMParams)

  #

  def __str__(self) -> str:
    return self.template

  def __repr__(self) -> str:
    return (
      f"Prompt(template={self.template}"
      + f", role={self.role}"
      + f", model={self.params.model}"
      + f", temperature={self.params.temperature}"
      + f", max_tokens={self.params.max_tokens}"
      + f", top_p={self.params.top_p}"
      + f", frequency_penalty={self.params.frequency_penalty}"
      + f", response_format={self.params.response_format}"
      + ")"
    )

  #

  @classmethod
  def from_markdown_file(
    cls,
    file_path: str,
  ) -> "Prompt":
    """
    Create a prompt from a markdown file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
      metadata, prompt_text = parse_frontmatter(
        f.read()
      )
    if not prompt_text:
      raise ValueError(
        "Markdown file does not contain content."
      )
    params = LLMParams()
    params.model = str(
      metadata.get("model", params.model)
    )
    params.temperature = float(
      metadata.get(
        "temperature",
        params.temperature,
      )
    )
    params.max_tokens = int(
      metadata.get(
        "max_tokens",
        params.max_tokens,
      )
    )
    params.top_p = float(
      metadata.get("top_p", params.top_p)
    )
    params.frequency_penalty = float(
      metadata.get(
        "frequency_penalty",
        params.frequency_penalty,
      )
    )
    params.response_format = metadata.get(
      "response_format",
      params.response_format,
    )

    return cls(
      template=prompt_text,
      params=params,
    )

  #

  def save(
    self,
    name: str,
    prompt_dir: str = PROMPT_DIR,
  ) -> str:
    """
    Save the prompt to a file in the given directory.
    """
    full_path = os.path.join(prompt_dir, f"{name}.md")
    with open(full_path, "w", encoding="utf-8") as f:
      f.write(self.template)
    return full_path

  def render(
    self,
    **kwargs: Any,
  ) -> str:
    """
    Render the prompt template with the given variables.
    """
    template = Template(self.template)
    return template.render(**kwargs)

  async def call_llm(
    self,
    history: list[Message] | None = None,
    user_input: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    **template_vars: Any,
  ) -> str | ChatCompletionMessageToolCall:
    """
    Call the LLM with the given prompt input,
    incorporating conversation history and tools.
    """
    messages = self._prepare_messages(
      template_vars, history, user_input
    )
    return await call_llm(
      messages=messages,
      params=self.params,
      tools=tools,
    )

  async def call_llm_streaming(
    self,
    history: list[Message] | None = None,
    user_input: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    **template_vars: Any,
  ) -> AsyncGenerator[dict[str, Any], None]:
    """
    Call the LLM with streaming enabled.
    """
    messages = self._prepare_messages(
      template_vars, history, user_input
    )
    async for chunk in call_llm_streaming(
      messages=messages,
      params=self.params,
      tools=tools,
    ):
      yield chunk

  def _prepare_messages(
    self,
    template_vars: dict[str, Any],
    history: list[Message] | None = None,
    user_input: str | None = None,
  ) -> list[Message]:
    """
    Prepare the messages for the LLM call.
    """
    prompt = self.render(**template_vars)

    messages: list[Message] = []
    if self.role == "system":
      messages.append(
        {"role": self.role, "content": prompt}
      )
      if history:
        for message in history:
          if message["role"] == "system":
            raise ValueError(
              "System prompt cannot be duplicated."
            )
        messages.extend(history)
    else:
      if history:
        messages.extend(history)
      messages.append(
        {"role": self.role, "content": prompt}
      )

    if user_input:
      messages.append(
        {"role": "user", "content": user_input}
      )

    return messages


def load_prompt(
  name: str,
  prompt_dir: str = PROMPT_DIR,
) -> Prompt:
  """
  Load a prompt from a file in the given directory.
  """
  full_path = os.path.join(prompt_dir, f"{name}.md")
  logger.info(f"Loading prompt from {full_path}")
  return Prompt.from_markdown_file(file_path=full_path)
