"""A basic prompt to solve a math problem."""

from typing import Type

from pydantic import BaseModel, Field

from mirascope import tags
from mirascope.anthropic import AnthropicExtractor


class ProblemDetails(BaseModel):
    solving_steps: str = Field(description="The steps to solve the math problem.")
    answer: int = Field(description="the answer to the math problem.")


@tags(["version:0003"])
class ProblemSolver(AnthropicExtractor[ProblemDetails]):
    extract_schema: Type[ProblemDetails] = ProblemDetails
    prompt_template = """
    Here is a math problem: {problem}
    Write out the answer step by step to arrive at the answer.
    """

    problem: str
