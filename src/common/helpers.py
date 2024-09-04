import json
import re
from typing import Any, Optional, Union


def extract_code_fence(text: str) -> Optional[str]:
  """
  Extract the content of a code fence from the given text, if it exists.

  Parameters
  ----------
  text : str
      The input text that may contain a code fence.

  Returns
  -------
  Optional[str]
      The content within the code fence if found, otherwise None.

  Examples
  --------
  >>> extract_code_fence("```\\n[ { "a": 1 } ]\\n```")
  '[ { "a": 1 } ]'
  >>> extract_code_fence("```json\\n[ { "a": 1 } ]\\n```")
  '[ { "a": 1 } ]'
  >>> extract_code_fence("No code fence here")
  None
  """
  pattern = r"```(?:\w+)?\s*\n(.*?)\n```"
  match = re.search(pattern, text, re.DOTALL)
  return match.group(1).strip() if match else None


def get_json(json_data: Any) -> Union[list, dict]:
  """
  Parse and extract JSON data from various input formats.

  Parameters
  ----------
  json_data : Any
      The input JSON data, which can be a string, list, or dictionary.

  Returns
  -------
  Union[list, dict]
      The extracted JSON data as a list or dictionary.

  Raises
  ------
  ValueError
      If the JSON data is not in the expected format or cannot be parsed.

  Examples
  --------
  >>> get_json('{"key": [1, 2, 3]}')
  {'key': [1, 2, 3]}
  >>> get_json([1, 2, 3])
  [1, 2, 3]
  >>> get_json('```json\\n{"a": 1, "b": 2}\\n```')
  {'a': 1, 'b': 2}
  """
  if isinstance(json_data, str):
    code_content = extract_code_fence(json_data)
    if code_content:
      json_data = code_content

    try:
      json_data = json.loads(json_data)
    except json.JSONDecodeError as e:
      raise ValueError(
        f"Invalid JSON data: {e}"
      ) from e

  if not isinstance(json_data, (list, dict)):
    raise ValueError(
      "The JSON data must be a list or dictionary."
    )

  return json_data


def get_json_list(json_data: Any) -> list:
  """
  Get a list from a JSON object.

  Parameters
  ----------
  json_data : Any
      The input JSON data, which can be a string, list, or dictionary.

  Returns
  -------
  list
      The extracted list from the JSON data.

  Raises
  ------
  ValueError
      If the JSON data does not contain a list or is not in the expected format.

  Examples
  --------
  >>> get_json_list('{"key": [1, 2, 3]}')
  [1, 2, 3]
  >>> get_json_list([1, 2, 3])
  [1, 2, 3]
  >>> get_json_list("```json\\n[1, 2, 3]\\n```")
  [1, 2, 3]
  """
  result = get_json(json_data)
  if isinstance(result, list):
    return result
  if isinstance(result, dict):
    list_value = next(
      (
        v
        for v in result.values()
        if isinstance(v, list)
      ),
      None,
    )
    if list_value is not None:
      return list_value
  raise ValueError(
    "The JSON data does not contain a list."
  )


def get_json_object(json_data: Any) -> dict:
  """
  Get a dictionary from a JSON object.

  Parameters
  ----------
  json_data : Any
      The input JSON data, which can be a string, list, or dictionary.

  Returns
  -------
  dict
      The extracted dictionary from the JSON data.

  Raises
  ------
  ValueError
      If the JSON data is not a dictionary or is not in the expected format.

  Examples
  --------
  >>> get_json_object('{"key": {"a": 1, "b": 2}}')
  {'a': 1, 'b': 2}
  >>> get_json_object('{"a": 1, "b": 2}')
  {'a': 1, 'b': 2}
  >>> get_json_object(
  ...   '```json\\n{"a": 1, "b": 2}\\n```'
  ... )
  {'a': 1, 'b': 2}
  """
  result = get_json(json_data)
  if isinstance(result, dict):
    return result
  raise ValueError(
    "The JSON data is not a dictionary."
  )
