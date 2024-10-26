# Chatbot with Tool

An essential aspect of an agent is that it can use "tools" (i.e., functions) to perform actions. In this example, we build on the previous chatbot example by adding a simple tool that the LLM can use, as appropriate, during conversation with the user. We'll go more deeply into tools and API use by agents in later chapters, but for now, we'll just show how to add a simple tool to the (streaming) chatbot.

## Features

First, we add a simple function that will return the current temperature for a given location in the requested units. In a real application, this tool would call a weather API to get the forecast, but for now, we'll just return a dummy forecast.

Next, we must describe this function as a _tool_ for the LLM to use. This follows a standard format established by [OpenAI function calling](https://platform.openai.com/docs/guides/function-calling). This tool specification describes the name, the purpose of the function, and its parameters.

We are also taking advantage of [Chainlit's step concept](https://docs.chainlit.io/concepts/step). Steps represent the individual tasks or operations performed by a language model to process a user's request. Each step has a type (e.g., "tool"), input, output, and a start/end time. In the Chainlit UI, steps of type "tool" are displayed in real time, giving users insight into the model's chain of thought.

The only complicating aspect of this example is that we must process the LLM response to determine if the tool was called and, if so, extract the tool's call details. Since we are using a streaming model, we need to accumulate the results before we can actually invoke the tool.

It is important to note that the LLM can't actually call the tool. Instead, the tool is called by the application, which then updates the conversation history with the tool's response. This is a common pattern in agent-based systems.

## Changes

We've changed the `handle_message` function to:

- get the conversation history from the user session
- append the new user message to the history
- pass the history to the model for generating the response
- append the response to the history

## Quickstart

To get started with the basic chatbot using Chainlit and LiteLLM, follow these steps:

1. Clone the repository and navigate to the `0_basic_chatbot` directory.
1. Ensure you have an OpenAI API key. If you don't have one, you can sign up for one [here](https://platform.openai.com/signup).
1. Your OpenAI API key should be set as an environment variable `OPENAI_API_KEY`. Either set it in your environment or copy the `.env.example` file to `.env` in the `0_basic_chatbot` directory and set it there.
1. **Optional**: If you want to use a local model instead of OpenAI, you can install [Ollama](https://ollama.com/) and uncomment the lines in `app.py` that import and use the local model:

   ```python
   # MODEL = "gpt-4o-mini"
   MODEL = "ollama_chat/llama3"
   ```

1. Create a virtual environment and install the dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install .
   ```

1. Run the app:

```bash
chainlit app.py
```
