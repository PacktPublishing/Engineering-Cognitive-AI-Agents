#!/usr/bin/env python3
"""
Winston Minimal Cognitive Kernel - Proof that <200 lines can do cognitive agency
Chapter 2: What's the absolute minimum needed for cognition?

The entire cognitive loop: reason -> match intent -> execute -> repeat.
No orchestration bloat. No complex schemas. Pure cognitive simplicity.
"""

import json
from datetime import datetime
from typing import Any, cast

from openai import OpenAI
from loguru import logger
from jinja2 import Environment, FileSystemLoader
from common.config import initialize_config, setup_logging, OPENAI_API_KEY, OPENAI_MODEL, config
from common import initialize_intent_database
from common.intent_database import index_tool, query_tools_by_intent
from .tool_registry import execute_tool_function
from .mock_tools import TOOL_SCHEMAS

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = OPENAI_MODEL

# Prompt templates
template_env = Environment(loader=FileSystemLoader("./prompts"))

# The only persistent state Winston needs
action_trace: list[dict[str, str]] = []

# Minimal core functions - the only tools Winston needs built-in
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

FALLBACK_ACTION_TOOLS = [
    {
        "type": "function",
        "name": "insufficient_information",
        "description": "Tools are suitable but essential parameters are missing.",
        "parameters": {
            "type": "object",
            "properties": {
                "missing_parameters": {
                    "type": "string",
                    "description": "Description of what specific information is needed",
                }
            },
            "required": ["missing_parameters"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "no_suitable_tool",
        "description": "None of the available tools are suitable for the intent.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Explanation of why no tool is suitable",
                }
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


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
    print(f"✓ Task Complete: {reason}")
    return "COMPLETE"


def task_blocked(reason: str) -> str:
    """Mark task as blocked."""
    add_to_trace("Task analysis", "task_blocked", reason)
    print(f"✗ Task Blocked: {reason}")
    return "BLOCKED"


def reason_about_task(task_description: str) -> dict[str, Any] | None:
    """The reasoning phase - let the model think about the task."""
    try:
        template = template_env.get_template("chapter02/reasoning.md")
        prompt = template.render(
            task_description=task_description,
            action_trace=action_trace,
            timestamp=datetime.now().isoformat(),
        )

        response = client.responses.create(
            model=MODEL,
            input=prompt,
            tools=cast(Any, REASONING_TOOLS),
            tool_choice="auto",
        )

        if response.status == "completed":
            for item in response.output:
                if item.type == "function_call":
                    return {
                        "function": item.name,
                        "arguments": json.loads(item.arguments),
                    }
        return None
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return None


def execute_intent(
    intent: str, rationale: str, task_description: str, collection
) -> None:
    """Match intent to tools and execute - the action phase with LLM tool selection."""
    logger.info(f"Processing intent: '{intent}' with rationale: '{rationale}'")

    # Query ChromaDB for tools matching the intent
    matching_tools = query_tools_by_intent(collection, intent)

    if not matching_tools:
        add_to_trace(rationale, intent, "No suitable tools found for intent")
        logger.info(f"No tools found for intent '{intent}' - continuing reasoning")
        return

    logger.info(f"Found {len(matching_tools)} tools for intent '{intent}'")

    # Build action prompt with available tools
    try:
        action_template = template_env.get_template("chapter02/action.md")
        action_prompt = action_template.render(
            task_description=task_description,
            current_intent=intent,
            intent_rationale=rationale,
            available_tools=matching_tools,
            action_trace=action_trace,
            timestamp=datetime.now().isoformat(),
        )

        # Create tool schemas for OpenAI function calling
        action_tools = []
        for tool in matching_tools:
            action_tools.append({
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "strict": tool.get("strict", True),
            })

        # Add fallback functions
        action_tools.extend(FALLBACK_ACTION_TOOLS)

        # Call OpenAI with action prompt and matched tools
        response = client.responses.create(
            model=MODEL,
            input=action_prompt,
            tools=cast(Any, action_tools),
            tool_choice="required",  # Force tool selection
        )

        if response.status != "completed":
            logger.warning(f"Action response status: {response.status}")
            add_to_trace(rationale, intent, "action phase failed")
            return

        # Process tool calls
        for output_item in response.output:
            if output_item.type == "function_call":
                function_name = output_item.name
                arguments = json.loads(output_item.arguments)

                logger.info(f"Action phase selected tool: {function_name}")

                if function_name == "insufficient_information":
                    result = (
                        f"Insufficient information: {arguments['missing_parameters']}"
                    )
                    add_to_trace(rationale, intent, result)
                    return

                if function_name == "no_suitable_tool":
                    result = f"No suitable tool: {arguments['reason']}"
                    add_to_trace(rationale, intent, result)
                    return

                # Execute the selected tool
                tool_result = execute_tool_function(function_name, arguments)
                add_to_trace(rationale, f"{intent} -> {function_name}", tool_result)
                logger.success(f"Tool executed: {function_name} -> {tool_result}")
                return

        # No function call received
        add_to_trace(rationale, intent, "no tool selection made")

    except Exception as e:
        error_msg = f"Action phase error: {e}"
        logger.error(error_msg)
        add_to_trace(rationale, intent, error_msg)


def setup_demo_tools(collection) -> None:
    """Setup Chapter 2's demo communication tools."""
    intent = "communicate with colleagues"
    for tool_name, tool_schema in TOOL_SCHEMAS.items():
        index_tool(collection, tool_schema, intent, "communication")
    logger.info("Demo tools ready")


def run_cognitive_loop(
    task_description: str, collection, max_iterations: int = 10
) -> str:
    """The pure cognitive loop - reason, act, repeat."""
    logger.info(f"Starting: {task_description}")

    # Clear trace for new task
    global action_trace
    action_trace = []

    # The cognitive loop
    for iteration in range(max_iterations):
        logger.debug(f"Iteration {iteration + 1}")

        # Stage 1: Reason about the task
        decision = reason_about_task(task_description)

        if not decision:
            continue

        function_name = decision["function"]
        args = decision["arguments"]

        # Stage 2: Execute the decision
        if function_name == "task_complete":
            return task_complete(args["reason"])
        elif function_name == "task_blocked":
            return task_blocked(args["reason"])
        elif function_name == "do":
            execute_intent(
                args["intent"], args["rationale"], task_description, collection
            )
            # Continue loop with action results in trace

    return task_blocked(f"Max iterations ({max_iterations}) reached")


def _setup_environment() -> None:
    """Set up the environment including logging configuration.

    This must be called before any other Winston operations that use logging.
    """
    # Initialize configuration first and update global config reference
    global config
    config = initialize_config("chapter02")

    # Configure logging using centralized config
    log_file = config.get_chapter_path("logs", create=True) / "winston.log"
    setup_logging(log_file=str(log_file))


def main() -> None:
    """Simple CLI for testing Winston's cognitive capabilities."""
    print("Winston Minimal Cognitive Kernel")
    print("================================")

    # Setup environment first (logging, etc.)
    _setup_environment()

    print("Initializing intent database...")

    # Setup intent database once at startup
    # Use the global config object that was initialized in _setup_environment
    persist_dir = str(config.get_chapter_path("chroma_db", create=True))
    collection = initialize_intent_database(persist_dir)
    setup_demo_tools(collection)

    print("Ready! Enter a task or 'quit' to exit.\n")

    while True:
        try:
            task = input("Task: ").strip()
            if task.lower() in ["quit", "exit", ""]:
                break

            result = run_cognitive_loop(task, collection)
            print(f"Actions: {len(action_trace)}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
