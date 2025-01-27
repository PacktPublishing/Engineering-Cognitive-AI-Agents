# Agent Implementation Guidelines

## 1. Core Design Philosophy

The fundamental principle of specialist agent design is that **cognitive logic lives in the prompt**. The language model, guided by a carefully crafted system prompt, performs all analysis and decision-making. Tools simply represent the concrete actions available based on that reasoning.

## 2. Core Requirements

```python
class SpecialistAgent(BaseAgent):
    """Each specialist agent must:
    1. Inherit from BaseAgent
    2. Have a clear, focused cognitive role
    3. Provide configuration YAML
    4. Maintain clean separation of concerns
    """
```

## 3. Configuration (YAML)

```yaml
# required: config/agents/{agent_id}.yaml
id: agent_id # Unique identifier
model: gpt-4 # Model to use
system_prompt: | # Core intelligence
  You are a {SPECIALIST} agent in a Society of Mind system.

  Your ONLY role is to {SPECIFIC_COGNITIVE_FUNCTION}.

  Given input, analyze:
  1. {KEY_ANALYSIS_POINTS}
  2. {DECISION_CRITERIA}

  Based on your analysis, select the appropriate action:
  - Use tool_a when {CONDITION_A}
  - Use tool_b when {CONDITION_B}

  Always explain your reasoning before taking action.

temperature: 0.7 # Optional parameters
stream: true
```

## 4. Tool Implementation

```python
from pydantic import BaseModel, Field
from winston.core.tools import Tool

# A. Define Request/Response Models
class ActionRequest(BaseModel):
    """Each tool needs input validation."""
    content: str = Field(
        description="Content to analyze"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context"
    )

class ActionResponse(BaseModel):
    """And structured output."""
    result: str = Field(
        description="Action results"
    )
    metadata: dict = Field(
        description="Additional metadata"
    )

# B. Implement Tool Handler(s)
async def handle_action(
    request: ActionRequest
) -> ActionResponse:
    """Implement concrete action logic only."""
    # ... tool implementation
    return ActionResponse(
        result="Action completed",
        metadata={"status": "success"}
    )

# C. Optional: Format Results
def format_result(
    result: ActionResponse
) -> str:
    """Format tool results for user display."""
    return f"Result: {result.result}"

# D. Create Tool Instance
action_tool = Tool(
    name="perform_action",
    description="Execute specific action based on LLM analysis",
    handler=handle_action,
    input_model=ActionRequest,
    output_model=ActionResponse,
    format_response=format_result  # Optional
)
```

## 5. Agent Implementation

```python
class SpecialistAgent(BaseAgent):
    """Each specialist performs a specific cognitive function."""

    def __init__(
        self,
        system: System,
        config: AgentConfig,
        paths: AgentPaths,
    ) -> None:
        super().__init__(system, config, paths)

        # Tools represent possible actions based on LLM reasoning
        self.system.register_tool(Tool(
            name="action_a",
            description="Take action A when analysis indicates X",
            handler=self._handle_action_a,
            input_model=ActionARequest,
            output_model=ActionAResponse
        ))

        self.system.register_tool(Tool(
            name="action_b",
            description="Take action B when analysis indicates Y",
            handler=self._handle_action_b,
            input_model=ActionBRequest,
            output_model=ActionBResponse
        ))

        # Grant self access to own tools
        self.system.grant_tool_access(
            self.id,
            ["action_a", "action_b"]
        )
```

## 6. Separation of Concerns

1. **System Prompt**

   - Defines the cognitive role and decision process
   - Specifies analysis criteria and decision logic
   - Establishes conditions for tool usage
   - Contains all reasoning patterns

2. **Language Model**

   - Performs all analysis and reasoning
   - Makes decisions based on prompt guidance
   - Explains reasoning before taking action
   - Selects appropriate tools based on analysis

3. **Tools**

   - Execute concrete actions only
   - Implement no decision logic
   - Process structured inputs
   - Return structured outputs
   - Format results for display (optional)

4. **Agent Class**
   - Inherits from BaseAgent
   - Registers available tools
   - Grants tool access
   - Provides no additional logic

The BaseAgent handles all core functionality:

- Message processing
- LLM interaction
- Tool execution
- Response streaming

This clean separation ensures that cognitive logic remains in the prompt/LLM layer while tools serve purely as action executors based on that reasoning.

## Anti-Pattern: "RPC-like" Control Flow

❌ **NEVER** use metadata or message fields to direct agent behavior like this:

```python
# WRONG: Using metadata as RPC-like control flow
message = Message(
    content="Some content",
    metadata={
        "type": "do_analysis",  # NO! This is not how we direct behavior
        "operation": "store",   # NO! This is not how we select actions
        "mode": "quick"        # NO! This is not how we control processing
    }
)
```

This approach:

- Bypasses the LLM's cognitive capabilities
- Creates brittle, procedural control flow
- Violates the core architectural principle that cognitive logic belongs in the prompt

## Key Principles

✅ **CRITICAL**: Cognitive Logic Lives in the Prompt

1. **Cognitive Logic in Prompt**

   - The system prompt defines the agent's cognitive role
   - LLM reasoning determines appropriate actions
   - Tools represent conclusions/decisions, not control flow

2. **Tools as Decision Points**

   - Each tool represents a possible conclusion from analysis
   - Tool parameters capture the details of the decision
   - Multiple tools represent distinct cognitive branches

3. **Clean Separation**
   - Prompt: Contains ALL cognitive logic and decision criteria
   - LLM: Performs analysis and selects appropriate action
   - Tools: Execute concrete actions based on LLM decisions
   - Metadata: Carries context, NOT control flow

## Remember

- If you find yourself using metadata or messages to control agent behavior, STOP
- If you're creating complex control flows between agents, STOP
- Return to the core principle: Cognitive logic lives in the prompt
- Let the LLM's reasoning, guided by the prompt, drive tool selection and action

This architectural principle ensures our agents remain truly cognitive rather than degrading into procedural RPC endpoints.

## 3. Core Specialist Pattern

The EpisodeAnalyst demonstrates the canonical pattern for specialist agents:

```python
# 1. Define a clear result model
class AnalysisResult(BaseModel):
    """Model representing the cognitive decision."""
    decision: bool = Field(description="Primary decision point")
    metadata: dict[str, Any] = Field(default_factory=dict)

class SpecialistAgent(BaseAgent):
    def __init__(self, system: AgentSystem, config: AgentConfig, paths: AgentPaths) -> None:
        super().__init__(system, config, paths)

        # 2. Register single focused tool
        tool = Tool(
            name="report_analysis",
            description="Report analysis results",
            handler=self._handle_report,
            input_model=AnalysisResult,  # Same model for input/output
            output_model=AnalysisResult,
        )
        self.system.register_tool(tool)
        self.system.grant_tool_access(self.id, [tool.name])

    async def _handle_report(self, result: AnalysisResult) -> AnalysisResult:
        """Simple pass-through handler."""
        return result
```

Key aspects of this pattern:

1. Single, focused Pydantic result model
2. Inherits from BaseAgent (provides process() method)
3. Registers one primary tool using the result model
4. Minimal handler implementation
5. Clear cognitive role in config YAML
6. No additional processing logic - all intelligence in prompt

This pattern ensures:

- Clean separation between cognitive logic (prompt) and action (tool)
- Structured decision capture via Pydantic
- Minimal boilerplate code
- Clear single responsibility

## 7. Workspace Management

Each agent in the system can maintain both private and shared workspaces:

1. **Private Workspace**

   - Agent-specific "scratch pad" for processing
   - Maintains individual cognitive context
   - Independent operation without interference
   - Used for agent-specific memory and understanding
   - Accessed through `self.workspace_path`

2. **Shared Workspace**
   - Enables multi-agent collaboration
   - Passed via message metadata as `shared_workspace`
   - Facilitates complex cognitive operations
   - Preserves boundaries between agent processes
   - Accessed through `message.metadata["shared_workspace"]`

Example usage:

```python
async def process(
    self,
    message: Message,
) -> AsyncIterator[Response]:
    """Process in both private and shared contexts."""
    # Get both workspaces
    private_workspace, shared_workspace = self._get_workspaces(message)

    # Use private workspace for agent-specific processing
    # Use shared workspace for collaborative work

    # Update both workspaces with new insights
    await self._update_workspaces(
        message,
        private_update_template="...",
        shared_update_template="...",
    )
```

Key principles:

1. **Workspace Initialization**

   - Private workspaces are automatically initialized
   - Templates can customize initial structure
   - Markdown format enables easy inspection

2. **Context Management**

   - Private workspace maintains agent-specific memory
   - Shared workspace enables collective intelligence
   - Both persist across sessions

3. **Update Process**

   - Selective updates preserve context
   - Maintain relationships between information
   - Keep temporal continuity
   - Ensure coherence across sections

4. **Best Practices**
   - Use private workspace for agent-specific processing
   - Share only relevant insights in shared workspace
   - Maintain clean separation between private and shared context
   - Use templates to standardize workspace structure
   - Keep workspaces focused and organized

## 8. Agency-Level Workspace Patterns

In the Society of Mind paradigm, agents form hierarchical groups called "agencies", where coordinator agents manage specialist sub-agents. This structure requires specific workspace patterns:

1. **Agency Private Workspace**

   - Each coordinator maintains an agency-level private workspace
   - Accessible to both coordinator and its sub-agents
   - Functions as shared context within the agency
   - Preserves agency boundaries in multi-agency systems
   - Accessed through coordinator's `self.workspace_path`

2. **Workspace Access Pattern**

```python
class CoordinatorAgent(BaseAgent):
    """Coordinator pattern with agency workspace."""

    def __init__(self, system: System, config: AgentConfig, paths: AgentPaths) -> None:
        super().__init__(system, config, paths)

        # Initialize sub-agents with agency workspace
        self.specialist_a = SpecialistAgent(
            system,
            config,
            paths,
            agency_workspace=self.workspace_path,  # Pass coordinator's workspace
        )
        self.specialist_b = SpecialistAgent(
            system,
            config,
            paths,
            agency_workspace=self.workspace_path,
        )

    async def process(self, message: Message) -> AsyncIterator[Response]:
        """Process using agency-wide context."""
        # Enhance message with agency context
        agency_message = Message(
            content=message.content,
            metadata={
                **message.metadata,
                "agency_workspace": self.workspace_path,  # Make workspace available
            },
        )

        # Sub-agents can now access agency workspace
        async for response in self.specialist_a.process(agency_message):
            yield response
```

3. **Agency Context Management**

   - Coordinator owns and initializes workspace
   - Sub-agents read and contribute to workspace
   - Maintains cognitive continuity within agency
   - Enables specialist collaboration through shared context

4. **Best Practices**

   - Use agency workspace for agency-specific knowledge
   - Keep agency context separate from global shared workspaces
   - Allow sub-agents to contribute insights to agency workspace
   - Use coordinator to manage workspace updates
   - Maintain clear agency boundaries

5. **Multi-Level Context**
   ```
   System
   ├── Global Shared Workspace
   └── Agencies
       ├── Agency A
       │   ├── Agency Private Workspace (Coordinator + Sub-agents)
       │   └── Sub-agent Private Workspaces (Optional)
       └── Agency B
           ├── Agency Private Workspace
           └── Sub-agent Private Workspaces
   ```

This pattern enables:

- Clear cognitive boundaries between agencies
- Efficient collaboration within agencies
- Hierarchical context management
- Specialized knowledge sharing
- Society of Mind principles in practice
