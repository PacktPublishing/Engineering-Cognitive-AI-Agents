from dataclasses import dataclass

from winston.core.models import ModelType


@dataclass
class Behavior:
  """
  Enhanced behavior configuration.

  Parameters
  ----------
  name : str
      Name of the behavior.
  type : str, optional
      Type of behavior, defaults to "default".
  model : ModelType, optional
      The model to use, defaults to GPT4O_MINI.
  temperature : float, optional
      Temperature for model sampling, defaults to 0.7.
  stream : bool, optional
      Whether to stream responses, defaults to True.
  tool_ids : list[str] | None, optional
      List of tool IDs to enable for this behavior.
  """

  name: str
  type: str = "default"
  model: ModelType = ModelType.GPT4O_MINI
  temperature: float = 0.7
  stream: bool = True
  tool_ids: list[str] | None = None
