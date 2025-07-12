"""Manages a collection of Model Context Protocol (MCP) servers.

This module provides the MCPHost class, which is responsible for reading a
configuration file, launching and managing the lifecycle of stdio-based
and HTTP-based servers, and providing a unified interface to introspect
all connected servers and retrieve their tool schemas.
"""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from loguru import logger
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


class MCPHost:
    """Manages a collection of MCP servers defined in a configuration file.

    Parameters
    ----------
    config_path : Path
        The path to the MCP configuration JSON file.

    Attributes
    ----------
    config : dict[str, Any]
        The loaded configuration data.
    sessions : dict[str, ClientSession]
        A dictionary mapping server names to their client session instances.
    """

    def __init__(self, config_path: Path):
        """Initialize the MCPHost with a given configuration."""
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()

    async def startup(self) -> None:
        """Load configuration and initialize all defined MCP servers."""
        logger.info(f"Starting MCP Host from config: {self.config_path}")
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load or parse MCP config: {e}")
            raise

        servers_map = self.config.get("mcpServers", {})
        for name, config in servers_map.items():
            server_config = config.copy()
            server_config["name"] = name
            # If "enabled" is not specified, assume it is true.
            if server_config.get("enabled", True):
                await self._initialize_server(server_config)

        logger.info(f"MCP Host started with {len(self.sessions)} servers.")

    async def _create_stdio_session(
        self, name: str, config: dict[str, Any]
    ) -> ClientSession:
        """Create a client session for an stdio-based MCP server."""
        command = config.get("command")
        if not command or not isinstance(command, str):
            raise ValueError(
                f"Stdio server '{name}' config missing or has invalid 'command' (must be a string)"
            )

        args = config.get("args", [])
        if not isinstance(args, list):
            raise ValueError(f"Stdio server '{name}' config 'args' must be a list")

        params = StdioServerParameters(
            command=command,
            args=args,
            env=config.get("env"),
        )
        logger.debug(f"Connecting to stdio server '{name}' with command: {command}")

        read, write = await self._exit_stack.enter_async_context(stdio_client(params))
        session = ClientSession(read, write)
        await self._exit_stack.enter_async_context(session)
        await session.initialize()
        return session

    async def _create_http_session(
        self, name: str, config: dict[str, Any]
    ) -> ClientSession:
        """Create a client session for an HTTP-based MCP server."""
        url = config.get("url")
        if not url:
            raise ValueError(f"HTTP server '{name}' config missing 'url'")

        logger.debug(f"Connecting to http server '{name}' at {url}")
        read, write, _ = await self._exit_stack.enter_async_context(
            streamablehttp_client(url)
        )
        session = ClientSession(read, write)
        await self._exit_stack.enter_async_context(session)
        await session.initialize()
        return session

    async def _initialize_server(self, server_config: dict[str, Any]) -> None:
        """Initialize a single MCP server based on its configuration."""
        server_name = server_config.get("name")
        server_type = "stdio"  # Assuming stdio for now as per book context
        command = server_config.get("command")

        if not all([server_name, command]):
            logger.warning(f"Skipping server with incomplete config: {server_config}")
            return

        assert isinstance(server_name, str)

        logger.debug(f"Initializing server '{server_name}' of type '{server_type}'")
        try:
            session: ClientSession | None = None
            if server_type == "stdio":
                session = await self._create_stdio_session(
                    server_name, server_config
                )
            elif server_type == "http":
                session = await self._create_http_session(
                    server_name, server_config
                )
            else:
                logger.warning(
                    f"Unsupported server type '{server_type}' for '{server_name}'"
                )
                return

            if session:
                self.sessions[server_name] = session
                logger.success(
                    f"Successfully initialized and connected to server '{server_name}'"
                )

        except Exception as e:
            logger.opt(exception=True).error(
                f"Failed to initialize server '{server_name}': {e}"
            )

    async def get_all_tools(self) -> dict[str, list[Tool]]:
        """Retrieve all tools from all connected servers.

        Returns
        -------
        dict[str, list[Tool]]
            A dictionary mapping server names to a list of their available tools.
            If a server fails, its list will be empty.
        """
        all_tools: dict[str, list[Tool]] = {}
        for name, session in self.sessions.items():
            try:
                logger.debug(f"Listing tools for server '{name}'...")
                tools_response = await session.list_tools()
                all_tools[name] = tools_response.tools
                logger.info(f"Found {len(all_tools[name])} tools for server '{name}'")
            except Exception:
                logger.opt(exception=True).error(f"Failed to get tools from '{name}'")
                all_tools[name] = []
        return all_tools

    async def shutdown(self) -> None:
        """Close all client sessions and their underlying transports."""
        logger.info(f"Shutting down MCP Host and {len(self.sessions)} sessions...")
        await self._exit_stack.aclose()
        self.sessions.clear()
        logger.info("MCP Host shut down successfully.")
