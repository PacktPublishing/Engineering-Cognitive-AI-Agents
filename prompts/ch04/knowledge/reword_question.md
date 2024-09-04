---
model: gpt-4o-mini
temperature: 0.7
max_tokens: 256
top_p: 0.95
frequency_penalty: 0.0
response_format_type: text
---

# Reword a Question

Rephrase the [ORIGINAL QUESTION] provided in {{ num_rewordings }} distinct ways,
ensuring the meaning and context remain intact.
Strive for originality and steer clear of redundancy and typical synonyms.
Make certain that the core meaning of the rephrased questions
is preserved.
Provide the reworded questions in a list format, with each question
on a new line, without numbers or bullets.

## Example

[ORIGINAL QUESTION]: What is the capital of Italy?
[REWRITTEN QUESTIONS]:
Which city serves as the capital of Italy?
Can you name the capital city of Italy?
What is the name of Italy's capital?

## Input

[ORIGINAL QUESTION]: {{ question }}
[REWRITTEN QUESTIONS]:
