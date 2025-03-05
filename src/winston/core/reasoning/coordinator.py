"""Reasoning Coordinator: Orchestrates systematic problem-solving through memory-informed reasoning.

The Reasoning Coordinator implements a sophisticated problem-solving cycle by coordinating specialist
agents that work together to understand, solve, and learn from challenges. It integrates memory
at each stage of reasoning to enhance problem-solving capabilities and build a growing knowledge base.

Architecture Overview:
```mermaid
graph TD
    RC[Reasoning Coordinator] -->|State Management| WS[Workspace]
    MC[Memory Coordinator] <-->|Knowledge Exchange| RC
    RC -->|Query Context| MC
    RC -->|Store Learnings| MC

    subgraph "Reasoning Stages"
        RC -->|Stage 1| HA[Hypothesis Agent]
        HA -->|Results| RC
        RC -->|Stage 2| IA[Inquiry Agent]
        IA -->|Results| RC
        RC -->|Stage 3| VA[Validation Agent]
        VA -->|Results| RC
    end

    subgraph "Memory Integration"
        RC -->|Before Hypothesis| QH[Query Memory]
        QH -->|Problem Context| HA
        RC -->|Before Inquiry| QI[Query Memory]
        QI -->|Hypothesis Context| IA
        RC -->|Before Validation| QV[Query Memory]
        QV -->|Inquiry Context| VA
    end

    subgraph "Learning Capture"
        HA -->|Hypothesis Learnings| LC[Learning Capture]
        IA -->|Inquiry Learnings| LC
        VA -->|Validation Learnings| LC
        LC -->|Store| MC
    end
```

System Prompt and Decision Making:
The Reasoning Coordinator uses a specialized system prompt that:
1. Establishes its role as the central decision-maker in the reasoning process
2. Provides the current workspace content as context for decision-making
3. Guides analysis through structured criteria:
   - Context Continuity: Determining if a problem is new or continuing
   - Stage Progression: Identifying the current reasoning stage and transition conditions
   - Stage Requirements: Detailed criteria for each reasoning stage
4. Requires decisions to be made through the handle_reasoning_decision tool with:
   - requires_context_reset: Whether to start fresh with a new problem
   - next_stage: The appropriate reasoning stage to execute next
   - workspace_updates: Specific content changes needed in the workspace
   - explanation: Clear rationale for the decision

Workspace Template and Management:
1. Custom Workspace Template:
   - Provides a structured markdown format with predefined sections:
     * Current Problem: The problem statement
     * Reasoning Stage: The current stage in the reasoning process
     * Background Knowledge: Relevant information from memory
     * Learning Capture: Insights from memory relevant to the current stage
     * Next Steps: Planned actions for problem resolution
   - Initializes new workspaces with problem-specific content
   - Maintains consistent structure across reasoning cycles

2. Advanced Workspace Editing:
   - Uses WorkspaceManager's sophisticated editing capabilities:
     * Delta-based editing for precise, targeted updates
     * Edit validation to ensure changes maintain workspace integrity
     * Diff generation to track changes between versions
     * Archiving of previous workspaces for reference
   - Handles workspace transitions between reasoning stages
   - Manages content organization to prevent duplication
   - Preserves cognitive continuity across reasoning cycles

Reasoning Stages:
1. HYPOTHESIS_GENERATION
   - Analyzes the problem and generates potential solutions
   - Consults memory for similar problems and relevant domain knowledge
   - Updates workspace with hypotheses and their confidence levels

2. INQUIRY_DESIGN
   - Designs tests to validate the hypotheses
   - Consults memory for relevant test designs and validation approaches
   - Updates workspace with test designs and execution plans

3. VALIDATION
   - Analyzes test results and validates hypotheses
   - Consults memory for interpretation frameworks and previous conclusions
   - Updates workspace with validation results and confidence assessments

4. Additional States:
   - NEEDS_USER_INPUT: Requests additional information from the user
   - PROBLEM_SOLVED: Indicates the problem has been successfully solved
   - PROBLEM_UNSOLVABLE: Indicates the problem cannot be solved with current constraints

Specialist Agent Dispatching:
The Reasoning Coordinator orchestrates specialist agents by:
1. Determining the appropriate specialist based on the current reasoning stage
2. Preparing the workspace context for the specialist:
   - Loading the current workspace content
   - Extracting the problem statement
   - Determining the current reasoning stage
   - Querying memory for relevant context
   - Updating the workspace with memory-informed context
3. Dispatching to the appropriate specialist agent:
   - HypothesisAgent: Generates testable predictions with confidence levels
   - InquiryAgent: Designs practical tests with clear success metrics
   - ValidationAgent: Evaluates test results and updates hypothesis confidence
4. Processing specialist responses:
   - Extracting results from the specialist
   - Updating the workspace with the specialist's output
   - Organizing content to maintain workspace clarity
   - Ensuring proper stage transitions in the workspace

Memory Coordination (Query Mode):
1. Before each specialist agent runs:
   - Extracts the problem statement from the workspace
   - Formulates a stage-specific memory query:
     * For Hypothesis: Queries similar problems and domain knowledge
     * For Inquiry: Queries test designs and validation approaches
     * For Validation: Queries interpretation frameworks and conclusions
   - Sets query_mode flag to prevent workspace modifications
   - Sends the query to the Memory Coordinator
   - Processes the memory response to extract relevant context
   - Updates the workspace with retrieved memory context

2. After each specialist agent completes:
   - Extracts specialist results from the workspace
   - Formulates a stage-specific memory update:
     * For Hypothesis: Stores generated hypotheses and confidence levels
     * For Inquiry: Stores test designs and execution plans
     * For Validation: Stores validation results and updated confidence
   - Sends the update to the Memory Coordinator
   - Associates learnings with the problem domain for future retrieval

Implementation Details:
- Uses a decision-based approach to determine the next reasoning stage
- Provides clear explanations for stage transitions
- Supports context reset for new problems
- Archives previous workspaces for reference
- Handles workspace updates through delta-based editing for efficiency

Example Reasoning Cycle:
1. Initialize workspace with problem statement using custom template
2. Query memory for relevant problem context (query_mode)
3. Generate hypotheses with memory-informed context
4. Store hypothesis learnings in memory
5. Transition to inquiry design stage
6. Query memory for relevant test design context (query_mode)
7. Design tests with memory-informed context
8. Store inquiry learnings in memory
9. Transition to validation stage
10. Query memory for relevant validation context (query_mode)
11. Validate results with memory-informed context
12. Store validation learnings in memory
13. Determine if problem is solved, needs more iterations, or requires user input

This memory-integrated reasoning approach enables Winston to:
- Learn from past experiences
- Apply relevant knowledge to new problems
- Build a growing repertoire of problem-solving strategies
- Improve reasoning effectiveness over time
"""

import json
import time
from collections.abc import AsyncIterator
from enum import StrEnum, auto
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

from loguru import logger
from pydantic import BaseModel, Field

from winston.core.agent import (
  AgentConfig,
  AgentPaths,
  BaseAgent,
  Message,
  Response,
)
from winston.core.steps import ProcessingStep
from winston.core.system import AgentSystem
from winston.core.tools import Tool
from winston.core.workspace import WorkspaceManager

from .hypothesis import HypothesisAgent
from .inquiry import InquiryAgent
from .validation import ValidationAgent


class ReasoningStage(StrEnum):
  """Current stage in the reasoning process."""

  HYPOTHESIS_GENERATION = auto()
  INQUIRY_DESIGN = auto()
  VALIDATION = auto()
  NEEDS_USER_INPUT = auto()
  PROBLEM_SOLVED = auto()
  PROBLEM_UNSOLVABLE = auto()


class ReasoningDecision(BaseModel):
  """The coordinator's decision about the current reasoning state and next steps."""

  requires_context_reset: bool = Field(
    ...,
    description="Whether the current reasoning context needs to be reset for a new problem",
  )
  next_stage: ReasoningStage = Field(
    ...,
    description="The next reasoning stage to execute",
  )
  workspace_updates: str = Field(
    ...,
    description="Complete workspace content to replace the current workspace. The LLM has full autonomy to structure the workspace as needed.",
  )
  explanation: str = Field(
    ...,
    description="Explanation of the reasoning behind this decision",
  )


class ReasoningCoordinator(BaseAgent):
  """Coordinates memory-informed reasoning."""

  def __init__(
    self,
    system: AgentSystem,
    config: AgentConfig,
    paths: AgentPaths,
  ):
    super().__init__(system, config, paths)

    # Use the workspace path initialized by the system
    self.workspace_manager = WorkspaceManager()
    self.agency_workspace = (
      Path(paths.workspaces) / f"{self.id}.md"
    )

    # Initialize reasoning specialists with agency workspace
    self.hypothesis_agent = HypothesisAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "hypothesis.yaml"
      ),
      paths,
    )
    self.inquiry_agent = InquiryAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "inquiry.yaml"
      ),
      paths,
    )
    self.validation_agent = ValidationAgent(
      system,
      AgentConfig.from_yaml(
        paths.system_agents_config
        / "reasoning"
        / "validation.yaml"
      ),
      paths,
    )

    # Register the reasoning decision tool
    tool = Tool(
      name="handle_reasoning_decision",
      description="Handle and apply a reasoning decision, including any workspace updates, and return the validated decision",
      handler=self._handle_reasoning_decision,
      input_model=ReasoningDecision,
      output_model=ReasoningDecision,
    )
    self.system.register_tool(tool)
    self.system.grant_tool_access(self.id, [tool.name])

  async def _apply_workspace_updates(
    self, updates: str
  ) -> None:
    """Apply updates to the workspace content.

    Parameters
    ----------
    updates : str
        String containing the complete workspace content to replace the current workspace.
        The LLM has full autonomy to structure the workspace as needed.
    """
    if not updates.strip():
      return

    # Check if the workspace exists
    if self.agency_workspace.exists():
      # Use the edit_file method for more robust updates
      logger.debug(
        "Applying workspace updates using edit delta"
      )
      try:
        # Generate a task description for the edit
        task = "Update the reasoning workspace with the latest content"

        # Use the edit_file method which combines delta generation, application, and validation
        result = await self.workspace_manager.edit_file(
          self.agency_workspace,
          task,
          self,  # Use self as the agent
          delta_template=None,  # Use default template
          validation_template=None,  # Use default template
        )

        # Log the validation result
        logger.debug(
          f"Edit validation result: {result["validation"]}"
        )

        # Log the diff for debugging
        logger.debug(f"Edit diff:\n{result["diff"]}")

      except Exception as e:
        # Fall back to direct save if edit_file fails
        logger.warning(
          f"Edit delta failed, falling back to direct save: {e}"
        )
        self.workspace_manager.save_workspace(
          self.agency_workspace,
          updates,
        )
    else:
      # Simply save the provided content as the new workspace
      logger.debug("Creating new workspace")
      self.workspace_manager.save_workspace(
        self.agency_workspace,
        updates,
      )

  async def _handle_reasoning_decision(
    self,
    decision: ReasoningDecision,
  ) -> ReasoningDecision:
    """Handle and apply a reasoning decision, including workspace management.

    This method centralizes all workspace management logic, handling:
    1. Context reset (archiving old workspace and creating new one)
    2. Workspace updates for ongoing problems
    3. All workspace state transitions

    Parameters
    ----------
    decision : ReasoningDecision
        The reasoning decision to process
    message : Optional[Message], optional
        The original user message, needed for workspace initialization, by default None

    Returns
    -------
    ReasoningDecision
        The validated decision after processing
    """
    logger.debug(
      f"Handling reasoning decision: {decision.model_dump_json(indent=2)}"
    )

    return decision

  def _update_reasoning_stage(
    self, content: str, stage: ReasoningStage
  ) -> str:
    """Update the reasoning stage in the workspace content.

    Parameters
    ----------
    content : str
        The current workspace content
    stage : ReasoningStage
        The new reasoning stage

    Returns
    -------
    str
        The updated workspace content
    """
    # Check if the content has a "Reasoning Stage" section
    if "# Reasoning Stage" in content:
      # Split the content at the "Reasoning Stage" section
      parts = content.split("# Reasoning Stage")
      if len(parts) > 1:
        # Get the part after "# Reasoning Stage"
        stage_part = parts[1]
        # Find the end of the stage line (next newline)
        end_of_stage = stage_part.find("\n", 1)
        if end_of_stage > 0:
          # Replace the stage line with the new stage
          updated_content = (
            parts[0]
            + "# Reasoning Stage\n"
            + stage.name
            + stage_part[end_of_stage:]
          )
          return updated_content

    # If we couldn't find the section or update it, return the original content
    logger.warning(
      "Could not update reasoning stage in workspace"
    )
    return content

  async def _cleanup_workspace(self) -> None:
    """Clean up workspace for a new problem context."""
    logger.debug(
      f"Cleaning up workspace: {self.agency_workspace}"
    )
    if self.agency_workspace.exists():
      # Archive the current workspace by renaming it with a timestamp
      archived_path = self.agency_workspace.with_name(
        f"{self.agency_workspace.stem}_archived_{int(time.time())}.md"
      )
      self.agency_workspace.rename(archived_path)
      logger.debug(
        f"Archived workspace to: {archived_path}"
      )

  async def _prepare_reasoning_workspace(
    self,
    message: Message,
  ) -> None:
    """Prepare reasoning workspace for initial stage.

    - Initializes fresh workspace using template
    - Sets up initial problem context

    Parameters
    ----------
    message : Message
        The original user message
    """
    if not self.config.workspace_template:
      raise ValueError(
        "No workspace template provided for reasoning coordinator"
      )
    template = self.config.workspace_template
    print(f"\n\n\n\nTemplate: {template}\n\n\n\n")
    print(
      f"\n\n\n\nMessage.content: {message.content}\n\n\n\n"
    )
    content = template.format(
      problem_statement=message.content,
      stage=ReasoningStage.HYPOTHESIS_GENERATION.name,
    )
    print(f"\n\n\n\nContent: {content}\n\n\n\n")
    self.workspace_manager.initialize_workspace(
      self.agency_workspace,
      owner_id=self.id,
      template=template,
      content=content,
    )

  async def _update_memory_with_learnings(
    self,
    message: Message,
    workspace_content: str,
    stage: ReasoningStage,
  ) -> None:
    """
    Update memory with learnings from the current stage.

    Parameters
    ----------
    message : Message
        The original user message
    workspace_content : str
        Current workspace content
    stage : ReasoningStage
        Current reasoning stage
    """
    # Extract the problem statement from the workspace content
    problem_statement = message.content
    if "# Current Problem" in workspace_content:
      problem_parts = workspace_content.split(
        "# Current Problem"
      )
      if len(problem_parts) > 1:
        problem_lines = (
          problem_parts[1].strip().split("\n")
        )
        if problem_lines:
          problem_statement = problem_lines[0].strip()

    # Extract specialist results if available based on the current stage
    specialist_content = ""
    section_header = ""

    if stage == ReasoningStage.HYPOTHESIS_GENERATION:
      section_header = (
        "# Hypothesis Generation Results"
      )
    elif stage == ReasoningStage.INQUIRY_DESIGN:
      section_header = "# Inquiry Design Results"
    elif stage == ReasoningStage.VALIDATION:
      section_header = "# Validation Results"

    if (
      section_header
      and section_header in workspace_content
    ):
      specialist_parts = workspace_content.split(
        section_header
      )
      if len(specialist_parts) > 1:
        specialist_content = specialist_parts[
          1
        ].strip()
        # Find the next section if any
        next_section = specialist_content.find("\n# ")
        if next_section > 0:
          specialist_content = specialist_content[
            :next_section
          ].strip()

    if stage == ReasoningStage.PROBLEM_SOLVED:
      memory_message = Message(
        content=f"""Please analyze and store key learnings from this solved problem:
Problem: {problem_statement}
Solution Process: {workspace_content}""",
        metadata={
          "shared_workspace": self.workspace_path,
          "semantic_metadata": json.dumps({
            "reasoning_stage": stage.name,
            "content_type": "solution",
            "problem_type": "solved",
            "problem_domain": problem_statement,  # Add problem domain for better retrieval
          }),
        },
      )
    else:
      # Include extracted specialist content if available
      content_to_store = workspace_content
      if specialist_content:
        content_to_store = f"""# Current Problem
{problem_statement}

{section_header}
{specialist_content}"""

      memory_message = Message(
        content=f"""Please store interim learnings from reasoning stage {stage.name}:
Problem: {problem_statement}
Current State: {content_to_store}""",
        metadata={
          "shared_workspace": self.workspace_path,
          "semantic_metadata": json.dumps({
            "reasoning_stage": stage.name,
            "content_type": "interim_learning",
            "problem_type": "in_progress",
            "problem_domain": problem_statement,  # Add problem domain for better retrieval
          }),
        },
      )

    # Process responses from memory coordinator
    async for response in cast(
      AsyncIterator[Response],
      self.system.invoke_conversation(
        "memory_coordinator",
        memory_message.content,
        context=memory_message.metadata,
      ),
    ):
      if not response.metadata.get("streaming", True):
        break

  async def _process_specialist_response(
    self,
    specialist_name: str,
    content: str,
    workspace_content: str,
    response_metadata: dict[str, Any],
  ) -> Response:
    """Process a specialist agent's response and update the workspace.

    This helper method centralizes the workspace update logic for all specialist agents.

    Parameters
    ----------
    specialist_name : str
        Name of the specialist (e.g., "Hypothesis Generation", "Inquiry Design", "Validation")
    content : str
        Content returned by the specialist agent
    workspace_content : str
        Current workspace content before the update
    response_metadata : dict
        Metadata from the specialist agent's response

    Returns
    -------
    Response
        Updated response with workspace content
    """
    logger.debug(
      f"Processing specialist response from: {specialist_name}"
    )

    # Determine the section header based on the specialist name
    section_header = f"# {specialist_name} Results"
    logger.debug(
      f"Using section header: {section_header}"
    )

    # Check if the workspace exists and has content
    if (
      self.agency_workspace.exists()
      and workspace_content.strip()
    ):
      try:
        # Create updated workspace content that includes the specialist content
        updated_content = workspace_content
        logger.debug(
          "Starting workspace content update"
        )

        # Update the reasoning stage based on the specialist name
        if specialist_name == "Hypothesis Generation":
          logger.debug(
            "Updating reasoning stage to HYPOTHESIS_GENERATION"
          )
          updated_content = (
            self._update_reasoning_stage(
              updated_content,
              ReasoningStage.HYPOTHESIS_GENERATION,
            )
          )
        elif specialist_name == "Inquiry Design":
          logger.debug(
            "Updating reasoning stage to INQUIRY_DESIGN"
          )
          updated_content = (
            self._update_reasoning_stage(
              updated_content,
              ReasoningStage.INQUIRY_DESIGN,
            )
          )
        elif specialist_name == "Validation":
          logger.debug(
            "Updating reasoning stage to VALIDATION"
          )
          updated_content = (
            self._update_reasoning_stage(
              updated_content,
              ReasoningStage.VALIDATION,
            )
          )

        # Remove any existing specialist results sections to avoid duplication
        # First check for the current specialist's section
        if section_header in updated_content:
          logger.debug(
            f"Removing existing {section_header} section to avoid duplication"
          )
          # Remove the existing section and its content
          parts = updated_content.split(section_header)
          # Keep the part before the section
          updated_content = parts[0]

          # If there are parts after this section, find the next major section
          if len(parts) > 1:
            remaining = parts[1]
            next_section_pos = remaining.find("\n# ")
            if next_section_pos > 0:
              # Add everything from the next section onwards
              logger.debug(
                "Preserving content after the next major section"
              )
              updated_content += remaining[
                next_section_pos:
              ]

        # Also remove any Learning Capture section that might contain duplicated content
        if "## Learning Capture" in updated_content:
          logger.debug(
            "Removing Learning Capture section to avoid duplication"
          )
          parts = updated_content.split(
            "## Learning Capture"
          )
          # Keep the part before the Learning Capture section
          updated_content = parts[0]

          # If there are parts after this section, find the next major section
          if len(parts) > 1:
            remaining = parts[1]
            next_section_pos = remaining.find("\n# ")
            if next_section_pos > 0:
              # Add everything from the next section onwards
              logger.debug(
                "Preserving content after the next major section"
              )
              updated_content += remaining[
                next_section_pos:
              ]

        # Now add the new specialist results section at the end
        # Make sure there's a newline before adding the section
        if not updated_content.endswith("\n\n"):
          if updated_content.endswith("\n"):
            updated_content += "\n"
          else:
            updated_content += "\n\n"

        # Add the section header and content
        logger.debug(
          f"Adding new {section_header} section with content"
        )
        updated_content += (
          f"{section_header}\n\n{content}"
        )

        # Save the updated content
        logger.debug(
          f"Saving updated workspace content to {self.agency_workspace}"
        )
        self.workspace_manager.save_workspace(
          self.agency_workspace,
          updated_content,
        )
        logger.debug(
          "Workspace content saved successfully"
        )

        # Return response with a summary instead of the full workspace content
        # to avoid payload size issues
        logger.debug(
          "Returning response with specialist content"
        )
        return Response(
          content=content,  # Just return the specialist content
          metadata={
            **response_metadata,
            "workspace": str(self.agency_workspace),
            # Don't include the full workspace_content in metadata
          },
        )
      except Exception as e:
        # Fall back to direct save if update fails
        logger.warning(
          f"Workspace update failed, falling back to direct save: {e}"
        )
        logger.debug(
          "Attempting direct save as fallback"
        )
        self.workspace_manager.save_workspace(
          self.agency_workspace,
          content,
        )
    else:
      # Save the new content directly to the workspace
      logger.debug(
        f"Workspace doesn't exist or is empty, saving content directly to {self.agency_workspace}"
      )
      self.workspace_manager.save_workspace(
        self.agency_workspace,
        content,
      )

    # Return response with the content
    logger.debug(
      "Returning response with full content"
    )
    return Response(
      content=content,
      metadata={
        **response_metadata,
        "workspace": str(self.agency_workspace),
        "workspace_content": content,
      },
    )

  async def _query_memory_for_context(
    self,
    problem_statement: str,
    stage: ReasoningStage,
    workspace_content: str,
  ) -> str:
    """Query memory for relevant context based on the current stage.

    Parameters
    ----------
    problem_statement : str
        The problem statement
    stage : ReasoningStage
        The current reasoning stage
    workspace_content : str
        Current workspace content

    Returns
    -------
    str
        Relevant context from memory
    """
    query_content = ""

    if stage == ReasoningStage.HYPOTHESIS_GENERATION:
      # Before hypothesis generation, query for information related to the problem
      query_content = f"""Please retrieve any relevant information from memory related to:
Problem: {problem_statement}

This information will be used for hypothesis generation. Focus on similar problems,
relevant domain knowledge, and previous hypotheses that might be applicable."""

    elif stage == ReasoningStage.INQUIRY_DESIGN:
      # Before inquiry design, query for information related to the hypotheses
      # Extract hypotheses from workspace
      hypotheses = ""
      if (
        "# Hypothesis Generation Results"
        in workspace_content
      ):
        hypothesis_parts = workspace_content.split(
          "# Hypothesis Generation Results"
        )
        if len(hypothesis_parts) > 1:
          hypothesis_content = hypothesis_parts[
            1
          ].strip()
          # Find the next section if any
          next_section = hypothesis_content.find(
            "\n# "
          )
          if next_section > 0:
            hypotheses = hypothesis_content[
              :next_section
            ].strip()
          else:
            hypotheses = hypothesis_content

      query_content = f"""Please retrieve any relevant information from memory related to:
Problem: {problem_statement}
Hypotheses:
{hypotheses}

This information will be used for designing inquiries to test these hypotheses.
Focus on previous test designs, validation approaches, and relevant experimental methods."""

    elif stage == ReasoningStage.VALIDATION:
      # Before validation, query for information related to the inquiry results
      # Extract inquiry results from workspace
      inquiry_results = ""
      if (
        "# Inquiry Design Results" in workspace_content
      ):
        inquiry_parts = workspace_content.split(
          "# Inquiry Design Results"
        )
        if len(inquiry_parts) > 1:
          inquiry_content = inquiry_parts[1].strip()
          # Find the next section if any
          next_section = inquiry_content.find("\n# ")
          if next_section > 0:
            inquiry_results = inquiry_content[
              :next_section
            ].strip()
          else:
            inquiry_results = inquiry_content

      query_content = f"""Please retrieve any relevant information from memory related to:
Problem: {problem_statement}
Inquiry Results:
{inquiry_results}

This information will be used for validating the results of our inquiries.
Focus on similar validation patterns, interpretation frameworks, and previous conclusions."""

    if not query_content:
      return ""

    # Query memory coordinator
    memory_context = ""
    memory_message = Message(
      content=query_content,
      metadata={
        "shared_workspace": self.workspace_path,
        "semantic_metadata": json.dumps({
          "reasoning_stage": stage.name,
          "content_type": "query",
          "problem_domain": problem_statement,
        }),
        # Set query_mode flag to prevent workspace modifications
        "query_mode": True,
      },
    )

    # Process responses from memory coordinator
    async for response in cast(
      AsyncIterator[Response],
      self.system.invoke_conversation(
        "memory_coordinator",
        memory_message.content,
        context=memory_message.metadata,
      ),
    ):
      if not response.metadata.get("streaming", True):
        # Parse the JSON response from the memory coordinator
        try:
          memory_data = json.loads(response.content)
          if memory_data.get("content"):
            memory_context = memory_data["content"]
        except json.JSONDecodeError:
          # Fallback to using the raw response if it's not valid JSON
          memory_context = response.content
        break

    return memory_context

  async def _update_workspace_with_memory_context(
    self,
    workspace_content: str,
    memory_context: str,
    stage: ReasoningStage,
  ) -> str:
    """Update workspace with context from memory.

    Parameters
    ----------
    workspace_content : str
        Current workspace content
    memory_context : str
        Context retrieved from memory
    stage : ReasoningStage
        Current reasoning stage

    Returns
    -------
    str
        Updated workspace content
    """
    if not memory_context.strip():
      return workspace_content

    # Format the memory context as a Learning Capture section
    stage_name = stage.name.replace("_", " ").title()
    learning_section = f"""# Learning Capture
## Relevant Knowledge for {stage_name}:
{memory_context}
"""

    # Check if there's already a Learning Capture section
    if "# Learning Capture" in workspace_content:
      # Replace the existing Learning Capture section
      parts = workspace_content.split(
        "# Learning Capture"
      )
      # Keep the part before the Learning Capture section
      updated_content = parts[0]

      # If there are parts after this section, find the next major section
      if len(parts) > 1:
        remaining = parts[1]
        next_section_pos = remaining.find("\n# ")
        if next_section_pos > 0:
          # Add everything from the next section onwards
          updated_content += (
            learning_section
            + remaining[next_section_pos:]
          )
        else:
          # No next section, just add the learning section
          updated_content += learning_section
      else:
        # No parts after, just add the learning section
        updated_content += learning_section
    else:
      # No existing Learning Capture section, add it before any specialist results
      # Find the first specialist results section
      specialist_pos = float("inf")
      for header in [
        "# Hypothesis Generation Results",
        "# Inquiry Design Results",
        "# Validation Results",
      ]:
        pos = workspace_content.find(header)
        if pos >= 0 and pos < specialist_pos:
          specialist_pos = pos

      if specialist_pos < float("inf"):
        # Insert before the first specialist results
        updated_content = (
          workspace_content[:specialist_pos]
          + learning_section
          + "\n\n"
          + workspace_content[specialist_pos:]
        )
      else:
        # No specialist results yet, add at the end
        updated_content = (
          workspace_content + "\n\n" + learning_section
        )

    return updated_content

  async def _run_specialist_agent(
    self,
    agent_name: str,
    specialist_agent: BaseAgent,
    message: Message,
    step: ProcessingStep,
  ) -> AsyncIterator[Response]:
    """Run a specialist agent and process its responses.

    This helper method centralizes the specialist agent execution logic.

    Parameters
    ----------
    agent_name : str
        Name of the specialist (e.g., "Hypothesis Generation", "Inquiry Design", "Validation")
    specialist_agent : BaseAgent
        The specialist agent to run
    message : Message
        The original user message
    step : ProcessingStep
        The processing step for this specialist

    Yields
    ------
    Response
        Responses from the specialist agent
    """
    # Load current workspace content
    workspace_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )

    # Extract problem statement
    problem_statement = message.content
    if "# Current Problem" in workspace_content:
      problem_parts = workspace_content.split(
        "# Current Problem"
      )
      if len(problem_parts) > 1:
        problem_lines = (
          problem_parts[1].strip().split("\n")
        )
        if problem_lines:
          problem_statement = problem_lines[0].strip()

    # Determine the current stage based on the specialist agent
    current_stage = (
      ReasoningStage.HYPOTHESIS_GENERATION
    )
    if agent_name == "Hypothesis Generation":
      current_stage = (
        ReasoningStage.HYPOTHESIS_GENERATION
      )
    elif agent_name == "Inquiry Design":
      current_stage = ReasoningStage.INQUIRY_DESIGN
    elif agent_name == "Validation":
      current_stage = ReasoningStage.VALIDATION

    # Query memory for relevant context
    memory_context = (
      await self._query_memory_for_context(
        problem_statement,
        current_stage,
        workspace_content,
      )
    )

    # Update workspace with memory context
    if memory_context:
      updated_workspace = await self._update_workspace_with_memory_context(
        workspace_content,
        memory_context,
        current_stage,
      )

      # Save the updated workspace
      self.workspace_manager.save_workspace(
        self.agency_workspace,
        updated_workspace,
      )

      # Reload the workspace content
      workspace_content = updated_workspace

    # Create message with workspace content
    specialist_message = Message(
      content=message.content,
      metadata={
        **message.metadata,
        "workspace_content": workspace_content,
      },
    )

    # Process with specialist agent
    async for response in specialist_agent.process(
      specialist_message
    ):
      if response.metadata.get("streaming"):
        yield response
        continue

      # For non-streaming responses, update the workspace
      # Reload the workspace content to ensure we have the latest state
      current_workspace_content = (
        self.workspace_manager.load_workspace(
          self.agency_workspace
        )
      )

      updated_response = (
        await self._process_specialist_response(
          agent_name,
          response.content,
          current_workspace_content,
          response.metadata,
        )
      )

      # Show the response in the step
      await step.show_response(updated_response)
      yield updated_response

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process messages to coordinate reasoning operations.

    This method orchestrates the reasoning process by:
    1. Making a decision about the current reasoning state
    2. Dispatching to the appropriate specialist agent based on the decision
    3. Updating the workspace with the specialist agent's results
    4. Updating memory with learnings from the current stage

    The LLM will automatically use the handle_reasoning_decision tool
    due to required_tool in config. The tool handler validates and applies
    workspace updates, while this method handles the flow control and
    specialist dispatching.
    """
    # Get current workspace content
    current_content = (
      self.workspace_manager.load_workspace(
        self.agency_workspace
      )
    )

    # Initial decision making phase
    async with ProcessingStep(
      name="Reasoning Decision",
      step_type="run",
    ) as step:
      # Let the LLM evaluate the message using system prompt and tools
      async for response in self._handle_conversation(
        Message(
          content=message.content,
          metadata={
            "current_workspace": current_content,
          },
        )
      ):
        if response.metadata.get("streaming"):
          yield response
          continue

        logger.debug(
          f"Reasoning decision: {response.content}"
        )

        # Tool has been executed, response contains the decision
        decision = (
          ReasoningDecision.model_validate_json(
            response.content
          )
        )
        logger.debug(
          f"Reasoning Decision: Next Stage={decision.next_stage}, Requires Reset={decision.requires_context_reset}, Explanation={decision.explanation}"
        )

        # Handle context reset if needed
        if decision.requires_context_reset:
          logger.debug("Cleaning up workspace")
          await self._cleanup_workspace()

          logger.debug("Preparing reasoning workspace")
          await self._prepare_reasoning_workspace(
            message
          )

        # For ongoing problems, apply updates if provided
        if decision.workspace_updates:
          logger.debug(
            f"Applying workspace updates for ongoing problem: {decision.workspace_updates[:100]}..."
          )
          # For ongoing problems, use edit delta for incremental updates
          await self._apply_workspace_updates(
            decision.workspace_updates
          )

        # Get updated workspace content after decision
        updated_content = (
          self.workspace_manager.load_workspace(
            self.agency_workspace
          )
        )

        # Show decision in step
        await step.show_response(
          Response(
            content=dedent(f"""
```markdown
# Reasoning Decision:
- Next Stage: {decision.next_stage}
- Requires Reset: {decision.requires_context_reset}
- Explanation: {decision.explanation}
```""").strip(),
            metadata={
              "reasoning_stage": decision.next_stage,
              "requires_reset": decision.requires_context_reset,
              "explanation": decision.explanation,
              "workspace_content": updated_content,
            },
          )
        )

        # Dispatch to appropriate specialist based on decided stage
        match decision.next_stage:
          case ReasoningStage.HYPOTHESIS_GENERATION:
            async with ProcessingStep(
              name="Hypothesis Generation",
              step_type="run",
            ) as hypothesis_step:
              async for (
                response
              ) in self._run_specialist_agent(
                "Hypothesis Generation",
                self.hypothesis_agent,
                message,
                hypothesis_step,
              ):
                yield response

          case ReasoningStage.INQUIRY_DESIGN:
            async with ProcessingStep(
              name="Inquiry Design",
              step_type="run",
            ) as inquiry_step:
              async for (
                response
              ) in self._run_specialist_agent(
                "Inquiry Design",
                self.inquiry_agent,
                message,
                inquiry_step,
              ):
                yield response

          case ReasoningStage.VALIDATION:
            async with ProcessingStep(
              name="Validation",
              step_type="run",
            ) as validation_step:
              async for (
                response
              ) in self._run_specialist_agent(
                "Validation",
                self.validation_agent,
                message,
                validation_step,
              ):
                yield response

          case ReasoningStage.NEEDS_USER_INPUT:
            yield Response(
              content="Additional user input needed",
              metadata={
                "action": "request_user_input",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

          case ReasoningStage.PROBLEM_SOLVED:
            yield Response(
              content="Problem has been solved",
              metadata={
                "action": "problem_solved",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

          case ReasoningStage.PROBLEM_UNSOLVABLE:
            yield Response(
              content="Problem has been determined to be unsolvable",
              metadata={
                "action": "problem_unsolvable",
                "workspace_content": self.workspace_manager.load_workspace(
                  self.agency_workspace
                ),
              },
            )

        # Update memory with stage-appropriate learnings
        async with ProcessingStep(
          name="Memory Update",
          step_type="run",
        ) as memory_step:
          logger.debug(
            "Updating memory with learnings"
          )
          await self._update_memory_with_learnings(
            message,
            self.workspace_manager.load_workspace(
              self.agency_workspace
            ),
            decision.next_stage,
          )
          await memory_step.show_response(
            Response(
              content=dedent(f"""
```markdown
# Memory Update
- Stage: {decision.next_stage}
- Status: Complete
```""").strip(),
              metadata=message.metadata,
            )
          )
