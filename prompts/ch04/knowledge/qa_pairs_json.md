---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 1024
top_p: 0.95
frequency_penalty: 0.0
response_format_type: json_object
---

# Generate Question-Answer Pairs as JSON

You will be given a text containing question and answer pairs in various
formats. Your task is to extract these pairs and convert them into a JSON array
of objects. Each object should have two keys: 'q' for the question and 'a' for
the answer.
The output should be structured as follows:
[
{
"q": "Question 1",
"a": "Answer 1"
},
{
"q": "Question 2",
"a": "Answer 2"
},
...
]
Ensure that:

1. The entire output is a valid JSON array.
2. Each question-answer pair is represented as a separate object within the array.
3. The 'q' key contains the full question text.
4. The 'a' key contains the full answer text.
5. Any formatting or structure from the original text is removed, presenting clean
   question and answer strings.
6. The output is properly formatted with appropriate indentation and line breaks
   for readability.

Process the entire input text and include all question-answer pairs found in the
output JSON array.

Input text:

{{ input_text }}

{% if previous_error %}
Previous error:

{{ previous_error }}
{% endif %}

Your JSON output (only):
