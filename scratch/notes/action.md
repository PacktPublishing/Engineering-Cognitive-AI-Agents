What is wrong with the following implementation?

```python
class ActionAgent(BaseAgent):
    """Agent focused on taking conc
rete actions through tool usage."""

    def __init__(self, system: System, config: AgentConfig, paths: AgentPaths) -> None:
        super().__init__(system, config, paths)

        # Connect to memory system
        self.memory_coordinator = system.get_agent("memory_coordinator")

        # Register and gain access to basic tools
        self.system.register_tool(Tool(
            name="search_files",
            description="Search for files matching pattern",
            handler=self._handle_file_search,
            input_model=FileSearchRequest,
            output_model=FileSearchResponse
        ))

        self.system.register_tool(Tool(
            name="read_file",
            description="Read contents of specified file",
            handler=self._handle_file_read,
            input_model=FileReadRequest,
            output_model=FileReadResponse
        ))

        self.system.grant_tool_access(self.id, ["search_files", "read_file"])

    async def process(self, message: Message) -> AsyncIterator[Response]:
        """Process input and take appropriate actions."""

        # 1. Analyze situation using memory context
        workspace = await self.memory_coordinator.get_workspace(message)

        # 2. Determine required actions
        async for response in self.generate_streaming_response(
            Message(
                content=message.content,
                metadata={
                    "workspace": workspace,
                    "available_tools": self.list_available_tools()
                }
            )
        ):
            if response.metadata.get("tool_call"):
                # Execute tool and handle results
                tool_result = await self.execute_tool(
                    response.metadata["tool_name"],
                    response.metadata["tool_args"]
                )

                # Update memory with results
                await self.memory_coordinator.update_workspace(
                    message,
                    tool_result
                )

            yield response
```

---

This implementation has several issues that violate our core architectural principles:

1. **Cognitive Logic in Code**: The agent is making decisions about tool usage in code rather than through the system prompt. The LLM should be analyzing the situation and determining what tools to use - all cognitive decisions should live in the prompt.

2. **Direct Memory Access**: The agent directly calls the memory coordinator rather than going through the system's message routing. This creates tight coupling and bypasses our established communication patterns.

3. **Mixed Responsibilities**: The agent is trying to handle both cognitive processing (analyzing situations) and mechanical operations (executing tools) in the same method. These should be cleanly separated.

Here's how it should be implemented:

```python
class ActionAgent(BaseAgent):
    """Agent focused on taking concrete actions through tool usage."""

    def __init__(self, system: System, config: AgentConfig, paths: AgentPaths) -> None:
        super().__init__(system, config, paths)

        # Register tools
        self.system.register_tool(Tool(
            name="search_files",
            description="Search for files matching pattern",
            handler=self._handle_file_search,
            input_model=FileSearchRequest,
            output_model=FileSearchResponse
        ))

        self.system.register_tool(Tool(
            name="read_file",
            description="Read contents of specified file",
            handler=self._handle_file_read,
            input_model=FileReadRequest,
            output_model=FileReadResponse
        ))

        # Grant self access to tools
        self.system.grant_tool_access(self.id, ["search_files", "read_file"])

```

And the system prompt would handle the cognitive logic:

```yaml
id: action_agent
model: gpt-4
system_prompt: |
  You are an Action specialist in a Society of Mind system.
  Your role is to analyze situations and determine appropriate actions.

  Given input, analyze:
  1. What actions are needed
  2. Which tools best accomplish those actions
  3. What order tools should be used in

  Available tools:
  - search_files: Search for files matching a pattern
  - read_file: Read contents of a specific file

  For each action needed:
  1. Explain your reasoning
  2. Select appropriate tool
  3. Provide required parameters

  Always consider:
  - Most efficient sequence of actions
  - Required information from each step
  - How results should be used

  Remember: Focus on concrete actions that accomplish the goal.
```

Key improvements:

1. **Cognitive Logic in Prompt**: All decisions about what tools to use and when are handled by the LLM through the system prompt.

2. **Clean Separation**: The agent class only handles tool registration and access - all cognitive processing happens through the standard `process()` method inherited from `BaseAgent`.

3. **System-Managed Communication**: Memory access and tool execution happen through the system's standard message routing and tool management.

4. **Clear Responsibilities**: The agent focuses purely on its role of taking actions through tools, with the LLM handling all decision-making about when and how to use those tools.

This revised implementation better follows our core principles:

- Cognitive logic lives in the prompt
- Clear separation of concerns
- System-managed communication
- Tools for concrete actions only

The LLM can now focus on analyzing situations and selecting appropriate tools while the agent class provides clean mechanical implementation of those tools.

---

YES! Thank you for this crucial correction. You've highlighted fundamental architectural principles that I violated:

1. **Cognitive Logic in Prompt**: The LLM should make ALL decisions about tool usage, with its reasoning guided by the system prompt.

2. **Clean Separation**: The agent class should ONLY handle tool registration and mechanical operations.

3. **System-Managed Communication**: ALL interaction should go through proper system routing.

Let's extend this correct implementation to include a concrete example:

```python
# Tool definitions with clear input/output contracts
class FileSearchRequest(BaseModel):
    """Parameters for file search."""
    pattern: str = Field(description="Search pattern to match")
    directory: str = Field(description="Directory to search in")

class FileSearchResponse(BaseModel):
    """Results from file search."""
    matches: list[str] = Field(description="Matching file paths")

class FileReadRequest(BaseModel):
    """Parameters for file reading."""
    path: str = Field(description="Path of file to read")

class FileReadResponse(BaseModel):
    """Results from file read."""
    content: str = Field(description="File contents")
```

The tool handlers remain purely mechanical:

```python
async def _handle_file_search(
    self,
    request: FileSearchRequest
) -> FileSearchResponse:
    """Execute file search without cognitive processing."""
    matches = await self._search_files(
        request.pattern,
        request.directory
    )
    return FileSearchResponse(matches=matches)

async def _handle_file_read(
    self,
    request: FileReadRequest
) -> FileReadResponse:
    """Read file without cognitive processing."""
    content = await self._read_file(request.path)
    return FileReadResponse(content=content)
```

Would you like me to:

1. Expand the system prompt to better guide the LLM's reasoning about tool usage
2. Show how this agent would handle a specific task through the system
3. Something else?
