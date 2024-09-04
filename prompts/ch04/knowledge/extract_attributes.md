---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 200
---

# Extract Attributes (NLP)

Given the following text and extracted entities, identify attributes for each entity. Respond with a JSON object where keys are entity names and values are objects of attribute-value pairs.

Text: {{ text }}

Entities: {{ entities }}

Attributes:
