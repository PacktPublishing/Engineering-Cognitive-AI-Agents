"""Core agent interfaces and base implementation."""

import json
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel


@dataclass
class AgentConfig(BaseModel):
  """Enhanced agent configuration with validation."""

  id: str
  model: str
  vision_model: str | None = None
  system_prompt: str
  temperature: float = 0.7
  stream: bool = True
  max_retries: int = 3
  timeout: float = 30.0
  workspace_template: str | None = None

  @classmethod
  def from_yaml(
    cls, path: str | Path
  ) -> "AgentConfig":
    """Load configuration from a YAML file.

    Parameters
    ----------
    path : str | Path
        Path to the YAML configuration file

    Returns
    -------
    AgentConfig
        Loaded and validated configuration

    Raises
    ------
    FileNotFoundError
        If the configuration file doesn't exist
    ValueError
        If the configuration is invalid
    """
    path = Path(path)
    with path.open() as f:
      config_data = yaml.safe_load(f)

    return cls.model_validate(config_data)

  @classmethod
  def from_json(
    cls, path: str | Path
  ) -> "AgentConfig":
    """Load configuration from a JSON file.

    Parameters
    ----------
    path : str | Path
        Path to the JSON configuration file

    Returns
    -------
    AgentConfig
        Loaded and validated configuration

    Raises
    ------
    FileNotFoundError
        If the configuration file doesn't exist
    ValueError
        If the configuration is invalid
    """
    path = Path(path)
    with path.open() as f:
      config_data = json.load(f)

    return cls.model_validate(config_data)
