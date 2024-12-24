# Design Note: Communication Patterns in Winston's Architecture

## Motivation

Our current tightly-coupled agent architecture serves core cognitive operations well but limits flexibility for system-wide events and external integrations. We need an architecture that maintains reliability for critical cognitive processes while enabling looser coupling for notifications and service integration.

## Proposed Architecture

We propose three distinct communication patterns, each optimized for specific use cases:

### 1. Direct Communication (Current)

For core cognitive operations requiring guaranteed delivery and strict ordering.

```python
async def process(self, message: Message) -> AsyncIterator[Response]:
    """Direct agent-to-agent communication."""
    return await self.system.route_message(recipient_id, message)
```

**Use Cases:**

- Memory operations
- Reasoning chains
- Planning sequences
- Any operation requiring immediate response or strict ordering

**Key Properties:**

- Guaranteed delivery
- Synchronous operation
- Clear control flow
- Strong typing
- Error propagation

### 2. Event Bus (New)

For system-wide notifications and state changes where loose coupling is beneficial.

```python
class EventBus:
    """Decoupled event distribution system."""

    async def publish(self, topic: str, event: Event) -> None:
        """Distribute event to all subscribers."""

    def subscribe(self, topic: str, handler: callable) -> None:
        """Register interest in topic."""
```

**Use Cases:**

- Preference changes
- Context shifts
- Learning events
- State updates
- Cross-cutting concerns

**Key Properties:**

- One-to-many distribution
- Asynchronous processing
- Loose coupling
- Optional handling
- Runtime subscription

### 3. Tool Registry (Enhanced)

For external service integration and protocol abstraction.

```python
class ToolRegistry:
    """Flexible service integration layer."""

    async def execute(
        self,
        tool_name: str,
        implementation: str,
        **params
    ) -> Any:
        """Execute specific tool implementation."""
```

**Use Cases:**

- API calls
- External services
- Protocol-specific implementations
- Pluggable backends

**Key Properties:**

- Implementation abstraction
- Protocol independence
- Runtime selection
- Clear interface contracts
- Service isolation

## Implementation Strategy

### Phase 1: Event Bus Integration

1. Implement basic EventBus with publish/subscribe
2. Identify non-critical notifications to migrate
3. Add event bus support to AgentSystem
4. Create decorators for easy subscription

```python
class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(set)

    async def publish(self, topic: str, event: Event) -> None:
        for handler in self._subscribers[topic]:
            await handler(event)

    def subscribe(self, topic: str, handler: callable) -> None:
        self._subscribers[topic].add(handler)

# Usage
@subscribe("preference_changed")
async def handle_preference_change(event: Event) -> None:
    """React to preference changes."""
```

### Phase 2: Enhanced Tool Registry

1. Extend current Tool protocol for multiple implementations
2. Add implementation registry
3. Create adapters for common protocols (REST, gRPC)
4. Implement runtime implementation selection

```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._implementations: dict[str, dict[str, callable]] = {}

    def register_implementation(
        self,
        tool_name: str,
        impl_name: str,
        implementation: callable
    ) -> None:
        """Register specific implementation."""
```

### Phase 3: System Integration

1. Update AgentSystem to support all patterns
2. Create clear guidelines for pattern selection
3. Migrate appropriate interactions to new patterns
4. Add monitoring and debugging support

```python
class AgentSystem:
    def __init__(self):
        self.event_bus = EventBus()
        self.tool_registry = ToolRegistry()
        self._agents: dict[str, Agent] = {}
```

## Migration Guidelines

When choosing a communication pattern:

1. **Use Direct Communication when:**

   - Operation is part of core cognitive process
   - Immediate response is required
   - Strong typing and error handling needed
   - Operation ordering is critical

2. **Use Event Bus when:**

   - Multiple agents might be interested
   - Asynchronous processing is acceptable
   - Loose coupling is beneficial
   - Optional handling is appropriate

3. **Use Tool Registry when:**
   - Integrating external services
   - Multiple implementations might exist
   - Protocol abstraction is needed
   - Implementation might change at runtime

## Success Metrics

1. **Reduced Coupling**

   - Fewer direct dependencies between agents
   - Easier addition of new capabilities
   - Simpler testing and mocking

2. **Improved Flexibility**

   - Multiple implementation support
   - Runtime behavior modification
   - Easier integration of new services

3. **Maintained Reliability**
   - Core cognitive operations unaffected
   - Clear error handling
   - Consistent behavior

## Next Steps

1. Implement basic EventBus
2. Identify initial events to migrate
3. Create adapters for current tools
4. Update documentation and examples
5. Add monitoring and debugging support

## Open Questions

1. How to handle event ordering when needed?
2. Should we support event persistence?
3. How to manage tool versioning?
4. What monitoring capabilities are needed?

## References

- Current agent implementation
- Tool protocol definition
- System configuration patterns
- Message and Response models

This design note provides a comprehensive guide for implementing the new communication patterns while maintaining the stability of our core cognitive operations. It outlines clear phases for incremental implementation and provides specific guidelines for choosing between patterns.
