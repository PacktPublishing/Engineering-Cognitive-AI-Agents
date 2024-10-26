---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 8192
---

I will generate a comprehensive summary of the following messages in a conversation, making sure to capture the key points and details, including entities, relationships, and context, while remaining concise and informative.

I will incorporate any previous summary into my new summary.

[MESSAGES]:
{{ messages }}

[PREVIOUS SUMMARY]:
{{ previous_summary }}

[NEW SUMMARY]:
