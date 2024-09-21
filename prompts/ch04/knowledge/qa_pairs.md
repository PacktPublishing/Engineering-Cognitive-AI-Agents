---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
response_format:
  type: json_schema
  json_schema:
    name: qa_pairs
    strict: true
    schema:
      type: object
      properties:
        qa_pairs:
          type: array
          items:
            type: object
            properties:
              q:
                type: string
                description: "The full question text"
              a:
                type: string
                description: "The full answer text"
            required:
              - q
              - a
            additionalProperties: false
      required:
        - qa_pairs
      additionalProperties: false
---

I derive various questions (along with their answers) that the given text implies.

I generate question-answer pairs as JSON based on the given text.

Each object will have two keys: 'q' for the question and 'a' for the answer.

I will ensure that:

1. The entire output is a valid JSON array.
2. Each question-answer pair is represented as a separate object within the array.
3. The 'q' key contains the full question text.
4. The 'a' key contains the full answer text.
5. Any formatting or structure from the original text is removed, presenting clean question and answer strings.
6. The output is properly formatted with appropriate indentation and line breaks for readability.

I process the entire input text and include all question-answer pairs found in the output JSON array.

[INPUT TEXT]:
{{ input_text }}

[QA PAIRS]:
