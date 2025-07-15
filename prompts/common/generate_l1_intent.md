You are an AI assistant tasked with generating a concise "action intent" for a single tool provided by an MCP (Model Context Protocol) server. Your goal is to create a high-level, user-centric phrase that captures the **purpose or outcome** of using this specific tool.

## Tool Information

**Tool Name:** `{{ tool.name }}`
**Tool Description:** `{{ tool.description }}`
**Tool Schema:**

```json
{% if tool.input_schema is defined and tool.input_schema is not none -%}
{{ tool.input_schema | tojson(indent=2) }}
{%- else -%}
{}
{%- endif %}
```

## Guidelines for Creating the Action Intent

1. **Focus on Outcome**: The intent should describe the result the user wants, not the technical process of the tool.
2. **Be User-Centric**: Frame the intent from the perspective of a user trying to solve a problem.
3. **Use Action-Oriented Language**: Start with a clear verb (e.g., "Create," "Find," "Analyze," "Manage").
4. **Be Abstract but Specific**: The intent should be abstract enough to potentially group similar tools, but specific enough to be clearly understood. For example, "Create a memory entity" is better than "Manage memory."

## Anti-Examples (What to Avoid)

- **Too Technical (describing the tool):** "Use the create_entities tool"
- **Too Vague (lacking clear action):** "Handle knowledge graph data"
- **Not User-Centric:** "Performs entity creation" (better: "Create a new entity in the knowledge graph")

## Task

Based on the tool information and guidelines provided, generate a single, clear, and actionable intent. The intent should be a short phrase in lowercase without any quotation marks or additional formatting.

**Generated Intent:**
