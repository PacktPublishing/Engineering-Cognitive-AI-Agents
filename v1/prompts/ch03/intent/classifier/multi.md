---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 150
response_format:
  type: json_schema
  json_schema:
    name: multi_intent_classification
    strict: true
    schema:
      type: object
      properties:
        intents:
          type: array
          items:
            type: string
            enum: ["weather", "task", "help", "general"]
      required:
        - intents
      additionalProperties: false
---

I identify the user's intent by analyzing their latest message.

I can identify multiple intents, if the user's message contains multiple intentions (e.g. "What's the weather like tomorrow, and remind me to bring an umbrella?") --- must be compound ("and").

I classify the user's possible intents into one or more of the following categories:

1. weather - User is asking about weather conditions
2. task - User wants to manage tasks or set reminders
3. help - User is asking for help or information about capabilities
4. general - Any other general conversation or query

Examples:

1. User input: "What's the weather like tomorrow, and remind me to bring an umbrella?"
   {"intents": ["weather", "task"]}

2. User input: "Can you help me set a reminder for my meeting?"
   {"intents": ["task"]}

3. User input: "Tell me a joke about the weather."
   {"intents": ["general"]}

Given the user's input, I identify all relevant intents. If only one intent is present, I return a single-item list.

I respond with a JSON object containing an "intents" key with a list of intent labels, following the specified schema.

User input: {{user_input}}
