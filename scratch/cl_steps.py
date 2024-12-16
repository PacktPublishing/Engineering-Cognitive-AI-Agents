import chainlit as cl
from openai import AsyncOpenAI

client = AsyncOpenAI()


@cl.on_message
async def main(msg: cl.Message):
  async with cl.Step(name="gpt4", type="llm") as step:
    step.input = msg.content

    stream = await client.chat.completions.create(
      messages=[
        {"role": "user", "content": msg.content}
      ],
      stream=True,
      model="gpt-4",
      temperature=0,
    )

    async for part in stream:
      delta = part.choices[0].delta
      if delta.content:
        # Stream the output of the step
        await step.stream_token(delta.content)
