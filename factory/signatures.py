"""
DSPy signatures for the AI Software Factory.

This module defines the declarative signatures that replace brittle prompt engineering
with type-safe, optimizable AI interactions.
"""

from typing import TYPE_CHECKING

import dspy

if TYPE_CHECKING:
    from factory.models import CodeArtifact


class GenerateCode(dspy.Signature):
    """
    Implement a feature based on a Spec-Kit task.

    This signature produces type-safe code artifacts that are validated
    by Pydantic schemas before being written to disk.
    """

    context: str = dspy.InputField(
        desc="Relevant sections from AGENTS.md and project context"
    )
    task: str = dspy.InputField(desc="The specific task description to implement")
    plan: str = dspy.InputField(desc="Architectural constraints from the plan")

    artifact: "CodeArtifact" = dspy.OutputField(
        desc="The executable code artifact conforming to CodeArtifact schema"
    )


class GenerateSpec(dspy.Signature):
    """
    Generate a functional specification from the project intent.

    Transforms the high-level intent from seed.json into a comprehensive
    specification document with user stories and acceptance criteria.
    """

    intent: str = dspy.InputField(desc="The project intent from seed.json")
    tech_stack: str = dspy.InputField(desc="Technology stack configuration")
    governance: str = dspy.InputField(desc="Governance rules and constraints")

    specification: str = dspy.OutputField(
        desc="Complete functional specification in markdown format"
    )


class GeneratePlan(dspy.Signature):
    """
    Generate a technical architecture plan from the specification.

    Translates functional requirements into concrete technical decisions
    including library choices, database schemas, and API signatures.
    """

    specification: str = dspy.InputField(desc="The functional specification")
    tech_stack: str = dspy.InputField(desc="Technology stack constraints")

    plan: str = dspy.OutputField(desc="Technical architecture plan in markdown format")


class DecomposeTasks(dspy.Signature):
    """
    Decompose the plan into atomic units of work.

    Breaks down the technical plan into granular, independently executable
    tasks that prevent context drift during implementation.
    """

    plan: str = dspy.InputField(desc="The technical architecture plan")
    specification: str = dspy.InputField(desc="The functional specification")

    tasks: str = dspy.OutputField(desc="Task list in markdown checklist format")


class DebugCode(dspy.Signature):
    """
    Analyze and fix code that failed validation.

    Used in the reflexion loop when generated code fails linting or testing.
    """

    code: str = dspy.InputField(desc="The code that failed validation")
    error: str = dspy.InputField(desc="The error message from validation")
    context: str = dspy.InputField(desc="Relevant context from AGENTS.md")

    fixed_code: str = dspy.OutputField(desc="The corrected code")
    explanation: str = dspy.OutputField(desc="Explanation of the fix")
