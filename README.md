# Engineering Cognitive AI Agent – Source Code Companion

This repository is the official source-code companion to the book "Engineering Cognitive AI Agent" by Donald Thompson. It explores the principles and practices of building minimal cognitive agents that maximize LLM capabilities while minimizing orchestration complexity.

## Project Structure

The project is organized as a workspace with the following key components:

- **`common/`**: Shared utilities and configurations used across chapters.
- **`chapter01/`**, **`chapter02/`**, **`chapter03/`**, ...: Code and resources for each chapter.
- **`chroma-repl/`**: Interactive REPL for interacting with Winstons vector-store.

## Getting Started

### Environment Configuration

Before running any chapter code, you need to configure your environment variables:

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update the values as needed:
   - Set your `OPENAI_API_KEY` with a valid OpenAI API key
   - Adjust `LOG_LEVEL`, `LOG_FILE`, and other settings as desired
   - Update `OPENAI_MODEL` if you want to use a different model

### Running Chapter Code

Each chapter contains executable code that demonstrates the concepts covered in that chapter. To run chapter-specific code, use the following command pattern:

```bash
uv run --package <chapter_name> python -m <chapter_name>.main
```

For exmample, to run Chapter 1:

```bash
uv run --package chapter01 python -m chapter01.main
```

To run the REPL, use:

```bash
uv run --package chroma-repl python -m chroma_repl.main
```

...

### Prerequisites

1. Install the `uv` package manager
2. Run `uv sync` to install all dependencies
3. Configure your environment variables (see Environment Configuration above)

## Development

This project uses the `uv` workspace system for managing dependencies and organizing code. To set up the workspace:

1. Install the `uv` package manager.
2. Run `uv sync` to install dependencies.
3. Use `uv run` to execute scripts or test packages.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For questions or feedback, please contact Donald Thompson at [witt3rd@witt3rd.com].
