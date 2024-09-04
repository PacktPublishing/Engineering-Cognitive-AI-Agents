---
model: gpt-4o-mini
temperature: 0.7
max_tokens: 300
---

# Winston remembers something

The user requests that you remember something. Extract
the key information and format it as a JSON object with
'content' and 'metadata' fields. The 'content' should
be the main information to remember, and 'metadata' can
include any additional context or categorization.

User message: {{ user_message }}

Response format:
{
"content": "The main information to remember",
"metadata": {
"category": "The category of the information (e.g., personal, work, general knowledge)",
"importance": "A number from 1-5 indicating the perceived importance of the information",
}
}

Extracted information:
