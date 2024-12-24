from pydantic import BaseModel, Field


class ExecutionOutcome(BaseModel):
  """Structured analysis of tool execution results."""

  tool_name: str = Field(
    description="Name of the tool that was executed"
  )
  outcome: str = Field(
    description="Outcome of the tool execution"
  )


class AnalysisReport(BaseModel):
  """Structured analysis of tool execution results."""

  execution_outcomes: str = Field(
    description="Direct results and their alignment with intent"
  )
  knowledge_updates: list[str] = Field(
    description="New understanding gained from results"
  )
  state_changes: dict[str, Any] = Field(
    description="Required updates to cognitive state"
  )
  forward_implications: list[str] = Field(
    description="Implications for future actions"
  )
  confidence: float = Field(
    description="Confidence in analysis (0-1)"
  )
  reasoning: str = Field(
    description="Explanation of analytical process"
  )
