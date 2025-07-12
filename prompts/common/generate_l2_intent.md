You are an expert AI assistant for an advanced cognitive agent. Your task is to analyze a list of low-level, specific L1 intents (agent capabilities) and categorize them into semantically related groups. For each group, you will create a higher-level L2 intent that represents the group's shared purpose.

## Input: L1 Intents

You will be given a list of L1 intents. These are fine-grained capabilities of the agent.

**L1 Intents:**
```
{% for intent in l1_intents -%}
- {{ intent }}
{% endfor %}
```

## Task: Categorize and Abstract

Your goal is to group the related L1 intents and then write a new, more abstract L2 intent for each group. An L2 intent is a broader capability that encompasses a set of L1 intents.

Follow these rules:
1.  **Analyze and Group**: Identify clusters of L1 intents that share a common purpose or relate to a similar step in a workflow.
2.  **Create L2 Intent**: For each group, write a concise, high-level L2 intent that describes the group's overall function. This L2 intent acts as a "category name."
3.  **Strict Output Format**: Present the output as one or more `[GROUP]` blocks. Each block must contain the L2 intent and the list of L1 intents belonging to it. Do not include any other text or explanation.

## Example

**Input L1 Intents:**
```
- check python code for syntax errors
- install a python package using pip
- run a python script
- format python code using black
- analyze python code for style issues
- search for files by name
- list contents of a directory
```

**Correct Output:**
```
[GROUP]
L2 Intent: manage and execute python code
L1 Intents:
- check python code for syntax errors
- install a python package using pip
- run a python script
- format python code using black
- analyze python code for style issues

[GROUP]
L2 Intent: navigate and search the file system
L1 Intents:
- search for files by name
- list contents of a directory
```

## Your Turn

Now, analyze the provided L1 intents and generate the `[GROUP]` blocks according to the rules.
