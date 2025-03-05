# **BRUTALIST WRITING GUIDELINES FOR ENGINEERING COGNITIVE AI AGENTS**

Books that teach cognitive AI should operate like the systems they describe: **deliberate, structured, and purposeful.** The goal is not to impress with verbose academic abstractions or distract with unnecessary detail—but rather to provide readers with **conceptual clarity**, **architectural understanding**, and **practical tools.** Every sentence, diagram, and code snippet must fulfill a purpose: to empower readers to **design, implement, and think critically** about robust AI systems.

---

## **CORE WRITING PRINCIPLES** _(ALWAYS RESPECT THESE)_

### 1. **Purpose-Driven Writing**

- Every paragraph, section, and chapter **must contribute to the reader's learning experience.** Include only content that serves their ability to **grasp concepts, solve problems, and apply knowledge.**
- Serve the purpose of the book: **teaching architecture**, **enabling design**, and **fostering critical analysis of AI systems.**

### 2. **Clarity and Simplicity**

- Strip away excess. Favor blunt honesty and functional precision over stylistic decoration. Avoid jargon unless you define and contextualize it.
- Simple writing doesn't mean sacrificing depth—explore ideas deeply, but explain them **cleanly and directly.**

### 3. **Concept First, Execution Second**

- Always answer the **"why"** of a topic before diving into the **"how."** Ground every architectural or design choice in a clear rationale.
- Architectural principles and design decisions come first. Implementation (e.g., code), when presented, exists to **support understanding**—not dominate the discussion.

### 4. **Progressive, Holistic Teaching**

- Think of the book as a system, where every chapter or section contributes to the **larger scaffolding of understanding.**
  - Introduce concepts progressively. Build foundational knowledge before layering advanced material.
  - Every chapter and example must connect backward to prior content and forward to future material.
- Teach readers how components **interact, integrate, and evolve over time,** emphasizing both individual pieces and the larger whole.

### 5. **Functional Focus**

- Make every element of the book—whether text, diagram, or code—serve a specific teaching purpose. **No fluff, no filler.**

---

## **WHAT TO AVOID** _(NEVER DO THE FOLLOWING)_

### 1. **Overloading with Details**

- Avoid overloading readers with implementation details too early. Leave exhaustive detail for an accompanying codebase or appendix—focus the text on teaching principles and design.
- Granular discussions belong to external references or repositories when they don't serve the immediate learning goals.

### 2. **Abstract or Vague Writing**

- Don't resort to abstract philosophy or verbose, academic prose. Aim for **functional phrases and actionable insights**. Teach **clarity, not confusion.**

### 3. **Disconnected Content**

- Never leave a section unanchored. Every part must **tie into prior or future chapters.**
- Avoid isolated examples or fragmented topics that don’t contribute to the book’s overall flow.

### 4. **Style Over Substance**

- Do not sacrifice clarity or functionality for flowery language, aesthetic diagrams, or redundant code samples.
- Avoid overused, cliched words and phrases like:

1. **Overused Descriptive Words**:

   - Delve
   - Crucial
   - Journey
   - Robust
   - Leverage
   - Synergy
   - Innovative (unless genuinely groundbreaking)
   - Scalable
   - Seamless (especially in tech contexts)
   - Groundbreaking
   - Comprehensive

2. **Vague or Hyperbolic Phrases**:

   - State-of-the-art
   - Paradigm shift
   - Cutting-edge
   - Game-changer
   - Best practices (unless you clarify which practices you mean)
   - Tried and true
   - At the end of the day

3. **Unnecessary Idioms or Metaphors**:

   - Thinking outside the box
   - Move the needle
   - Wearing many hats
   - Hitting the nail on the head
   - All hands on deck
   - Leveling the playing field

4. **Buzzwords**:

   - Disruptive
   - Ecosystem (especially when referring to things like digital products)
   - Bandwidth (as in capacity to handle tasks)
   - Value proposition
   - Customer-centric
   - Data-driven (unless specifics are given)
   - Agile (used indiscriminately)
   - Turnkey solutions
   - Low-hanging fruit

5. **Fluffy Connectives**:

   - Needless to say
   - Without further ado
   - In a nutshell
   - With that being said
   - It goes without saying

6. **Motivational or Generic Intentions**:
   - Passion for excellence
   - Take a deep dive
   - Pushing the envelope
   - Striving for perfection
   - Think big, act fast

By replacing these expressions with more specific, accurate, or concise language, you'll improve clarity and avoid diluting your message. Let me know if you'd like examples of better alternatives for a particular phrase!

### 5. **LLM-Style Embellishments**

- **Reject Unnecessary Qualifiers**: Remove adjectives, adverbs, and dramatic phrases that don't add meaningful information:

  - "fundamentally transforms" → "changes" or "modifies"
  - "seamlessly integrates" → "integrates" or "connects"
  - "dramatically improves" → "improves"

- **Eliminate Technical Hyperbole**: Technical writing demands exactness. Avoid subjective or exaggerated terms that make text sound like marketing copy rather than factual documentation.

- **Common Offenders to Cut**:

  - Self-inflating verbs: "transforms," "revolutionizes," "unlocks"
  - Vague intensifiers: "incredibly," "profoundly," "deeply"
  - Subjective qualifiers: "elegant," "sophisticated," "powerful"

- **Maintain Precision**: Choose specific, accurate language that precisely describes what happens without interpretive embellishment.

- **Writing Example**:
  - Flowery: "This three-phase process fundamentally transforms how Winston interacts with its cognitive workspaces."
  - Precise: "This three-phase process modifies how Winston interacts with its cognitive workspaces."

---

## **STRUCTURE AND DESIGN OF CHAPTERS**

Each chapter must function as a **step in the reader’s journey.** It introduces concepts logically, builds understanding methodically, and culminates in actionable insight or application.

### **1. Introduction**

- **Define the Problem**: Start by presenting the challenge or capability the chapter addresses. Explain why it’s important in the broader system.
- **Contextualize**: Connect to prior chapters or the overall book structure to ensure readers see the logical progression.
- **Preview the Solution**: Briefly outline the architectural/design approaches the chapter will explore.

### **2. Core Architecture**

- **System-Level Concepts**: Clearly explain the architectural foundations and structural abstractions.
  - Discuss **alternative approaches** and justify the selected solution using reasoned arguments.
  - Use Mermaid diagrams and conceptual frameworks sparingly, only when they clarify complex relationships.
- **Relationships Between Components**: Show how individual pieces interact as part of the full system.

### **3. Implementation Sections**

- Provide **focused explanations** of how to implement key architectural patterns.
- **Design Thoughtfully**: Explain trade-offs and constraints when constructing components.
- **Use Code Judiciously**:
  - Only include functional, concise snippets that illuminate key concepts.
  - **Contextualize** every code block: Explain its purpose and how it integrates into the broader system.

### **4. Integration Example**

- Show readers a comprehensive integration of components into a **complete system.**
  - Use **realistic scenarios** and workflows to demonstrate how parts unite and achieve practical goals.
  - Highlight **outputs, interactions, and real-world utility.**
  - Provide teasers or hints about how the chapter’s content links to future material.

### **5. Conclusion**

- **Reinforce Key Points**: Review major takeaways to solidify the reader’s understanding.
- **Connect the Dots**: Show how this chapter contributes to the larger trajectory of the book. Prepare the reader for what’s next.

---

## **BEST PRACTICES FOR WRITING STYLE**

1. **Precision**: Avoid wordy explanations. Use concise, functional language to communicate ideas effectively.
2. **Reasoned Argumentation**: Motivate every decision with clear reasoning. Address trade-offs and alternatives.
3. **Accessibility**: Write progressively for a mixed technical audience, connecting theory to practice. Don’t assume an advanced reader; build their knowledge incrementally.
4. **Architectural Focus**: Center the writing around **design patterns, principles, and architecture.** Granular implementation details are secondary.
5. **Avoid Empty Words**: Stay focused on teaching. Avoid vague expressions (e.g., "delve deeply," "seemingly simple") that fail to add clarity.

---

## **INTEGRATION OF CODE AND DIAGRAMS**

- **Code Integration**:

  - Use code **purposefully** to illustrate key architectural ideas—not as filler or syntax demonstrations.
  - Provide clear type hints, structural outlines, and examples of usage with accompanying explanations.
  - Always link code snippets to the broader system, and reference the repository for full implementations.

- **Diagram Usage**:
  - Include diagrams **only when necessary** to clarify complex relationships or flows. Avoid cluttered or overly technical visuals.
  - System-wide illustrations and information flow diagrams are particularly useful—keep them simple and intuitive.

---

## **EXAMPLES AND SCENARIOS**

Examples are one of the most powerful ways to bridge abstract ideas and direct application. Use them liberally but strategically:

- **Realistic**: Ground examples in real-world tasks and applications relevant to cognitive AI systems.
- **Progressive Learning**: Build examples that grow in complexity alongside the reader’s understanding.
- **Application-Oriented**: Show examples in context—how they work within the broader architecture.

---

## **GOOD TECHNICAL WRITING**

Adapting Dieter Rams' design principles, good technical writing:

### **Is innovative**

Technical writing evolves with technology. Find fresh approaches to explain complex concepts and stay ahead of emerging patterns in cognitive systems.

### **Makes knowledge useful**

Writing must empower readers to apply information immediately. Useless knowledge burdens readers; useful knowledge solves problems.

### **Is structured**

Organize writing with clear hierarchy and consistent patterns. Structure should enhance comprehension, not simply decorate.

### **Makes concepts understandable**

Break complexity into digestible components. Clarity isn't a bonus—it's the foundation. The reader should never need to re-read for basic comprehension.

### **Is unobtrusive**

Keep focus on content, not stylistic flourishes. The writing should be invisible, allowing ideas to take center stage.

### **Is honest**

Acknowledge limitations and challenges. Don't oversell capabilities or gloss over difficulties. Technical honesty builds reader trust.

### **Is enduring**

Emphasize principles and patterns that transcend specific implementations. Good technical writing remains valuable despite technological evolution.

### **Is thorough**

Leave no critical concept unexplained. Anticipate questions and address them methodically, without unnecessary elaboration.

### **Is efficient**

Respect the reader's cognitive resources. Each sentence should provide value without waste. Conserve attention as a finite resource.

### **Contains only what's necessary**

Use the minimum text needed to convey maximum meaning. Remove everything that doesn't contribute to understanding. When uncertain whether to include something, remove it.

## **STYLOMETRIC ANALYSIS AND APPLICATION**

This analysis provides a concrete style guide based on effective technical writing. Follow these patterns to maintain consistency and clarity throughout your work.

### **1. Lexical Features**

- **Word Choice**: Use precise, technical vocabulary suited to a scientific and engineering audience. Balance domain-specific terms with clear explanations.
- **Function Words**: Deploy connectors like "while," "through," and "for example" to link ideas logically. Use prepositions like "within" and "between" to emphasize relationships.
- **Vocabulary Richness**: Maintain moderate richness with recurring technical terms and varied synonyms to avoid repetition.
- **Tone Indicators**: Use words reflecting precision, clarity, and confidence in system design.

### **2. Syntactic Features**

- **Sentence Length**: Write medium to long sentences (15-25 words), often compound or complex, to support detailed explanations.
- **Sentence Structure**: Use subordination ("while," "which") and coordination ("and," "but") to build layered arguments. Use passive voice selectively for objectivity.
- **Punctuation**: Use dashes for emphasis and parentheses for asides. Introduce lists or explanations with colons.
- **Parallelism**: Apply in lists and procedural descriptions to enhance readability.

### **3. Structural Features**

- **Paragraph Length**: Write substantial paragraphs (150-250 words), each focusing on a single concept with a clear topic sentence and supporting details.
- **Headings**: Structure content hierarchically with numbered sections and descriptive titles.
- **Exposition**: Blend theoretical explanation with practical implementation. Justify design choices explicitly.
- **Examples**: Include concrete examples and code snippets to ground abstract concepts.
- **Visual Aids**: Reference figures and code blocks to enhance clarity.

### **4. Tone and Style**

- **Tone**: Maintain an authoritative yet instructional stance. Be optimistic about system potential while acknowledging limitations.
- **Style**: Write analytically and procedurally, focusing on clarity and modularity. Be formal but accessible.
- **Rhetorical Devices**: Use analogy and contrast to clarify complex ideas.

### **5. Unique Markers**

- Emphasize "separation of concerns," "modularity," and "cognitive plausibility" as guiding principles.
- Position prompts as the locus of cognitive reasoning.
- Reference iterative development with phrases like "this foundation" and "future chapters."

### **6. Words and Phrases to Avoid**

Beyond the previously listed terms, specifically avoid:

- Marketing or sales-pitch language
- Colloquial expressions or slang
- Overly simplistic or vague terms
- Words like "delve" and "journey"
- Self-inflating hyperbole and unnecessary adjectives

**Before**: "We elevate the robustness of storing data by implementing redundancy."
**After**: "We improve data storage by implementing redundancy."

### **7. Style Transformation Example**

#### Original Text (Casual)

> I wrote some code to save data yesterday. It works fine, I guess. You can pull up old stuff when you need it, which is cool. I might tweak it later if I feel like it.

#### Transformed Text (Technical)

> Yesterday, I implemented a data persistence mechanism designed to store information efficiently—an essential capability for maintaining context across interactions. This system, while functional in its current form, enables the retrieval of previously stored data as needed, providing a practical foundation for future enhancements. The implementation leverages a straightforward storage approach, ensuring that data remains accessible through a simple query process. For example, a user requesting historical information can retrieve it seamlessly, much like accessing a well-organized archive. While this establishes a robust baseline—demonstrating clear separation between storage and retrieval operations—future iterations will refine its scalability and integration with broader cognitive workflows. Looking ahead, I anticipate introducing adaptive mechanisms to optimize performance, building on this initial framework to support increasingly sophisticated data management needs.

### **8. Application Process**

1. Identify the core idea and frame it technically.
2. Replace casual terms with precise, domain-specific vocabulary.
3. Build complex, layered sentences using appropriate connectors.
4. Develop substantial paragraphs with clear topics and logical flow.
5. Ground text with concrete examples and design justifications.
6. Emphasize modularity, clarity, and scalability.
7. Maintain an authoritative, instructional voice balanced with growth acknowledgment.

### **9. Example of Poor Writing Transformation**

#### Problematic Phrase

> "Then an examination takes place to determine why"

This phrase violates multiple brutalist guidelines:

1. **Uses passive voice** ("takes place") instead of stating who performs the action
2. **Lacks clarity and directness** by hiding the actor and using unnecessary words
3. **Sounds vague and academic** rather than functional and precise
4. **Uses empty filler words** that don't contribute to understanding

#### Improved Versions

> "Then we examine why"
> "Next, we investigate the reason"
> "We then analyze the cause"

The improved versions are:

- Active rather than passive
- Direct and concise
- Clear about who performs the action
- Free of unnecessary words

This example demonstrates how even short phrases can violate the brutalist principles when they prioritize formality over clarity and directness.

---

## **FINAL PHILOSOPHY**

Cognitive AI is complex, but your book must not be. **Expose the scaffolding of ideas so readers can see the structure.** Each chapter, section, and diagram should teach cleanly, directly, and without confusing ornamentation. Clarity beats complexity. Functionality beats style.

Readers should finish the book feeling both informed and empowered—ready not just to replicate your examples but to design, build, and innovate their own cognitive AI systems independently.

**AVOID USING LISTS**: you are writing a book, not a checklist. People want to read prose, not endless lists and bullet points. **AVOID USING LISTS**

**Make the book raw, functional, and purpose-driven. Make it brutalist.**
