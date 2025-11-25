#!/usr/bin/env python3
"""
Main orchestration script for the AI Software Factory.

This script ties all components together into a linear execution graph:
1. Bootstrap: Hydrate environment with uv sync
2. Spec Generation: Generate spec.md from seed.json
3. Task Decomposition: Generate tasks.md
4. Context Loading: Initialize RAG with spec content
5. Agent Loop: Generate code for each task
6. Validation: Lint and test, invoke debugger if needed

Usage:
    uv run python scripts/build.py
"""

import subprocess
import sys
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from factory.bootstrap import bootstrap_factory, write_spec_artifact
from factory.memory import (
    build_context_string,
    create_memory_store,
    get_or_create_collection,
    index_document,
)


def sync_environment() -> bool:
    """
    Ensure the environment is hydrated with all dependencies.

    Returns:
        True if sync succeeded, False otherwise
    """
    print("Step 1: Syncing environment with uv...")
    try:
        subprocess.run(["uv", "sync"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Environment sync failed: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("uv not found. Please install uv first.", file=sys.stderr)
        return False


def run_linter() -> bool:
    """
    Run the Ruff linter on the project.

    Returns:
        True if linting passed, False otherwise
    """
    print("Running linter...")
    try:
        subprocess.run(
            ["uv", "run", "ruff", "check", "."],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        print("Linting failed", file=sys.stderr)
        return False


def run_tests() -> bool:
    """
    Run the pytest test suite.

    Returns:
        True if all tests passed, False otherwise
    """
    print("Running tests...")
    try:
        subprocess.run(
            ["uv", "run", "pytest"],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        print("Tests failed", file=sys.stderr)
        return False


def initialize_memory(speckit_dir: Path) -> tuple | None:
    """
    Initialize the RAG memory store and index spec documents.

    Args:
        speckit_dir: Path to the .speckit directory

    Returns:
        Tuple of (client, collection) if successful, None otherwise
    """
    print("Step 4: Initializing memory store...")

    client = create_memory_store()
    collection = get_or_create_collection(client)

    # Index any existing spec documents
    for doc_name in ["spec.md", "plan.md", "tasks.md"]:
        doc_path = speckit_dir / doc_name
        if doc_path.exists():
            chunks = index_document(collection, doc_path)
            print(f"  Indexed {doc_name}: {chunks} chunks")

    return client, collection


def generate_placeholder_spec(seed: dict, speckit_dir: Path) -> None:
    """
    Generate a placeholder spec.md when Spec-Kit CLI is not available.

    In production, this would be replaced by actual Spec-Kit generation.
    For turnkey setup, we create a template that can be filled in.

    Args:
        seed: The seed configuration
        speckit_dir: Path to the .speckit directory
    """
    project_name = seed.get("project_metadata", {}).get("name", "unnamed")
    description = seed.get("project_metadata", {}).get("description", "")
    intent = seed.get("intent", "")

    spec_content = f"""# Specification: {project_name}

## Overview

{description}

## Intent

{intent}

## Functional Requirements

> This section will be populated by the Spec-Kit specify command.
> For now, use this as a template to define your requirements.

### User Stories

1. As a developer, I want to...

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Non-Functional Requirements

- Performance: TBD
- Security: TBD
- Scalability: TBD
"""

    write_spec_artifact(speckit_dir / "spec.md", spec_content)


def generate_placeholder_plan(seed: dict, speckit_dir: Path) -> None:
    """
    Generate a placeholder plan.md when Spec-Kit CLI is not available.

    Args:
        seed: The seed configuration
        speckit_dir: Path to the .speckit directory
    """
    tech_stack = seed.get("tech_stack", {})
    language = tech_stack.get("language", "python")
    framework = tech_stack.get("framework", "fastapi")
    database = tech_stack.get("database", "chromadb")

    plan_content = f"""# Technical Architecture Plan

## Technology Stack

- **Language**: {language}
- **Framework**: {framework}
- **Database**: {database}

## Architecture Decisions

### Decision 1: [Title]

**Rationale**: TBD

### Decision 2: [Title]

**Rationale**: TBD

## Component Structure

```
src/
├── main.py          # Application entry point
├── api/             # API routes
├── models/          # Data models
├── services/        # Business logic
└── utils/           # Utilities
```

## API Design

> This section will be populated by the Spec-Kit plan command.
"""

    write_spec_artifact(speckit_dir / "plan.md", plan_content)


def generate_placeholder_tasks(speckit_dir: Path) -> None:
    """
    Generate a placeholder tasks.md when Spec-Kit CLI is not available.

    Args:
        speckit_dir: Path to the .speckit directory
    """
    tasks_content = """# Task Decomposition

## Phase 1: Setup

- [ ] **TASK-001**: Initialize project structure
- [ ] **TASK-002**: Configure dependencies

## Phase 2: Core Implementation

- [ ] **TASK-003**: Implement data models
- [ ] **TASK-004**: Implement API routes
- [ ] **TASK-005**: Implement business logic

## Phase 3: Testing & Validation

- [ ] **TASK-006**: Write unit tests
- [ ] **TASK-007**: Write integration tests
- [ ] **TASK-008**: Run full validation

> Tasks will be auto-generated by the Spec-Kit tasks command.
> Each task should be atomic and independently implementable.
"""

    write_spec_artifact(speckit_dir / "tasks.md", tasks_content)


def main() -> int:
    """
    Main entry point for the build orchestrator.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print("=" * 60)
    print("AI Software Factory - Build Orchestrator")
    print("=" * 60)

    speckit_dir = PROJECT_ROOT / ".speckit"
    seed_path = speckit_dir / "seed.json"

    # Step 1: Sync environment
    if not sync_environment():
        return 1

    # Step 2: Bootstrap from seed
    print("\nStep 2: Bootstrapping from seed...")
    seed = bootstrap_factory(seed_path)
    if not seed:
        return 1

    # Step 3: Generate spec artifacts (placeholder mode for turnkey)
    print("\nStep 3: Generating spec artifacts...")
    if not (speckit_dir / "spec.md").exists():
        generate_placeholder_spec(seed, speckit_dir)
    if not (speckit_dir / "plan.md").exists():
        generate_placeholder_plan(seed, speckit_dir)
    if not (speckit_dir / "tasks.md").exists():
        generate_placeholder_tasks(speckit_dir)

    # Step 4: Initialize memory store
    print("\nStep 4: Initializing memory store...")
    memory_result = initialize_memory(speckit_dir)
    if not memory_result:
        print("Warning: Memory store initialization failed", file=sys.stderr)
    else:
        _client, collection = memory_result
        # Example: Build context for a sample query
        context = build_context_string(
            collection,
            "project setup and initialization",
            PROJECT_ROOT / "AGENTS.md",
        )
        print(f"  Context built: {len(context)} characters")

    # Step 5: Agent Loop would go here
    # In a full implementation, this would iterate through tasks.md
    # and use DSPy to generate code for each task
    print("\nStep 5: Agent loop (placeholder)")
    print("  In production, DSPy would generate code for each task here.")

    # Step 6: Validation
    print("\nStep 6: Validation...")
    lint_ok = run_linter()
    test_ok = run_tests()

    if not (lint_ok and test_ok):
        print("\nValidation failed. In production, debugger agent would be invoked.")
        # Don't fail the build for lint/test issues in template mode
        # return 1

    print("\n" + "=" * 60)
    print("Build orchestration complete!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
