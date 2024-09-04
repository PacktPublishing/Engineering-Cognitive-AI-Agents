---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 800
top_p: 0.95
frequency_penalty: 0
response_format_type: text
---

# Winston's Multi-Intent Synthesis Prompt

You have received multiple responses to a user's query.
Synthesize these responses into a single, coherent
answer that addresses all aspects of the user's
request. Be concise and maintain your authentic tone
and style.

[PREVIOUS RESPONSES]:
{{ previous_responses }}
