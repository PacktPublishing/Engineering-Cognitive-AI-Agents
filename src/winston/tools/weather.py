# src/winston/tools/weather.py

"""Weather tool implementation."""

from enum import Enum

from pydantic import BaseModel, Field

from winston.core.tools import Tool


class Unit(str, Enum):
  """Temperature unit options."""

  FAHRENHEIT = "fahrenheit"
  CELSIUS = "celsius"


class WeatherRequest(BaseModel):
  """Weather request parameters."""

  location: str = Field(
    ...,
    description="The city and state/country to get weather for",
  )
  unit: Unit = Field(
    default=Unit.FAHRENHEIT,
    description="The temperature unit to use",
  )


class WeatherResponse(BaseModel):
  """Weather information response."""

  location: str = Field(
    ..., description="The location queried"
  )
  temperature: str = Field(
    ..., description="Current temperature"
  )
  unit: Unit = Field(
    ..., description="Temperature unit used"
  )
  forecast: list[str] = Field(
    default_factory=list,
    description="Weather forecast for next few days",
  )


async def get_weather(
  params: WeatherRequest,
) -> WeatherResponse:
  """Get the current weather in a given location."""
  # Mock weather data - in production this would call a weather API
  return WeatherResponse(
    location=params.location,
    temperature="72",
    unit=params.unit,
    forecast=["sunny", "windy"],
  )


# Create tool instance
weather_tool = Tool(
  name="get_current_weather",
  description="Get the current weather and forecast for a location",
  handler=get_weather,
  input_model=WeatherRequest,
  output_model=WeatherResponse,
)
