#!/usr/bin/env python3
"""
Winston Basic Cognitive Kernel - The simplest possible cognitive agent
Chapter 2: What's the absolute minimum needed for cognition?

A demonstration that meaningful AI agency requires surprisingly little orchestration.
This basic implementation proves the three-function paradigm works without any external capabilities.
"""

import json
from datetime import datetime
from typing import Any, cast

from openai import OpenAI
from loguru import logger
from jinja2 import Environment, FileSystemLoader
from common.config import initialize_config, setup_logging, OPENAI_API_KEY, OPENAI_MODEL

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = OPENAI_MODEL

# Prompt templates
template_env = Environment(loader=FileSystemLoader("./prompts"))

# The only persistent state Winston needs
action_trace: list[dict[str, str]] = []

# Basic reasoning tools - the minimal set Winston needs
REASONING_TOOLS = [
    {
        "type": "function",
        "name": "task_complete",
        "description": "Mark the current task as completed with a reason.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why the task is complete"}
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "task_blocked",
        "description": "Mark the current task as blocked with a reason.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why the task is blocked"}
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "do",
        "description": "Execute an action with given intent and rationale.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "The intent or goal of the action",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action should be taken",
                },
            },
            "required": ["intent", "rationale"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


@logger.catch
def build_prompt(task_description: str) -> str:
    """Construct complete prompt using Jinja2 template substitution.

    Parameters
    ----------
    task_description : str
        The user's task specification.

    Returns
    -------
    str
        Rendered prompt string ready for LLM processing.

    Examples
    --------
    >>> prompt = build_prompt("Test task")
    >>> len(prompt) > 0
    True
    """
    try:
        system_template = template_env.get_template("chapter02/system.md")

        prompt = system_template.render(
            task_description=task_description,
            action_trace=action_trace,
            timestamp=datetime.now().isoformat(),
        )

        logger.debug(f"Built prompt for task: {task_description[:50]}...")
        return prompt

    except Exception as e:
        logger.error(f"Failed to build prompt: {e}")
        raise


def add_to_trace(reasoning: str, action: str, result: str) -> None:
    """Add an entry to the action trace - Winston's only state."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reasoning": reasoning,
        "action": action,
        "result": result,
    }
    action_trace.append(entry)
    logger.info(f"Trace: {action} -> {result}")


def task_complete(reason: str) -> str:
    """Mark task as completed."""
    add_to_trace("Task analysis", "task_complete", reason)
    return f"Task completed: {reason}"


def task_blocked(reason: str) -> str:
    """Mark task as blocked."""
    add_to_trace("Task analysis", "task_blocked", reason)
    return f"Task blocked: {reason}"


@logger.catch
def do(intent: str, rationale: str) -> str:
    """Execute an action with given intent and rationale.

    Parameters
    ----------
    intent : str
        The intent or goal of the action.
    rationale : str
        Why this action should be taken.

    Returns
    -------
    str
        Action result message.

    Examples
    --------
    >>> result = do("analyze", "need to understand problem")
    >>> len(result) > 0
    True
    """
    add_to_trace(rationale, intent, "action logged")
    logger.info(f"Action: {intent} (Rationale: {rationale})")

    # In Chapter 2, Winston has no real capabilities
    # Actions are logged but don't execute external operations
    return f"Action '{intent}' logged with rationale: {rationale}"


@logger.catch
def handle_function_call(function_call: Any) -> str | None:
    """Handle function calls from the LLM response.

    Parameters
    ----------
    function_call : Any
        OpenAI function call object.

    Returns
    -------
    str | None
        Function result or None if continuing cognitive loop.

    Examples
    --------
    >>> # Would be called with actual OpenAI function call object
    >>> # result = handle_function_call(mock_function_call)
    >>> # isinstance(result, str) or result is None
    True
    """
    try:
        function_name = function_call.name
        arguments = json.loads(function_call.arguments)

        logger.debug(f"Executing function: {function_name} with args: {arguments}")

        if function_name == "task_complete":
            return task_complete(arguments["reason"])
        elif function_name == "task_blocked":
            return task_blocked(arguments["reason"])
        elif function_name == "do":
            do(arguments["intent"], arguments["rationale"])
            return None  # Continue cognitive loop
        else:
            logger.error(f"Unknown function: {function_name}")
            return None

    except Exception as e:
        logger.error(f"Function call handling failed: {e}")
        return None


@logger.catch
def run_task(task_description: str, max_iterations: int = 10) -> str | None:
    """The entire cognitive loop - Winston's core reasoning process.

    Parameters
    ----------
    task_description : str
        Description of the task to accomplish.
    max_iterations : int, default=10
        Maximum cognitive loop iterations to prevent infinite loops.

    Returns
    -------
    str | None
        Final result of the task or None if task fails.

    Examples
    --------
    >>> result = run_task("Simple test task")
    >>> isinstance(result, str) or result is None
    True
    """
    logger.info(f"Starting task: {task_description}")

    # Clear action trace for new task
    global action_trace
    action_trace = []

    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        logger.debug(f"Cognitive loop iteration {iterations}")

        try:
            # Build prompt with current task and trace context
            prompt = build_prompt(task_description)

            # Get reasoning from LLM
            response = client.responses.create(
                model=MODEL,
                input=prompt,
                tools=cast(Any, REASONING_TOOLS),
                tool_choice="auto",
            )

            # Check response status
            if response.status != "completed":
                logger.warning(f"Response status: {response.status}")
                continue

            # Handle function calls
            for output_item in response.output:
                if output_item.type == "function_call":
                    result = handle_function_call(output_item)
                    if result:  # Task completed or blocked
                        logger.info(f"Task finished after {iterations} iterations")
                        return result

            # If no function call received, log and continue
            logger.debug("No function call received, continuing reasoning")

        except Exception as e:
            logger.error(f"Error in cognitive loop iteration {iterations}: {e}")
            continue

    # Max iterations reached
    logger.warning(f"Task incomplete after {max_iterations} iterations")
    return task_blocked(
        f"Maximum iterations ({max_iterations}) reached without completion"
    )


def show_trace() -> None:
    """Display the current action trace in a readable format.

    Shows all entries in the action trace with timestamps,
    reasoning, actions, and results.
    """
    if not action_trace:
        print("Action trace is empty.")
        return

    print(f"\nAction Trace ({len(action_trace)} entries):")
    print("=" * 60)

    for i, entry in enumerate(action_trace, 1):
        print(f"\n{i}. {entry['timestamp']}")
        print(f"   Reasoning: {entry['reasoning']}")
        print(f"   Action:    {entry['action']}")
        print(f"   Result:    {entry['result']}")

    print("=" * 60)


def handle_command(command: str) -> bool:
    """Handle CLI commands that start with '/'.

    Parameters
    ----------
    command : str
        The command string starting with '/'

    Returns
    -------
    bool
        True if command was handled, False otherwise
    """
    command = command.lower().strip()

    if command == "/showtrace":
        show_trace()
        return True
    elif command in ["/help", "/?"]:
        print("\nAvailable commands:")
        print("  /showTrace  - Display the current action trace")
        print("  /help, /?   - Show this help message")
        print("  quit, exit  - Exit Winston\n")
        return True
    else:
        print(f"Unknown command: {command}")
        print("Type '/help' for available commands.")
        return True


def _setup_environment() -> None:
    """Set up the environment for Winston.

    Configures logging and other environment settings.
    """
    # Initialize configuration and configure logging using centralized config
    config = initialize_config("chapter02")
    log_file = config.get_chapter_path("logs", create=True) / "winston_basic.log"
    setup_logging(log_file=str(log_file))


def main() -> None:
    """REPL-like CLI interface for testing Winston's cognitive capabilities.

    Provides interactive way to test the minimal cognitive kernel.
    Supports commands starting with '/' for debugging and inspection.
    """
    # Setup environment first (logging, etc.)
    _setup_environment()
    print("Winston Kernel - Minimal Cognitive Agent")
    print("Chapter 2: What's the absolute minimum needed for cognition?")
    print("========================================================")
    print("Enter tasks for Winston to accomplish.")
    print("Type 'quit', 'exit', or press Ctrl+C to exit.")
    print("Type '/help' for available commands.\n")

    while True:
        try:
            task = input("Task: ").strip()

            if task.lower() in ["quit", "exit", ""]:
                print("Goodbye!")
                break

            # Handle CLI commands
            if task.startswith("/"):
                handle_command(task)
                continue

            print(f"\nProcessing: {task}")
            print("-" * 50)

            # Run the cognitive loop
            result = run_task(task)

            print(f"\nResult: {result}")
            print(f"Actions taken: {len(action_trace)}")
            print("=" * 50)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"CLI error: {e}")
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
