#!/usr/bin/env python3
"""
Winston Intent Tools - Chapter 2 demonstration tools
Chapter 2: Intent-Based Action System

Provides mock implementations of communication tools for testing the intent system.
These are chapter-specific examples that demonstrate the intent matching capabilities.
"""

from typing import Any
from loguru import logger
from .tool_registry import register_tool

# OpenAI tool schemas for intent database indexing - Chapter 2 specific examples
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "send_email": {
        "type": "function",
        "name": "send_email",
        "description": "Send an email message to communicate with colleagues",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Email address of recipient",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Email message content"},
            },
            "required": ["recipient", "subject", "message"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "send_slack": {
        "type": "function",
        "name": "send_slack",
        "description": "Send a Slack message to communicate with colleagues",
        "parameters": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "Slack channel or user"},
                "message": {"type": "string", "description": "Slack message content"},
            },
            "required": ["channel", "message"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "send_teams": {
        "type": "function",
        "name": "send_teams",
        "description": "Send a Microsoft Teams message to communicate with colleagues",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Teams user or channel"},
                "message": {"type": "string", "description": "Teams message content"},
            },
            "required": ["recipient", "message"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


@register_tool
@logger.catch
def send_email(recipient: str, subject: str, message: str) -> str:
    """Mock email sending tool for demonstration.

    Parameters
    ----------
    recipient : str
        Email address of recipient.
    subject : str
        Email subject line.
    message : str
        Email message content.

    Returns
    -------
    str
        Mock result of email sending operation.

    Examples
    --------
    >>> result = send_email("test@example.com", "Test", "Hello")
    >>> "sent" in result.lower()
    True
    """
    result = f"Email sent to {recipient} with subject '{subject}'"
    logger.info(f"Mock email tool executed: {result}")
    logger.debug(f"Email content: {message[:50]}{'...' if len(message) > 50 else ''}")
    return result


@register_tool
@logger.catch
def send_slack(channel: str, message: str) -> str:
    """Mock Slack messaging tool for demonstration.

    Parameters
    ----------
    channel : str
        Slack channel or user.
    message : str
        Slack message content.

    Returns
    -------
    str
        Mock result of Slack messaging operation.

    Examples
    --------
    >>> result = send_slack("#team", "Hello team")
    >>> "sent" in result.lower()
    True
    """
    result = f"Slack message sent to {channel}"
    logger.info(f"Mock Slack tool executed: {result}")
    logger.debug(f"Slack content: {message[:50]}{'...' if len(message) > 50 else ''}")
    return result


@register_tool
@logger.catch
def send_teams(recipient: str, message: str) -> str:
    """Mock Teams messaging tool for demonstration.

    Parameters
    ----------
    recipient : str
        Teams user or channel.
    message : str
        Teams message content.

    Returns
    -------
    str
        Mock result of Teams messaging operation.

    Examples
    --------
    >>> result = send_teams("user@company.com", "Hello")
    >>> "sent" in result.lower()
    True
    """
    result = f"Teams message sent to {recipient}"
    logger.info(f"Mock Teams tool executed: {result}")
    logger.debug(f"Teams content: {message[:50]}{'...' if len(message) > 50 else ''}")
    return result
