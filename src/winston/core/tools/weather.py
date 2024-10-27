from pydantic import BaseModel

from winston.core.tools import (
  ParameterSchema,
  ToolParameterType,
  create_tool,
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


weather_tool = create_tool(
  name="get_current_weather",
  description="Get the current weather in a given location",
  parameters={
    "location": ParameterSchema(
      type=ToolParameterType.STRING,
      description="The city and state, e.g. San Francisco, CA",
      required=True,
    ),
    "unit": ParameterSchema(
      type=ToolParameterType.STRING,
      description="Temperature unit (celsius or fahrenheit)",
      enum=["celsius", "fahrenheit"],
      required=False,
    ),
  },
  handler=get_current_weather,
  required_params=["location"],
  return_type=WeatherResponse,
)
