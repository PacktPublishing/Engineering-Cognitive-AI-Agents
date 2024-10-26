from enum import Enum
from typing import Optional

import litellm
from pydantic import BaseModel


# Define Pydantic models for structured output
class OrderStatus(str, Enum):
  PENDING = "pending"
  SHIPPED = "shipped"
  DELIVERED = "delivered"


class OrderDetails(BaseModel):
  order_id: str
  status: OrderStatus
  estimated_delivery: Optional[str]
  tracking_number: Optional[str]


# Define input model for the function
class OrderLookup(BaseModel):
  order_id: str


# Define function to get order details
def get_order_status(
  params: OrderLookup,
) -> OrderDetails:
  """Get the current status and details for an order"""
  # Mock database lookup
  orders = {
    "12345": {
      "status": OrderStatus.SHIPPED,
      "estimated_delivery": "2024-02-20",
      "tracking_number": "1Z999AA1234567890",
    },
    "67890": {
      "status": OrderStatus.PENDING,
      "estimated_delivery": None,
      "tracking_number": None,
    },
  }

  order = orders.get(params.order_id, {})
  return OrderDetails(
    order_id=params.order_id,
    status=order.get("status", OrderStatus.PENDING),
    estimated_delivery=order.get("estimated_delivery"),
    tracking_number=order.get("tracking_number"),
  )


# Convert function to OpenAI tool format
tools = [
  {
    "type": "function",
    "function": {
      "name": "get_order_status",
      "description": "Get the current status and details for an order",
      "parameters": OrderLookup.model_json_schema(),
    },
  }
]


def check_order_status(order_id: str):
  messages = [
    {
      "role": "system",
      "content": "You are a helpful customer service assistant. Use the provided tools to look up order information.",
    },
    {
      "role": "user",
      "content": f"Can you check the status of my order #{order_id}?",
    },
  ]

  # Make initial completion call with tool
  response = litellm.completion(
    model="gpt-4",
    messages=messages,
    tools=tools,
    tool_choice="auto",
  )

  # Get tool calls from response
  tool_calls = response.choices[0].message.tool_calls

  if tool_calls:
    # Execute function call
    tool_call = tool_calls[0]
    function_args = eval(tool_call.function.arguments)

    # Create OrderLookup instance and call function
    lookup_params = OrderLookup(**function_args)
    function_response = get_order_status(lookup_params)

    # Add function response to messages
    messages.append(response.choices[0].message)
    messages.append(
      {
        "tool_call_id": tool_call.id,
        "role": "tool",
        "name": "get_order_status",
        "content": function_response.model_dump_json(),
      }
    )

    # Get final response
    final_response = litellm.completion(
      model="gpt-4", messages=messages
    )

    return final_response


# Example usage
if __name__ == "__main__":
  response = check_order_status("12345")
  print(response.choices[0].message.content)
