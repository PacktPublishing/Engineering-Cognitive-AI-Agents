#!/usr/bin/env python3
"""
Winston Chapter 3: Hierarchical Capability Discovery

This kernel evolves Chapter 2's design by replacing a flat tool database
with a hierarchical intent graph, managed by an MCP Host. The cognitive
loop now involves the agent reasoning its way down the hierarchy to find
the right tool.
"""

from __future__ import annotations

import json
import hashlib
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click
from openai import AsyncOpenAI
from loguru import logger
from jinja2 import Environment, FileSystemLoader
from chromadb import Collection

# Import all Winston modules
from common.paths import get_chapter_path
from common.config import setup_logging, OPENAI_API_KEY, OPENAI_MODEL
from common import (
    MCPHost,
    IntentGenerator,
    initialize_intent_database,
    query_intent_nodes,
)

# Initialize OpenAI client
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)
MODEL = OPENAI_MODEL

# Prompt templates
template_env = Environment(loader=FileSystemLoader("./prompts"), enable_async=True)
# Add custom filter for JSON parsing in templates
template_env.filters["from_json"] = json.loads

# The only persistent state Winston needs
action_trace: list[dict[str, str]] = []

# Minimal core functions - the only tools Winston needs built-in
REASONING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": "Mark the current task as completed with a reason and optional result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the task is complete",
                    },
                    "result": {
                        "type": "string",
                        "description": "The final answer or result if the task was a question or required a specific output",
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_blocked",
            "description": "Mark the current task as blocked with a reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the task is blocked",
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
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
            },
        },
    },
]

# Action tools for resolving intents to concrete actions
ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_tool",
            "description": "Execute a specific tool with the provided arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_uri": {
                        "type": "string",
                        "description": "The tool URI in format 'tool::server_name::tool_name'",
                    },
                    "arguments": {
                        "type": "object",
                        "description": "The arguments to pass to the tool",
                    },
                },
                "required": ["tool_uri", "arguments"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refine_intent",
            "description": "Refine the current intent using an L2 intent category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent_id": {
                        "type": "string",
                        "description": "The ID of the L2 intent to use for refinement",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Explanation of how this refinement helps",
                    },
                },
                "required": ["intent_id", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
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
            },
        },
    },
    {
        "type": "function",
        "function": {
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
            },
        },
    },
]


def add_to_trace(reasoning: str, action: str, result: str) -> None:
    """Add an entry to the action trace."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reasoning": reasoning,
        "action": action,
        "result": result,
    }
    action_trace.append(entry)
    logger.info(f"Trace: {action} -> {result}")


def task_complete(reason: str, result: str | None = None) -> str:
    """Mark task as completed.

    Parameters
    ----------
    reason : str
        Explanation of why the task is complete.
    result : str | None, optional
        The final answer or result if the task was a question
        or required a specific output.

    Returns
    -------
    str
        Formatted completion message.
    """
    add_to_trace("Task analysis", "task_complete", reason)

    if result:
        print(f"\n✓ Task Complete: {reason}")
        print(f"\n📋 Result:\n{result}")
    else:
        print(f"\n✓ Task Complete: {reason}")
    return "COMPLETE"


def task_blocked(reason: str) -> str:
    """Mark task as blocked."""
    add_to_trace("Task analysis", "task_blocked", reason)
    print(f"\n✗ Task Blocked: {reason}")
    return "BLOCKED"


async def reason_about_task(task_description: str) -> dict[str, Any] | None:
    """The reasoning phase - let the model think about the task."""
    try:
        template = template_env.get_template("chapter03/reasoning.md")
        prompt = await template.render_async(
            task_description=task_description,
            action_trace=action_trace,
            timestamp=datetime.now().isoformat(),
        )

        response = await aclient.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            tools=cast(Any, REASONING_TOOLS),
            tool_choice="auto",
        )

        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            decision = {
                "function": tool_call.function.name,
                "arguments": json.loads(tool_call.function.arguments),
            }
            logger.info(
                f"REASONING DECISION: {decision['function']} with args: {decision['arguments']}"
            )
            return decision
        else:
            logger.warning("REASONING RESULT: No tool calls returned from LLM")
            return None
    except Exception as e:
        logger.error(f"Reasoning failed: {e}")
        return None


# These functions are no longer needed with the unified action prompt
# They have been replaced by the single LLM call in execute_intent


async def execute_intent(
    intent: str,
    rationale: str,
    task_description: str,
    collection: Collection,
    mcp_host: MCPHost,
) -> None:
    """Match intent to a flat list of L1/L2 intents and execute the chosen action."""
    logger.info(f"Executing intent: '{intent}'")
    add_to_trace(rationale, f"START_INTENT: {intent}", "Begin flexible discovery.")

    # Query the vector database for a flat list of matching intents (both L1 and L2)
    logger.debug(f"Querying intent database for: '{intent}'")
    options = query_intent_nodes(collection, intent)

    if not options:
        logger.warning(
            f"INTENT DATABASE QUERY RESULT: No matching options found for '{intent}'"
        )
        add_to_trace(rationale, intent, "No matching options found in intent database.")
        return

    logger.info(f"INTENT DATABASE QUERY RESULT: Found {len(options)} matching options")
    for i, option in enumerate(options):
        logger.debug(
            f"Option {i + 1}: ID={option.get('id', 'N/A')}, Type={option.get('type', 'N/A')}, Document={option.get('document', '')[:100]}..."
        )
    logger.debug(f"Full options data for template: {options}")

    # Build action prompt with available options
    try:
        action_template = template_env.get_template("chapter03/action.md")
        action_prompt = await action_template.render_async(
            task_description=task_description,
            current_intent=intent,
            intent_rationale=rationale,
            options=options,
            action_trace=action_trace,
            timestamp=datetime.now().isoformat(),
        )

        # Call OpenAI with action prompt and global ACTION_TOOLS
        response = await aclient.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": action_prompt}],
            tools=cast(Any, ACTION_TOOLS),
            tool_choice="auto",
        )

        # Process the response
        message = response.choices[0].message
        if not message.tool_calls:
            logger.warning(
                "ACTION SELECTION RESULT: LLM failed to select an action - no tool calls returned"
            )
            add_to_trace(rationale, intent, "LLM failed to select an action.")
            return

        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name

        # Defensive parsing of arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            logger.error(f"ACTION SELECTION ERROR: Failed to parse tool arguments: {e}")
            add_to_trace(rationale, intent, f"Failed to parse tool arguments: {e}")
            return

        logger.info(f"ACTION SELECTION RESULT: {function_name} with args: {arguments}")

        # Handle the different action types
        if function_name == "execute_tool":
            # Defensive extraction of required arguments
            tool_uri = arguments.get("tool_uri")
            tool_args = arguments.get("arguments", {})

            if not tool_uri:
                error_msg = "Missing required 'tool_uri' argument for execute_tool"
                logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                add_to_trace(rationale, "EXECUTE_TOOL", error_msg)
                return

            # Parse tool_uri to extract server_name and tool_name
            try:
                # tool_uri format: "tool::server_name::tool_name"
                uri_parts = tool_uri.split("::")
                if len(uri_parts) != 3 or uri_parts[0] != "tool":
                    error_msg = f"Invalid tool_uri format: '{tool_uri}' (expected 'tool::server_name::tool_name')"
                    logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                    add_to_trace(rationale, f"EXECUTE_TOOL: {tool_uri}", error_msg)
                    return

                server_name = uri_parts[1]
                tool_name = uri_parts[2]

                if not server_name:
                    error_msg = f"Empty server_name in tool_uri: '{tool_uri}'"
                    logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                    add_to_trace(rationale, f"EXECUTE_TOOL: {tool_uri}", error_msg)
                    return

                if not tool_name:
                    error_msg = f"Empty tool_name in tool_uri: '{tool_uri}'"
                    logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                    add_to_trace(rationale, f"EXECUTE_TOOL: {tool_uri}", error_msg)
                    return

                logger.debug(
                    f"Parsed tool_uri '{tool_uri}' -> server: '{server_name}', tool: '{tool_name}'"
                )

                session = mcp_host.sessions.get(server_name)
                if not session:
                    error_msg = f"No active session for server '{server_name}'"
                    logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                    logger.debug(
                        f"Available sessions: {list(mcp_host.sessions.keys())}"
                    )
                    add_to_trace(rationale, f"EXECUTE_TOOL: {tool_name}", error_msg)
                    return

                logger.success(
                    f"Executing tool '{tool_name}' on server '{server_name}' with args: {tool_args}"
                )
                tool_result = await session.call_tool(tool_name, tool_args)
                result_str = json.dumps([c.dict() for c in tool_result.content])
                logger.info(f"EXECUTE_TOOL RESULT: {result_str[:200]}...")
                add_to_trace(rationale, f"EXECUTE_TOOL: {tool_name}", result_str)

            except Exception as e:
                error_msg = f"Tool execution failed: {e}"
                logger.error(f"EXECUTE_TOOL ERROR: {error_msg}")
                add_to_trace(rationale, f"EXECUTE_TOOL: {tool_uri}", error_msg)

        elif function_name == "refine_intent":
            # Defensive extraction of required arguments
            intent_id = arguments.get("intent_id")
            explanation = arguments.get("explanation", "")

            if not intent_id:
                error_msg = "Missing required 'intent_id' argument for refine_intent"
                logger.error(f"REFINE_INTENT ERROR: {error_msg}")
                add_to_trace(rationale, f"REFINE_INTENT: {intent_id}", error_msg)
                return

            logger.debug(f"Refining intent with ID: {intent_id}")

            # Find the intent document from the options
            refined_intent = None
            for option in options:
                if option.get("id") == intent_id:
                    refined_intent = option.get("document", "")
                    break

            if refined_intent:
                logger.info(
                    f"REFINE_INTENT SUCCESS: Found intent document for ID {intent_id}"
                )
                add_to_trace(
                    rationale,
                    f"REFINE_INTENT: {intent_id}",
                    f"Refined to: {refined_intent}. {explanation}",
                )
            else:
                logger.error(
                    f"REFINE_INTENT ERROR: Failed to find intent document for ID {intent_id}"
                )
                add_to_trace(
                    rationale,
                    f"REFINE_INTENT: {intent_id}",
                    f"Failed to find intent document. {explanation}",
                )

        elif function_name == "insufficient_information":
            missing = arguments.get("missing_parameters", "Unknown parameters")
            logger.info(f"INSUFFICIENT_INFORMATION: {missing}")
            add_to_trace(rationale, intent, f"Insufficient information: {missing}")

        elif function_name == "no_suitable_tool":
            reason = arguments.get("reason", "No reason provided")
            logger.info(f"NO_SUITABLE_TOOL: {reason}")
            add_to_trace(rationale, intent, f"No suitable tool: {reason}")

        else:
            logger.warning(
                f"UNKNOWN ACTION: Unexpected function name '{function_name}' with args: {arguments}"
            )
            add_to_trace(rationale, intent, f"Unknown action: {function_name}")

    except Exception as e:
        error_msg = f"Action phase error: {e}"
        logger.error(error_msg)
        add_to_trace(rationale, intent, error_msg)


async def run_cognitive_loop(
    task_description: str,
    collection: Collection,
    mcp_host: MCPHost,
    max_iterations: int = 10,
) -> str:
    """The pure cognitive loop - reason, act, repeat."""
    logger.info(f"Starting: {task_description}")
    global action_trace
    action_trace = []

    for iteration in range(max_iterations):
        logger.debug(f"Iteration {iteration + 1}")

        decision = await reason_about_task(task_description)
        if not decision:
            logger.warning("Agent failed to make a decision. Blocking task.")
            return task_blocked(
                "Agent failed to make a decision in the reasoning step."
            )

        function_name = decision["function"]
        args = decision["arguments"]

        if function_name == "task_complete":
            return task_complete(args["reason"], args.get("result"))
        elif function_name == "task_blocked":
            return task_blocked(args["reason"])
        elif function_name == "do":
            await execute_intent(
                args["intent"],
                args["rationale"],
                task_description,
                collection,
                mcp_host,
            )

    task_blocked(f"Max iterations ({max_iterations}) reached.")
    return "BLOCKED"


def _calculate_config_hash(config: dict[str, Any]) -> str:
    """Generate a secure hash of the current MCP configuration."""
    config_str = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(config_str.encode("utf-8")).hexdigest()


def _setup_environment() -> None:
    """Set up the environment including logging configuration.

    This must be called before any other Winston operations that use logging.
    """
    # Configure logging
    log_file = get_chapter_path("chapter03", "logs", create=True) / "winston.log"
    setup_logging(log_file)


async def main(task: str | None = None) -> None:
    """Run the Chapter 3 kernel with optional task argument.

    Parameters
    ----------
    task : str, optional
        Task to execute immediately. If None, runs in interactive mode.
    """
    print("Winston Chapter 3: Scaling Agency with an Intent Index")
    print("======================================================")

    # Setup environment first (logging, etc.)
    _setup_environment()

    # 1. Setup Database
    persist_dir = str(get_chapter_path("chapter03", "chroma_db", create=True))
    collection = initialize_intent_database(persist_dir)
    logger.debug(f"Collection initialized with: {collection.count()} items.")

    # 2. Validate Configuration
    from common.config import validate_config, get_config

    config = get_config()
    config["INTENT_DB_PERSIST_DIR"] = persist_dir
    validate_config(config)
    # 2. Setup MCP Host
    config_path = Path("chapter03") / "mcp_config.json"
    mcp_host = MCPHost(config_path)
    await mcp_host.startup()

    # 3. Check for config changes and regenerate intents if needed
    current_hash = _calculate_config_hash(mcp_host.config)
    logger.debug(f"Kernel calculated hash: {current_hash}")
    # 3. Generate and Index Intents
    intent_generator = IntentGenerator(aclient, mcp_host, template_env, persist_dir)
    await intent_generator.generate_and_store_intents_if_needed(collection)

    print(f"\nIndexed {collection.count()} items. Ready for tasks.")

    try:
        if task:
            # CLI mode: execute single task
            print(f"Executing task: {task}\n")
            await run_cognitive_loop(task, collection, mcp_host)
            print(f"Actions: {len(action_trace)}")
        else:
            # Interactive mode: prompt for tasks
            print("Enter a task or 'quit' to exit.\n")
            while True:
                user_task = input("Task: ").strip()
                if user_task.lower() in ["quit", "exit", ""]:
                    break
                await run_cognitive_loop(user_task, collection, mcp_host)
                print(f"Actions: {len(action_trace)}\n")
    except (KeyboardInterrupt, EOFError):
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Kernel execution failed: {e}")
        raise click.ClickException(f"Kernel execution failed: {e}")
    finally:
        await mcp_host.shutdown()


@click.command()
@click.argument("task", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(task: str | None, verbose: bool) -> None:
    """Winston Chapter 3: Hierarchical Capability Discovery.

    Execute a cognitive task or run in interactive mode.

    TASK is the task description to execute. If omitted, runs interactively.

    Examples:
        python -m chapter03.kernel "What tools are available for memory operations?"
        python -m chapter03.kernel --verbose "Create a memory of today's events"
        python -m chapter03.kernel  # Interactive mode
    """
    if verbose:
        logger.add(sys.stderr, level="DEBUG")

    try:
        asyncio.run(main(task))
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
    except Exception as e:
        logger.error(f"CLI execution failed: {e}")
        raise click.ClickException(f"CLI execution failed: {e}")


if __name__ == "__main__":
    cli()
