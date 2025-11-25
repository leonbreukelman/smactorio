"""
Spec-Kit CLI automation for headless execution.

This module wraps the specify-cli to enable non-interactive,
automated spec-driven development in CI/CD pipelines.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_seed(seed_path: Path) -> dict[str, Any]:
    """
    Load and validate the steering seed configuration.

    Args:
        seed_path: Path to the seed.json file

    Returns:
        The parsed seed configuration

    Raises:
        FileNotFoundError: If seed.json doesn't exist
        json.JSONDecodeError: If seed.json is invalid JSON
    """
    with seed_path.open() as f:
        return json.load(f)


def run_spec_kit_init(project_name: str) -> bool:
    """
    Initialize a new Spec-Kit project.

    Args:
        project_name: Name of the project to initialize

    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            ["specify", "init", project_name],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Spec-Kit initialized: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Spec-Kit initialization failed: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            "specify-cli not found. Install with: uv tool install specify-cli",
            file=sys.stderr,
        )
        return False


def bootstrap_factory(seed_path: Path | None = None) -> dict[str, Any] | None:
    """
    Bootstrap the software factory from the steering seed.

    This is the main entry point for automated factory initialization.
    It reads the seed.json, initializes Spec-Kit, and prepares the
    environment for code generation.

    Args:
        seed_path: Optional path to seed.json. Defaults to .speckit/seed.json

    Returns:
        The seed configuration if successful, None otherwise
    """
    if seed_path is None:
        seed_path = Path(".speckit/seed.json")

    if not seed_path.exists():
        print(f"Seed file not found: {seed_path}", file=sys.stderr)
        return None

    seed = load_seed(seed_path)

    project_name = seed.get("project_metadata", {}).get("name", "unnamed-project")
    intent = seed.get("intent", "")

    print(f"Bootstrapping factory for project: {project_name}")
    print(f"Intent: {intent[:100]}..." if len(intent) > 100 else f"Intent: {intent}")

    # Initialize Spec-Kit (if available)
    # Note: In turnkey mode, this may be skipped if spec-kit isn't installed
    run_spec_kit_init(project_name)

    return seed


def write_spec_artifact(output_path: Path, content: str) -> None:
    """
    Write a spec artifact (spec.md, plan.md, tasks.md) to disk.

    Args:
        output_path: Path where the artifact should be written
        content: The markdown content to write
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    print(f"Written: {output_path}")


if __name__ == "__main__":
    # CLI entry point for testing
    result = bootstrap_factory()
    if result:
        print("Bootstrap complete!")
    else:
        sys.exit(1)
