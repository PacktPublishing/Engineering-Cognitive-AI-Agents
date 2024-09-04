---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 50
top_p: 0.95
frequency_penalty: 0
response_format_type: text
---

# Winston's User Intent Classifier Prompt

The user's possible intents are:

1. weather - User is asking about weather conditions
2. task - User wants to manage tasks or set reminders
3. help - User is asking for help or information about capabilities
4. general - Any other general conversation or query

Given the user's input, classify the user's intent.

Respond with ONLY the intent label (weather, task, help, or general).
