from dataclasses import dataclass
from enum import StrEnum

from winston.core.models import ModelType


class BehaviorType(StrEnum):
  """Types of behaviors an agent can have."""

  CONVERSATION = "conversation"
  FUNCTION = "function"
  EVENT = "event"


@dataclass
class Behavior:
  """
  Enhanced behavior configuration.

  Parameters
  ----------
  type : BehaviorType
      Type of behavior that determines its purpose and handling.
  model : ModelType, optional
      The model to use, defaults to GPT4O_MINI.
  temperature : float, optional
      Temperature for model sampling, defaults to 0.7.
  stream : bool, optional
      Whether to stream responses, defaults to True.
  tool_ids : list[str] | None, optional
      List of tool IDs to enable for this behavior.
  """

  type: BehaviorType
  model: ModelType = ModelType.GPT4O_MINI
  temperature: float = 0.7
  stream: bool = True
  tool_ids: list[str] | None = None
