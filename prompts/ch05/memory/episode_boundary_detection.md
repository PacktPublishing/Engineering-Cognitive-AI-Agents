---
model: gpt-4o-mini
temperature: 0.3
max_tokens: 2048
response_format:
  type: json_schema
  json_schema:
    name: episode_boundary_detection
    strict: true
    schema:
      type: object
      properties:
        is_new_episode:
          type: boolean
          description: "Indicates if a new episode has started"
        rationale:
          type: string
          description: "Explanation for why a new episode has started or not"
      required:
        - is_new_episode
        - rationale
      additionalProperties: false
---

I need to determine if a new episode has started in a
conversation based on these criteria:

- Have I noticed a significant change in the topic
  being discussed?
- Has the user's intent or purpose for the conversation
  shifted?
- Were there any long pauses between messages?
- Did we complete any specific tasks or goals in our
  previous exchange?
- Did the user explicitly signal that they were done
  with a topic?

I should analyze the conversation and look for the
signs to identify if we've moved on to a new episode.

[SHORT-TERM MEMORY]
{{whiteboard}}

[CONVERSATION HISTORY]
{{message_history}}

If a new episode has started, I will include a clear
true or false value for "is_new_episode". I provide a
concise rationale for the decision.
