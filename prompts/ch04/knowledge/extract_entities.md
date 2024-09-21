---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
response_format:
  type: json_schema
  json_schema:
    name: entities
    strict: true
    schema:
      type: object
      properties:
        entities:
          type: array
          items:
            type: object
            properties:
              name:
                type: string
                description: "The name of the entity"
              type:
                type: string
                description: "The type of the entity"
            required:
              - name
              - type
            additionalProperties: false
      required:
        - entities
      additionalProperties: false
---

I extract entities from the given text.

I generate a JSON array of objects, where each object represents an entity with two properties: "name" and "type".

I will ensure that:

1. The entire output is a valid JSON object containing an array named "entities".
2. Each entity is represented as a separate object within the "entities" array.
3. The "name" property contains the full name or identifier of the entity as mentioned in the text.
4. The "type" property specifies the category or classification of the entity.
5. I only include entities that are explicitly mentioned in the given text.
6. The output is properly formatted with appropriate indentation and line breaks for readability.

I will process the entire input text and include all relevant entities found in the output JSON array.

[INPUT TEXT]:
{{ text }}

[ENTITIES]:
