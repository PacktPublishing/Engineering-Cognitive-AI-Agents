# Engineering Cognitive AI Agents

This repository contains the code for the book "Engineering Cognitive AI Agents" by [Donald Thompson](https://github.com/witt3rd).

Each chapter has its own subfolder containing the full, self-contained project(s) for that chapter. If code from previous chapters is needed, it will be included in the chapter's subfolder. If the chapter contains multiple projects, they will be in separate subfolders.

## General Setup

### Python

The code in this repository is written for Python 3.11.9. You can download Python from the [official website](https://www.python.org/downloads/) or use a version manager like [pyenv](https://github.com/pyenv/pyenv). Each python project will have its own `requirements.txt` file that lists the dependencies for that project. You can install the dependencies by running `pip install -r requirements.txt` in the project's directory. It is recommended to use a virtual environment to manage dependencies, which can be done with the `venv` module or a tool like `pyenv`. With `venv`, you can create a virtual environment by running `python -m venv venv` in the project's directory, and activate it with `source venv/bin/activate` on Unix systems or `venv\Scripts\activate` on Windows _before_ running `pip install`.

### Framework Usage

We have kept the use of agent and LLM frameworks (e.g., [LangChain](https://www.langchain.com/), [LlamaIndex](https://www.llamaindex.ai/), [AutoGen](https://microsoft.github.io/autogen/), [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview), [Haystack](https://haystack.deepset.ai/), et al) to a minimum for several reasons. First, the book is intended to be a general guide to building agents, and we want to focus on the core concepts rather than the specifics of any particular framework. Second, the field of conversational agents is rapidly evolving, and we want to provide a foundation that will be useful regardless of the specific tools you choose to use. Finally, we want to make the code as accessible as possible to readers who may not be familiar with these frameworks and to avoid picking one framework over another.

#### LiteLLM

That being said, we do use [LiteLLM](https://docs.litellm.ai/docs/), which provides a unified, high-level interface for interacting with various large language models (LLMs) and providers, simplifying Python code by abstracting away the complexities of different APIs and allowing easy switching between models and providers without modifying the application logic.

#### Chainlit

[Chainlit](https://chainlit.io/) offers an efficient way to develop user experiences for LLM-powered agents by providing a high-level, React-based framework for interactive chatbot interfaces, allowing you to focus on your agent's logic. It has support for the most popular agent frameworks, so it will scale with you as you explore beyond our book.

## Development Setup

### VS Code

### Python Project and Package Management

We use [rye](https://rye.astral.sh/) for hassle-free management of Python projects and packages. It includes the [ruff](https://docs.astral.sh/ruff/) linter and formatter and the [uv](https://github.com/astral-sh/uv) package manager.

#### Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to ensure that code is formatted and linted before committing it. The configuration is stored in the `.pre-commit-config.yaml` file in the root of the repository. For `ruff`, the latest pre-commit configuration can be found [here](https://github.com/astral-sh/ruff-pre-commit).

To install the pre-commit hooks, run `pre-commit install` in the root of the repository. This will set up the hooks to run automatically when you commit changes. If you want to run the hooks manually, you can use `pre-commit run --all-files`.
