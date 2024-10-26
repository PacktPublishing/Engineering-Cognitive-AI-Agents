# src/winston/tools/weather.py
from pydantic import BaseModel

from winston.core.tools import (
  Tool,
  ToolParameter,
  ToolRegistry,
  ToolSchema,
)


class WeatherResponse(BaseModel):
  """
  Weather information response.

  Attributes
  ----------
  location : str
      The location for the weather report.
  temperature : str
      The current temperature.
  unit : str
      The temperature unit (celsius or fahrenheit).
  forecast : list[str]
      List of weather conditions.
  """

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
      The city and state, e.g. San Francisco, CA.
  unit : str | None, optional
      The unit of temperature, either 'celsius' or 'fahrenheit'.

  Returns
  -------
  WeatherResponse
      The weather information for the location.
  """
  return WeatherResponse(
    location=location,
    temperature="72",
    unit=unit or "fahrenheit",
    forecast=["sunny", "windy"],
  )


# Define the weather tool
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
        description="Temperature unit (celsius or fahrenheit)",
        enum=["celsius", "fahrenheit"],
      ),
    },
    required=["location"],
  ),
  handler=get_current_weather,
)

# Register the tool
ToolRegistry().register(weather_tool)
