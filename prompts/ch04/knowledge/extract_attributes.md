---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
response_format:
  type: json_schema
  json_schema:
    name: attributes
    strict: true
    schema:
      type: object
      properties:
        attributes:
          type: array
          items:
            type: object
            properties:
              entity:
                type: string
              properties:
                type: array
                items:
                  type: object
                  properties:
                    key:
                      type: string
                    value:
                      type: string
                  required:
                    - key
                    - value
                  additionalProperties: false
            required:
              - entity
              - properties
            additionalProperties: false
      required:
        - attributes
      additionalProperties: false
---

I extract attributes for each given entity based on the provided text.

I generate a JSON object with an "entities" array. Each item in the array represents an entity and its properties.

I ensure that:

1. The entire output is a valid JSON object.
2. The main object contains an "entities" array.
3. Each item in the "entities" array is an object with "entity" and "properties" keys.
4. The "entity" value is a string with the entity's name.
5. The "properties" value is an array of objects, each with "key" and "value" fields.
6. Both "key" and "value" are strings.
7. I only include attributes that are clearly implied or stated in the given text.
8. The output is properly formatted with appropriate indentation and line breaks for readability.

I process the entire input text and include all relevant attributes for each entity in the output JSON object.

[INPUT TEXT]:
{{ text }}

[ENTITIES]:
{{ entities }}

[ATTRIBUTES]:
