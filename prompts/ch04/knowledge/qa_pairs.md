---
model: gpt-4o-mini
temperature: 0.7
max_tokens: 1024
top_p: 0.95
frequency_penalty: 0.0
response_format_type: json_object
---

# Generate Question-Answer Pairs

Derive various questions (along with their answers) that this text implies:
Format your result as a JSON list of objects, where each object has a 'q' key
for the question and an 'a' key for the answer.

[INPUT TEXT]
{{ input_text }}

[JSON OUTPUT]
