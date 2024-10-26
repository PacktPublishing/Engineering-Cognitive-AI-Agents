# examples/ch03/winston_tools.py
from pydantic import BaseModel, Field

from winston.core.agent import (
  AgentConfig,
)
from winston.core.behavior import (
  Behavior,
  BehaviorType,
)
from winston.core.models import ModelType
from winston.core.tools import (
  Tool,
  ToolParameter,
  ToolRegistry,
  ToolSchema,
)
from winston.ui.chainlit_app import AgentChat


class WeatherRequest(BaseModel):
  location: str = Field(
    ...,
    description="The city and state, e.g. San Francisco, CA",
  )
  unit: str | None = Field(
    None,
    description="The unit of temperature, either 'celsius' or 'fahrenheit'",
  )


class WeatherResponse(BaseModel):
  location: str
  temperature: str
  unit: str
  forecast: list[str]


async def get_current_weather(
  location: str,
  unit: str | None = None,
) -> WeatherResponse:
  """
  Get the current weather in a given location.

  Parameters
  ----------
  location : str
      The city and state, e.g. San Francisco, CA
  unit : str | None, optional
      The unit of temperature, either 'celsius' or 'fahrenheit'

  Returns
  -------
  WeatherResponse
      The weather response containing location, temperature, unit, and forecast.
  """
  return WeatherResponse(
    location=location,
    temperature="72",
    unit=unit or "fahrenheit",
    forecast=["sunny", "windy"],
  )


weather_tool = Tool(
  name="get_current_weather",
  description="Get the current weather in a given location",
  parameters=ToolSchema(
    type="object",
    properties={
      "location": ToolParameter(
        type="string",
        description="The city and state, e.g. San Francisco, CA",
      ),
      "unit": ToolParameter(
        type="string",
        description="The unit of temperature, either 'celsius' or 'fahrenheit'",
        enum=["celsius", "fahrenheit"],
      ),
    },
    required=["location"],
  ),
  handler=get_current_weather,
)

# Register the tool
tool_registry = ToolRegistry()
tool_registry.register(weather_tool)


class ToolEnabledWinstonChat(AgentChat):
  """Winston chat interface with tool support"""

  def load_config(self) -> AgentConfig:
    """
    Load Winston configuration with tool support.

    Returns
    -------
    AgentConfig
        The agent configuration with tool support.
    """
    return AgentConfig(
      id="winston",
      type="assistant",
      capabilities={"conversation"},
      behaviors=[
        Behavior(
          type=BehaviorType.CONVERSATION,
          model=ModelType.GPT4O_MINI,
          temperature=0.7,
          stream=True,
          tool_ids=["get_current_weather"],
        ),
      ],
      prompts={
        "system": """You are Winston, the super-intelligent British advisor
                            with a razor-sharp wit and a delightful penchant for sarcasm. You
                            have access to various tools and capabilities that you can use to
                            assist users. When weather information is requested, use the
                            get_current_weather function to obtain accurate data."""
      },
    )


# Create the application
app = ToolEnabledWinstonChat()
