#!/usr/bin/env python3
"""
Winston Tool Registry - A simple, centralized registry for local Python tools.

This module provides a mechanism to register and execute functions as tools,
decoupling the tool-calling logic from the agent's core reasoning. This is
the backward-compatible implementation required by Chapter 2.
"""

from __future__ import annotations

from typing import Any, Callable

from loguru import logger

# The internal registry for all decorated tool functions
_TOOL_REGISTRY: dict[str, Callable[..., Any]] = {}


def register_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator to register a function as a tool.

    Parameters
    ----------
    func : Callable[..., Any]
        The function to be registered as a tool.

    Returns
    -------
    Callable[..., Any]
        The original function, unmodified.
    """
    tool_name = func.__name__
    _TOOL_REGISTRY[tool_name] = func
    logger.debug(f"Registered tool: '{tool_name}'")
    return func


@logger.catch
def execute_tool_function(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Look up and execute a registered tool function by name.

    Parameters
    ----------
    tool_name : str
        The name of the tool to execute.
    arguments : dict[str, Any]
        A dictionary of arguments to pass to the tool function.

    Returns
    -------
    Any
        The return value from the executed tool function.

    Raises
    ------
    KeyError
        If the requested tool_name is not found in the registry.
    """
    if tool_name not in _TOOL_REGISTRY:
        logger.error(f"Tool '{tool_name}' not found in registry.")
        raise KeyError(f"Tool '{tool_name}' is not a registered function.")

    logger.info(f"Executing local tool: '{tool_name}'")
    tool_function = _TOOL_REGISTRY[tool_name]
    return tool_function(**arguments)
