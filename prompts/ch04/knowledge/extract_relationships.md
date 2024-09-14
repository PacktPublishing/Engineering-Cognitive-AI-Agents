---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
---

# Extract Relationships (NLP)

Given the following text and extracted entities, identify relationships between the entities. Respond with a JSON array of objects, where each object has "source", "relationship", and "target" fields.

Text: {{ text }}

Entities: {{ entities }}

Relationships:
