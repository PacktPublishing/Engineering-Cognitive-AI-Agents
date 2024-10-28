"""Path management utilities for Winston agents."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentPaths:
  """Manages paths relative to the agent's root directory."""

  root: Path

  @property
  def config(self) -> Path:
    """Get the config directory path."""
    return self.root / "config"

  @property
  def workspaces(self) -> Path:
    """Get the workspaces directory path."""
    return self.root / "workspaces"
