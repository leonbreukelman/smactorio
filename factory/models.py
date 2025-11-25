"""
Pydantic models for type-safe AI code generation.

This module defines the output schemas that constrain DSPy agent outputs,
ensuring that all generated code passes validation before being persisted.
"""

import ast
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodeArtifact(BaseModel):
    """
    Represents the output of a coding task from the DSPy agent.

    All generated code must conform to this schema. The syntax_check validator
    ensures that invalid Python code is rejected before it reaches the filesystem.
    """

    model_config = ConfigDict(strict=True)

    filename: Annotated[
        str,
        Field(description="The relative path to the file (e.g., 'src/models/user.py')"),
    ]
    content: Annotated[
        str,
        Field(description="The valid, executable source code"),
    ]
    dependencies: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="New PyPI packages required by this code",
        ),
    ]
    test_plan: Annotated[
        str,
        Field(description="A comprehensive test strategy for this file"),
    ]

    @field_validator("content")
    @classmethod
    def syntax_check(cls, v: str) -> str:
        """
        Validates that the generated code has valid Python syntax.

        This validator runs BEFORE the code is accepted, enabling DSPy's
        self-correction loop to automatically retry on syntax errors.
        """
        try:
            ast.parse(v)
        except SyntaxError as e:
            raise ValueError(f"Generated code has syntax errors: {e}") from e
        return v


class TaskDefinition(BaseModel):
    """
    Represents an atomic unit of work from the task decomposition phase.
    """

    model_config = ConfigDict(strict=True)

    id: Annotated[str, Field(description="Unique identifier for the task")]
    title: Annotated[str, Field(description="Brief title of the task")]
    description: Annotated[str, Field(description="Detailed task description")]
    acceptance_criteria: Annotated[
        list[str],
        Field(description="Criteria that must be met for task completion"),
    ]
    dependencies: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="IDs of tasks that must be completed first",
        ),
    ]


class PlanSection(BaseModel):
    """
    Represents a section of the technical architecture plan.
    """

    model_config = ConfigDict(strict=True)

    title: Annotated[str, Field(description="Section title")]
    content: Annotated[str, Field(description="Section content in markdown")]
    rationale: Annotated[
        str,
        Field(description="Explanation for the architectural decision"),
    ]
