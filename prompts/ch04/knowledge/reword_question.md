---
model: gpt-4o-mini
temperature: 0.7
max_tokens: 8192
response_format:
  type: json_schema
  json_schema:
    name: reworded_questions
    strict: true
    schema:
      type: object
      properties:
        reworded_questions:
          type: array
          items:
            type: string
            description: "A reworded version of the original question"
      required:
        - reworded_questions
      additionalProperties: false
---

I rephrase the [ORIGINAL QUESTION] provided in {{ num_rewordings }} distinct ways, ensuring the meaning and context remain intact.

I strive for originality and steer clear of redundancy and typical synonyms.

I make certain that the core meaning of the rephrased questions is preserved.

I provide the reworded questions in a JSON array format, with each question as a separate string item.

# Example

[ORIGINAL QUESTION]:
What is the capital of Italy?

[REWORDED QUESTIONS]:
{
"reworded_questions": [
"Which city serves as the capital of Italy?",
"Can you name the capital city of Italy?",
"What is the name of Italy's capital?"
]
}

# Input

[ORIGINAL QUESTION]:
{{ question }}

[REWORDED QUESTIONS]:
