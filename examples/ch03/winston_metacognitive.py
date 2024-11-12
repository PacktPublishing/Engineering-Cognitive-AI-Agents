from typing import AsyncIterator

from winston.core.agent import BaseAgent
from winston.core.messages import Message, Response
from winston.core.workspace import WorkspaceManager


class MetacognitiveAgent(BaseAgent):
  """Specialist agent for metacognitive workspace refinement."""

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Analyze and refine the shared workspace."""
    _, shared_workspace = (
      self._get_workspaces(message)
    )
    if not shared_workspace:
      return

    reflection_prompt = f"""
        Analyze this workspace content metacognitively:

        {shared_workspace}

        Focus your analysis on:
        1. Interaction Patterns
           - Identify recurring themes in user communication
           - Note successful and less successful interaction strategies
           - Observe user engagement patterns

        2. Knowledge Integration
           - Assess how well different pieces of information connect
           - Identify gaps in understanding
           - Note areas where context could be better maintained

        3. Strategy Effectiveness
           - Evaluate effectiveness of current interaction approaches
           - Consider alternative strategies that might work better
           - Note which types of responses generate better engagement

        4. Workspace Organization
           - Assess clarity and usefulness of current organization
           - Identify areas where information could be better structured
           - Consider how to optimize for future interactions

        Provide specific recommendations for workspace updates that will improve future interactions.
        Format your response in two parts:
        1. Analysis: Your metacognitive observations and insights
        2. Updates: Specific changes to implement in the workspace
        """

    # Generate metacognitive analysis
    analysis_response = await self.generate_response(
      Message(
        content=reflection_prompt,
        metadata={"type": "Metacognitive Analysis"},
      )
    )

    # Generate the workspace updates
    update_prompt = f"""
        Based on this metacognitive analysis:
        {analysis_response.content}

        Generate an updated version of the workspace that implements the recommended improvements
        while maintaining all essential information. The updated workspace should:

        1. Maintain the core markdown structure
        2. Implement the suggested organizational improvements
        3. Integrate metacognitive insights
        4. Preserve all important user information and context
        5. Add a "Metacognitive Insights" section that tracks:
           - Successful interaction patterns
           - Areas for improvement
           - Strategic adjustments

        Current workspace:
        {shared_workspace}
        """

    update_response = await self.generate_response(
      Message(
        content=update_prompt,
        metadata={"type": "Workspace Update"},
      )
    )

    # Update the private workspace
    workspace_manager = WorkspaceManager()
    workspace_manager.save_workspace(
      self.workspace_path, analysis_response.content
    )

    # Update the shared workspace
    shared_workspace_path = message.metadata.get(
      "shared_workspace"
    )
    assert shared_workspace_path
    workspace_manager.save_workspace(
      shared_workspace_path, update_response.content
    )
    yield Response(
      content=update_response.content,
      metadata={"type": "Metacognitive Refinement"},
    )
