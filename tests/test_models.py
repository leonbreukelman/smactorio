"""Tests for factory.models module."""

import pytest

from factory.models import CodeArtifact, PlanSection, TaskDefinition


class TestCodeArtifact:
    """Tests for the CodeArtifact model."""

    def test_valid_code_artifact(self):
        """Test creating a valid CodeArtifact."""
        artifact = CodeArtifact(
            filename="src/main.py",
            content='print("Hello, World!")',
            dependencies=["requests"],
            test_plan="Test that the print statement executes correctly.",
        )
        assert artifact.filename == "src/main.py"
        assert artifact.content == 'print("Hello, World!")'
        assert artifact.dependencies == ["requests"]

    def test_syntax_validation_passes(self):
        """Test that valid Python syntax passes validation."""
        valid_code = """
def hello():
    return "Hello"

if __name__ == "__main__":
    print(hello())
"""
        artifact = CodeArtifact(
            filename="test.py",
            content=valid_code,
            test_plan="Test hello function",
        )
        assert artifact.content == valid_code

    def test_syntax_validation_fails(self):
        """Test that invalid Python syntax raises ValueError."""
        invalid_code = """
def hello(
    return "Hello"
"""
        with pytest.raises(ValueError, match="syntax errors"):
            CodeArtifact(
                filename="test.py",
                content=invalid_code,
                test_plan="Should fail",
            )

    def test_empty_dependencies_default(self):
        """Test that dependencies default to empty list."""
        artifact = CodeArtifact(
            filename="test.py",
            content="pass",
            test_plan="Minimal test",
        )
        assert artifact.dependencies == []


class TestTaskDefinition:
    """Tests for the TaskDefinition model."""

    def test_valid_task_definition(self):
        """Test creating a valid TaskDefinition."""
        task = TaskDefinition(
            id="TASK-001",
            title="Initialize project",
            description="Set up the initial project structure",
            acceptance_criteria=["Directory structure exists", "Config files created"],
            dependencies=[],
        )
        assert task.id == "TASK-001"
        assert task.title == "Initialize project"
        assert len(task.acceptance_criteria) == 2

    def test_task_with_dependencies(self):
        """Test task with dependencies on other tasks."""
        task = TaskDefinition(
            id="TASK-002",
            title="Implement API",
            description="Create the API endpoints",
            acceptance_criteria=["Endpoints respond correctly"],
            dependencies=["TASK-001"],
        )
        assert task.dependencies == ["TASK-001"]


class TestPlanSection:
    """Tests for the PlanSection model."""

    def test_valid_plan_section(self):
        """Test creating a valid PlanSection."""
        section = PlanSection(
            title="Database Design",
            content="Use PostgreSQL with SQLAlchemy ORM.",
            rationale="PostgreSQL provides ACID compliance and JSON support.",
        )
        assert section.title == "Database Design"
        assert "PostgreSQL" in section.content
        assert "ACID" in section.rationale
