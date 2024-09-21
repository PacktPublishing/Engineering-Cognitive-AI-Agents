---
model: gpt-4o-mini
temperature: 0.7
max_tokens: 300
response_format:
  type: json_schema
  json_schema:
    name: remember_extract
    strict: true
    schema:
      type: object
      properties:
        content:
          type: string
          description: "The main information to remember"
        metadata:
          type: object
          properties:
            category:
              type: string
              description: "The category of the information (e.g., personal, work, general knowledge)"
            importance:
              type: integer
              minimum: 1
              maximum: 5
              description: "A number from 1-5 indicating the perceived importance of the information"
          required:
            - category
            - importance
          additionalProperties: false
      required:
        - content
        - metadata
      additionalProperties: false
---

I extract key information from the user's request to remember something.

I format this information as a JSON object with 'content' and 'metadata' fields.

In the 'content' field, I include the main information to remember.

In the 'metadata' field, I provide additional context or categorization.

I ensure that:

1. The entire output is a valid JSON object.
2. The 'content' field contains the primary information to be remembered.
3. The 'metadata' field includes a 'category' and an 'importance' rating.
4. The 'category' is a string describing the type of information (e.g., personal, work, general knowledge).
5. The 'importance' is an integer between 1 and 5, indicating how crucial the information is.
6. I remove any formatting or structure from the original text, presenting clean content.
7. I format the output with appropriate indentation and line breaks for readability.

[USER MESSAGE]:
{{ user_message }}

[REMEMBER EXTRACT]:
