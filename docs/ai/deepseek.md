# DeepSeek R1: Revolutionizing Reasoning in Large Language Models with GRPO, Test-Time Compute Scaling, and Distillation

### Abstract/Summary

DeepSeek R1, developed by DeepSeek, is an open-source large language model (LLM) engineered to excel in reasoning tasks, rivaling models like OpenAI's o1. This brief explores its innovative multi-stage training pipeline, which integrates Group Relative Policy Optimization (GRPO)—an efficient reinforcement learning (RL) algorithm—with supervised fine-tuning (SFT) to enhance reasoning capabilities while ensuring readability. Key features include test-time compute scaling, enabling up to 32,768-token reasoning chains with improved accuracy via majority voting, and the use of reasoning tokens within <think></think> tags for transparent step-by-step logic. Additionally, the brief delves into the distillation process, where smaller models (1.5B to 70B parameters) are derived from DeepSeek R1’s reasoning traces, broadening accessibility. Technical details of GRPO training, inference processes, and performance metrics (e.g., 79.8% Pass@1 on AIME 2024) are provided, alongside comparisons with other reasoning models, highlighting DeepSeek R1’s contributions to AI reasoning advancements.

### Key Points

- Research suggests DeepSeek R1, a reasoning-focused AI model, performs comparably to OpenAI's o1, using reinforcement learning (RL) for enhanced reasoning.
- It seems likely that test-time compute scaling improves accuracy by generating multiple answers and using majority voting, up to 32,768 tokens.
- The evidence leans toward distillation creating smaller, efficient models from larger ones' reasoning traces, aiding broader use.
- Reasoning tokens are the model's step-by-step thought process, marked by special tags, enhancing transparency.

### Overview

DeepSeek R1 is an advanced large language model (LLM) designed for reasoning tasks, developed by DeepSeek. It aims to match or exceed models like OpenAI's o1, focusing on math, coding, and general reasoning. The model uses a multi-stage training approach, combining RL with supervised fine-tuning (SFT), to ensure both performance and readability.

### Training Method

The training involves Group Relative Policy Optimization (GRPO), an efficient RL algorithm that compares groups of responses to optimize the model without a separate critic. This method helps DeepSeek R1 generate accurate and well-formatted reasoning chains, addressing challenges like poor readability seen in earlier versions.

### Inference and Features

At inference, DeepSeek R1 can generate extensive reasoning up to 32,768 tokens, with test-time compute scaling allowing multiple samples for better accuracy via majority voting. Reasoning tokens, marked by <think></think> tags, show the model's thought process, while distilled smaller models (1.5B to 70B parameters) make advanced reasoning accessible for various applications.

---

### Comprehensive Analysis of DeepSeek R1 and Related Concepts

DeepSeek R1 represents a significant advancement in the field of large language models (LLMs), particularly in enhancing reasoning capabilities. This analysis provides a detailed examination of DeepSeek R1, its training methodology, and key concepts such as test-time compute scaling, reasoning tokens, and the distillation of smaller models from reasoning traces. It also contextualizes DeepSeek R1 against other reasoning models like OpenAI's o1, ensuring a thorough understanding for researchers, developers, and enthusiasts.

#### Background and Problem Statement

The development of DeepSeek R1 addresses a critical challenge in AI: creating LLMs that can effectively reason across diverse domains such as mathematics, coding, and general knowledge. Reasoning tasks often require complex, structured thinking, which traditional LLMs struggle with due to issues like poor readability and inconsistent language use. DeepSeek R1 aims to overcome these limitations, offering performance comparable to leading models like OpenAI's o1, while being open-source to foster community engagement.

The solution involves a sophisticated training pipeline that integrates reinforcement learning (RL) with supervised fine-tuning (SFT) and innovative techniques like cold-start data and distillation. This approach not only enhances reasoning but also ensures the model is practical for real-world applications, balancing performance with efficiency.

#### Basic Approach and Model Variants

DeepSeek R1's development is bifurcated into two main variants: DeepSeek-R1-Zero and DeepSeek-R1, each with distinct training strategies.

- **DeepSeek-R1-Zero**: This version is trained purely via RL on the base model, DeepSeek-V3-Base, without any initial SFT. It leverages the Group Relative Policy Optimization (GRPO) algorithm, demonstrating impressive reasoning capabilities. However, it faced challenges such as poor readability and language mixing, which impacted user experience.

- **DeepSeek-R1**: To address these issues, DeepSeek-R1 employs a multi-stage training pipeline:
  1. **Cold Start**: The base model is fine-tuned with thousands of long chain-of-thought (CoT) data, formatted with special tokens (e.g., |special_token|<reasoning_process>|special_token|<summary>) to ensure readability.
  2. **Reasoning-oriented RL**: Similar to R1-Zero, this stage uses GRPO with additional rewards for language consistency, though it may slightly reduce performance to improve user-friendliness.
  3. **Rejection Sampling and SFT**: The model is further refined with 600k reasoning samples and 200k non-reasoning samples (e.g., writing, factual QA, self-cognition), totaling 800k samples, fine-tuned for two epochs.
  4. **Secondary RL**: This final stage combines rule-based rewards for math and code with reward models for helpfulness and harmlessness, ensuring versatility across scenarios.

This multi-stage approach allows DeepSeek R1 to evolve from a purely RL-based model to a more robust, user-friendly reasoning tool, achieving performance metrics such as 79.8% Pass@1 on AIME 2024, 97.3% on MATH-500, and 90.8% on MMLU.

#### Technical Description of Training: GRPO

Group Relative Policy Optimization (GRPO) is a pivotal component of DeepSeek R1's training, particularly in the RL stages. As a variant of Proximal Policy Optimization (PPO), GRPO optimizes the model's policy by evaluating groups of responses relative to one another, rather than relying on a separate critic model. This efficiency is crucial for scaling to large models, reducing computational overhead.

The process involves:

- **Group Sampling**: For a given prompt, the LLM generates multiple responses.
- **Reward Scoring**: A reward model evaluates the quality of each response based on accuracy (e.g., rule-based for math, compiler-based for code) and format (enforcing <think></think> tags).
- **Advantage Calculation**: Responses are compared to the group's average reward to identify better or worse performances.
- **Policy Update**: The model's policy is adjusted to favor high-reward responses, constrained by KL divergence to avoid drastic changes.
- **Iterative Training**: This cycle repeats, gradually improving the model's ability to generate high-quality, aligned text.

GRPO's efficiency makes it ideal for reasoning tasks, enabling DeepSeek R1 to handle complex problem-solving and long CoTs, with observed "aha moments" during training, such as sudden improvements in reasoning strategies.

#### Inference Time: Technical Processes and Features

At inference time, DeepSeek R1's capabilities are leveraged to maximize reasoning performance, with several key features:

- **Generation Length**: The model supports a maximum generation length of 32,768 tokens, allowing for extensive reasoning processes. This is particularly useful for tasks requiring long CoTs, such as solving competition-level math problems.

- **Test-Time Compute Scaling**: This concept involves scaling computational resources during inference to improve accuracy. DeepSeek R1 uses pass@𝑘 evaluation, where multiple samples (𝑘 between 4-64) are generated, and the majority vote determines the final answer. For instance, on AIME 2024, cons@64 (majority vote with 64 samples) significantly boosts performance, demonstrating how additional compute can enhance results. The model is configured with temperature 0.6 and top-𝑝 0.95 for generation, balancing creativity and focus.

- **Reasoning Tokens**: These are the tokens generated within the <think></think> tags, representing the step-by-step reasoning process. This feature enhances transparency, allowing users to understand how the model arrives at its conclusions. For example, in math tasks, reasoning tokens might include intermediate steps like "Let's solve for x by first isolating terms," making the process explicit.

- **Prompt Sensitivity**: The model is sensitive to prompts, with recommendations for zero-shot settings to avoid performance degradation from few-shot prompts. Length control is also implemented, with average summary lengths varying by task, such as 689 tokens for ArenaHard and 2,218 characters for AlpacaEval 2.0.

#### Distillation of Smaller Models from Reasoning Traces

A notable aspect of DeepSeek R1 is the distillation process, which creates smaller, efficient models from the reasoning traces of the larger model. This involves:

- **Data Source**: The distillation uses 800k samples, including reasoning outputs from DeepSeek R1, covering both reasoning and non-reasoning tasks.
- **Training Process**: Smaller models, based on architectures like Qwen2.5 (1.5B, 7B, 14B, 32B) and Llama (8B, 70B), are fine-tuned on these samples without an RL stage. For example, DeepSeek-R1-Distill-Qwen-7B achieves 55.5% on AIME 2024 and 92.8% on MATH-500, demonstrating retained reasoning capability.
- **Impact**: This process makes advanced reasoning accessible on devices with limited computational resources, broadening the model's applicability.

The distillation leverages the chain-of-thought traces, ensuring that smaller models inherit the reasoning strategies developed by the larger model, such as reflection and long CoTs.

#### Comparison with Other Reasoning Models

DeepSeek R1 is positioned against other reasoning-focused models, notably OpenAI's o1. Research suggests DeepSeek R1 achieves comparable performance, with benchmarks like 79.8% Pass@1 on AIME 2024 matching or exceeding o1 in specific tasks. Unlike o1, DeepSeek R1 is open-source, offering model weights and distilled variants (e.g., 1.5B to 70B), which fosters community innovation. Other models, such as Google's Gemini and Anthropic's Claude, also focus on reasoning, but DeepSeek R1's open-source nature and GRPO-based training provide unique advantages.

#### Performance Metrics and Evaluation

To quantify DeepSeek R1's effectiveness, consider the following table of key benchmarks:

| **Benchmark** | **DeepSeek R1 Performance**    | **Notes**                                      |
| ------------- | ------------------------------ | ---------------------------------------------- |
| AIME 2024     | 79.8% Pass@1, 86.7% cons@64    | Majority voting significantly boosts accuracy. |
| MATH-500      | 97.3%                          | High accuracy in competition-level math.       |
| MMLU          | 90.8%                          | Strong general knowledge reasoning.            |
| GPQA Diamond  | 71.5%                          | Robust on specialized knowledge tasks.         |
| Codeforces    | 96.3% percentile (2029 rating) | Outperforms most human coders.                 |

These metrics highlight DeepSeek R1's versatility, with particular strength in math and coding, aligning with its design for reasoning-intensive tasks.

#### Practical Implications and Future Directions

DeepSeek R1's open-source availability, as seen on platforms like GitHub ([DeepSeek-R1 GitHub Repository](https://github.com/deepseek-ai/DeepSeek-R1)) and Hugging Face, democratizes access to advanced reasoning models. Its integration with Azure AI Foundry ([DeepSeek R1 on Azure](https://azure.microsoft.com/en-us/blog/deepseek-r1-is-now-available-on-azure-ai-foundry-and-github/)) further enhances enterprise adoption. The model's ability to scale compute at test time and distill into smaller variants suggests future applications in education, coding assistance, and research, potentially influencing how AI handles complex problem-solving.

Future research might explore optimizing GRPO for even larger models, enhancing prompt engineering for zero-shot settings, and expanding the distillation process to include more diverse reasoning tasks. The ongoing competition with models like OpenAI's o1 and o3, as noted in recent analyses ([DeepSeek R1 vs. OpenAI o1](https://www.datacamp.com/blog/deepseek-r1)), underscores the dynamic nature of this field.

#### Key Citations

- [DeepSeek-R1 GitHub Repository development by creating an account on GitHub](https://github.com/deepseek-ai/DeepSeek-R1)
- [DeepSeek official website unravel the mystery of AGI with curiosity](https://www.deepseek.com/)
- [deepseek-ai/DeepSeek-R1 on Hugging Face We’re on a journey to advance and democratize artificial intelligence](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [DeepSeek-R1 Release DeepSeek API Docs Performance on par with OpenAI-o1](https://api-docs.deepseek.com/news/news250120)
- [DeepSeek R1 Online Free nologin Open-Source AI Model for Advanced Reasoning](https://deepseek-r1.com/)
- [deepseek-ai/DeepSeek-R1 Demo on DeepInfra Try out API on the Web](https://deepinfra.com/deepseek-ai/DeepSeek-R1)
- [DeepSeek-R1 Features o1 Comparison Distilled Models DataCamp Blog](https://www.datacamp.com/blog/deepseek-r1)
- [DeepSeek-R1 Incentivizing Reasoning Capability in LLMs via Reinforcement Learning arXiv paper](https://arxiv.org/abs/2501.12948)
- [PromptHub Blog DeepSeek R-1 Model Overview and How it Ranks Against OpenAI's o1](https://www.prompthub.us/blog/deepseek-r-1-model-overview-and-how-it-ranks-against-openais-o1)
- [DeepSeek R1 is now available on Azure AI Foundry and GitHub Microsoft Azure Blog](https://azure.microsoft.com/en-us/blog/deepseek-r1-is-now-available-on-azure-ai-foundry-and-github/)
- [GRPO Trainer for training language models Hugging Face Documentation](https://huggingface.co/docs/trl/main/en/grpo_trainer)
- [What is GRPO The RL algorithm used to train DeepSeek Medium article](https://medium.com/data-science-in-your-pocket/what-is-grpo-the-rl-algorithm-used-to-train-deepseek-12acc19798d3)
- [The Math Behind DeepSeek A Deep Dive into Group Relative Policy Optimization Medium article](https://medium.com/%40sahin.samia/the-math-behind-deepseek-a-deep-dive-into-group-relative-policy-optimization-grpo-8a75007491ba)
- [GRPO Trainer Hugging Face Documentation for TRL](https://huggingface.co/docs/trl/grpo_trainer)
- [Training Large Language Models From TRPO to GRPO Towards Data Science article](https://towardsdatascience.com/training-large-language-models-from-trpo-to-grpo/)
- [PPO vs GRPO The Future of AI Training OpenAI o1 vs DeepSeek R1 Appy Pie Blog](https://www.appypie.com/blog/openai-o1-ppo-vs-deepseek-r1-grpo-comparison)
- [Post training an LLM for reasoning with GRPO in TRL Hugging Face Cookbook](https://huggingface.co/learn/cookbook/fine_tuning_llm_grpo_trl)
- [Efficient Learning DeepSeek R1 with GRPO DataOps Labs Blog](https://blog.dataopslabs.com/deepseek-r1-efficient-reinforcement-learning-with-grpo)
- [GRPO The Future of Self-Verifying AI DeepSeek R1 Case Study Appy Pie Blog](https://www.appypie.com/blog/group-relative-policy-optimization-self-verifying-ai)
