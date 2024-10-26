import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from dotenv import load_dotenv
from loguru import logger

from ch03.llm import LLMParams, call_llm
from ch03.prompt import Prompt, RoleType, load_prompt

#

a = Optional[int]

_ = load_dotenv()

APPLY_GRADIENT_PROMPT = load_prompt(
  "optimization/apply_gradient"
)

CLEANUP_TEXT_PROMPT = load_prompt(
  "optimization/cleanup_text"
)

PROMPT_LOSS_FN_INSTRUCTIONS = load_prompt(
  "optimization/prompt_loss"
)

FORWARD_MODEL_PARAMS = LLMParams(
  model=os.getenv("FORWARD_MODEL", "gpt-4o-mini"),
  temperature=float(
    os.getenv("FORWARD_TEMPERATURE", "0.7")
  ),
  max_tokens=int(
    os.getenv("FORWARD_MAX_TOKENS", "2048")
  ),
  top_p=float(os.getenv("FORWARD_TOP_P", "0.95")),
  frequency_penalty=float(
    os.getenv("FORWARD_FREQUENCY_PENALTY", "0")
  ),
)

BACKWARD_MODEL_PARAMS = LLMParams(
  model=os.getenv("BACKWARD_MODEL", "gpt-4o-mini"),
  temperature=float(
    os.getenv("BACKWARD_TEMPERATURE", "0.7")
  ),
  max_tokens=int(
    os.getenv("BACKWARD_MAX_TOKENS", "2048")
  ),
  top_p=float(os.getenv("BACKWARD_TOP_P", "0.95")),
  frequency_penalty=float(
    os.getenv("BACKWARD_FREQUENCY_PENALTY", "0")
  ),
)
#


@dataclass
class OptimizationResult:
  """
  Represents the result of an optimization.
  """

  variable: "Variable"
  params: LLMParams
  role: RoleType = "user"

  #

  def __str__(self) -> str:
    return self.variable.value

  def __repr__(self) -> str:
    return f"OptimizationResult(variable={self.variable}, params={self.params}, role={self.role})"

  #

  def to_prompt(
    self,
  ) -> Prompt:
    """
    Create a prompt from an optimization result.
    """
    return Prompt(
      template=self.variable.value,
      role=self.role,
      params=self.params,
    )


class Engine:
  """
  Represents an LLM engine.
  """

  def __init__(
    self,
    params: LLMParams,
    role: RoleType = "user",
  ) -> None:
    self.params = params
    self.role = role

  async def generate(
    self, prompt: str, prompt_input: str
  ) -> Any:
    response = await call_llm(
      messages=[
        {"role": self.role, "content": prompt},
        {
          "role": "assistant",
          "content": prompt_input,
        },
      ],
      params=self.params,
    )

    if (
      self.params.response_format_type == "json_object"
    ):
      try:
        return json.loads(response)
      except json.JSONDecodeError:
        logger.error(
          "Failed to parse JSON response from LLM"
        )
        return {}
    return response


class Variable:
  """
  Represents a variable in the optimization process.
  """

  def __init__(
    self,
    value,
    requires_grad=True,
    role_description="",
  ) -> None:
    self.value = value
    self.requires_grad = requires_grad
    self.role_description = role_description
    self.grad = None

  def __str__(self) -> str:
    return self.value

  def __repr__(self) -> str:
    return f"Variable(value={self.value}, requires_grad={self.requires_grad}, role_description={self.role_description})"

  def set_gradient(self, grad: str) -> None:
    """
    Set the gradient of the variable.
    """
    if self.requires_grad:
      self.grad = grad

  async def backward(
    self, application_prompt: str, engine
  ) -> None:
    """
    Applies the gradient to the variable value using an engine.
    """
    if self.requires_grad and self.grad:
      new_value = await engine.generate(
        prompt=application_prompt,
        prompt_input=(
          f"[ORIGINAL TEXT]:\n{self.value}\n\n"
          + f"[FEEDBACK]:\n{self.grad}\n\n"
          + "[REVISED TEXT]:\n"
        ),
      )
      self.value = (
        await self._clean_text(new_value, engine)
      ).strip()
      logger.debug(f"∇ Updated value:\n\n{self.value}")

  async def _clean_text(
    self,
    text: str,
    engine: Engine,
  ) -> Any:
    """
    Clean the text using the given engine.
    """
    cleaned_text = (
      await engine.generate(
        prompt=CLEANUP_TEXT_PROMPT.render(),
        prompt_input=f"[ORIGINAL TEXT]:\n{text}\n\n[CLEANED TEXT]:\n",
      )
    ).strip()
    return cleaned_text.strip()


class TextLoss:
  """
  Represents a text loss function.
  """

  def __init__(
    self,
    feedback_prompt: str,
    engine: Engine,
  ) -> None:
    self.feedback_prompt = feedback_prompt
    self.engine = engine

  def forward(
    self,
    text: str,
    results: list[tuple[str, str]],
  ) -> Any:
    """
    Calculate the loss for the given text and results.
    """
    formatted_results = "\n".join(
      [
        f"Input: {input}\nOutput: {output}"
        for input, output in results
      ]
    )
    evaluation_input = (
      f"Text:\n{text}\n\nResults:\n{formatted_results}"
    )
    logger.debug(
      f"∇ Evaluation input:\n\n{evaluation_input}"
    )
    loss = self.engine.generate(
      self.feedback_prompt, evaluation_input
    )
    return loss


class TGD:
  """
  Represents the Text Gradient Descent (TGD) algorithm.
  """

  def __init__(
    self,
    variable: Variable,
    model_engine: Engine,
    eval_engine: Engine,
    loss_fn: TextLoss,
    inputs: list[str],
  ) -> None:
    self.variable = variable
    self.model_engine = model_engine
    self.eval_engine = eval_engine
    self.loss_function = loss_fn
    self.inputs = inputs

  def generate_results(self) -> list[Any]:
    """
    Generate results for the inputs.
    """
    results = []
    for _input in self.inputs:
      output = self.model_engine.generate(
        self.variable.value, _input
      )
      results.append((_input, output))
    return results

  async def step(self) -> None:
    """
    Perform a single step of the optimization process.
    """
    results = self.generate_results()
    loss = self.loss_function.forward(
      self.variable.value, results
    )
    logger.debug(f"∇ Loss:\n\n{loss}")
    self.variable.set_gradient(loss)
    await self.apply_gradient()

  async def apply_gradient(self) -> None:
    """
    Apply the gradient to the variable.
    """
    apply_gradient_prompt = (
      APPLY_GRADIENT_PROMPT.render()
    )
    await self.variable.backward(
      apply_gradient_prompt, self.eval_engine
    )

  async def optimize_text(
    self,
    num_iterations: int = 5,
  ) -> OptimizationResult:
    """
    Optimize the text using the given number of iterations.
    """
    for i in range(num_iterations):
      logger.debug(
        f"∇ {i+1}. Current prompt:\n\n{self.variable.value}"
      )
      await self.step()

    return OptimizationResult(
      variable=self.variable,
      params=self.model_engine.params,
    )


#


async def optimize_prompt(
  initial_prompt: str,
  prompt_inputs: list[str],
  forward: LLMParams | Engine = FORWARD_MODEL_PARAMS,
  backward: LLMParams | Engine = BACKWARD_MODEL_PARAMS,
  num_iterations: int = 3,
) -> OptimizationResult:
  """
  Optimize a prompt using the given model and eval model.
  """
  logger.trace(
    f"Optimizing prompt: {initial_prompt}, forward: {forward}, backward: {backward}, inputs: {prompt_inputs}, num_iterations: {num_iterations}"
  )
  if isinstance(forward, LLMParams):
    forward_engine = Engine(
      params=forward,
    )
  else:
    forward_engine = forward

  if isinstance(backward, LLMParams):
    backward_engine = Engine(
      params=backward,
    )
  else:
    backward_engine = backward

  variable = Variable(
    value=initial_prompt,
    role_description="Prompt to optimize",
  )

  loss_fn = TextLoss(
    PROMPT_LOSS_FN_INSTRUCTIONS.render(),
    backward_engine,
  )

  optimizer = TGD(
    variable=variable,
    model_engine=forward_engine,
    eval_engine=backward_engine,
    loss_fn=loss_fn,
    inputs=prompt_inputs,
  )

  optimized_text = await optimizer.optimize_text(
    num_iterations=num_iterations
  )
  return optimized_text
