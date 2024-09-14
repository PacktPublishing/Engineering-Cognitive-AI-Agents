---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
---

# Extract Entities (NLP)

Extract entities from the following text. Respond with a JSON array of objects, where each object has a "name" and a "type". Only include entities that are explicitly mentioned in the text.

Text: {{ text }}

Entities:
