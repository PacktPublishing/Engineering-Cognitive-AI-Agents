---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
response_format:
  type: json_schema
  json_schema:
    name: relationships
    strict: true
    schema:
      type: object
      properties:
        relationships:
          type: array
          items:
            type: object
            properties:
              source:
                type: string
                description: "The source entity of the relationship"
              relationship:
                type: string
                description: "The type of relationship between the entities"
              target:
                type: string
                description: "The target entity of the relationship"
            required:
              - source
              - relationship
              - target
            additionalProperties: false
      required:
        - relationships
      additionalProperties: false
---

I identify relationships between the given entities based on the provided text.

I ensure that:

1. The entire output is a valid JSON array.
2. Each relationship is represented as a separate object within the array.
3. Each object has three keys: 'source' for the source entity, 'relationship' for the type of relationship, and 'target' for the target entity.
4. The 'source' and 'target' keys contain the exact entity names as provided in the input.
5. The 'relationship' key contains a concise description of the relationship between the entities.
6. The output is properly formatted with appropriate indentation and line breaks for readability.

I process the entire input text and include all identified relationships in the output JSON array.

[INPUT TEXT]:
{{ text }}

[RELATIONSHIPS]:
