# AGENTS.md - Context Protocol for AI Agents

This file provides machine-actionable instructions for AI agents working with this repository.
It implements the Cascading Context Pattern for the AI Software Factory.

## @Principles

- Prefer Pydantic V2 models over raw dictionaries
- All code must be fully typed with type hints
- No circular imports
- Test coverage must exceed the threshold defined in `.speckit/seed.json`
- Use async/await patterns for I/O operations
- Follow the style guide specified in the governance configuration

## @Commands

The following commands are available for building, testing, and running the project:

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Run the main application
uv run python src/main.py

# Run the build orchestrator
uv run python scripts/build.py
```

## @Architecture

This repository implements a Turnkey Software Factory architecture with the following layers:

1. **Governance Layer (Spec-Kit)**: Enforces Spec → Plan → Tasks workflow
2. **Environmental Layer (DevContainers + uv)**: Guarantees environmental isomorphism
3. **Context Layer (AGENTS.md)**: Implements cascading context protocol
4. **Cognitive Layer (DSPy + Pydantic)**: Type-safe AI code generation

### Key Directories

- `.devcontainer/` - DevContainer configuration for reproducible environments
- `.speckit/` - Spec-Kit artifacts (seed.json, spec.md, plan.md, tasks.md)
- `.github/workflows/` - CI/CD automation pipelines
- `factory/` - DSPy modules, Pydantic models, and optimization logic
- `src/` - Generated product code (output directory)
- `scripts/` - Orchestration and automation scripts

## @Project Structure

```
.
├── .devcontainer/           # DevContainer configuration
│   ├── Dockerfile           # Container definition with uv + DSPy
│   ├── devcontainer.json    # VS Code DevContainer settings
│   └── postcreatecommand.sh # Post-container-creation setup
├── .github/
│   └── workflows/           # CI/CD automation
├── .speckit/                # Spec-Kit governance artifacts
│   └── seed.json            # Steering Seed (project intent)
├── factory/                 # AI Factory logic
│   ├── __init__.py          # Package initialization
│   ├── models.py            # Pydantic models (CodeArtifact)
│   ├── signatures.py        # DSPy signatures
│   ├── bootstrap.py         # Spec-Kit CLI automation
│   └── memory.py            # ChromaDB RAG integration
│   └── state/               # Optimized agent state
├── scripts/
│   └── build.py             # Main orchestration script
├── src/                     # Generated product code
├── AGENTS.md                # This file (global context)
├── pyproject.toml           # Dependencies and project config
└── README.md                # Human-readable documentation
```

## @Workflow

The factory follows a deterministic Spec-Driven Development pipeline:

1. **Bootstrap**: Read `seed.json` and hydrate environment with `uv sync`
2. **Specify**: Generate `.speckit/spec.md` from intent
3. **Plan**: Generate `.speckit/plan.md` with technical architecture
4. **Decompose**: Generate `.speckit/tasks.md` with atomic work units
5. **Generate**: Use DSPy to implement each task with type-safe outputs
6. **Validate**: Run linting and testing, invoke debugger agent if needed

## @Constraints

- Never write code until the spec and plan are validated
- All DSPy outputs must conform to Pydantic schemas
- Code generation must pass syntax validation before being written
- New dependencies must be added via `uv add <package>`
