# Smactorio - AI Software Factory

[![CI](https://github.com/leonbreukelman/smactorio/actions/workflows/ci.yml/badge.svg)](https://github.com/leonbreukelman/smactorio/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

An **Autonomous Turnkey Software Factory** using Spec-Driven Development (SDD) and Agentic Orchestration.

## Overview

Smactorio is a "Software Factory in a Box" that transforms the vague request of "build me an app" into a rigorous, engineered process. It implements:

- **Governance Layer**: GitHub Spec-Kit for Spec → Plan → Tasks workflow
- **Environmental Layer**: DevContainers + uv for reproducible environments
- **Context Layer**: AGENTS.md protocol for AI agent context management
- **Cognitive Layer**: DSPy + Pydantic for type-safe AI code generation

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) (for DevContainer)
- [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- Or: [uv](https://docs.astral.sh/uv/) for local development

### Using DevContainer (Recommended)

1. Clone this repository
2. Open in VS Code
3. Click "Reopen in Container" when prompted
4. Run: `uv sync` to install dependencies

### Local Development

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/leonbreukelman/smactorio.git
cd smactorio

# Install dependencies
uv sync --all-extras

# Run linter
uv run ruff check .

# Run tests
uv run pytest
```

## Project Structure

```
.
├── .devcontainer/           # DevContainer configuration
│   ├── Dockerfile           # Container with uv + Spec-Kit CLI
│   ├── devcontainer.json    # VS Code settings
│   └── postcreatecommand.sh # Post-setup script
├── .github/workflows/       # CI/CD automation
├── .speckit/                # Spec-Kit governance artifacts
│   └── seed.json            # Steering Seed (project intent)
├── factory/                 # AI Factory logic
│   ├── models.py            # Pydantic models (CodeArtifact)
│   ├── signatures.py        # DSPy signatures
│   ├── bootstrap.py         # Spec-Kit CLI automation
│   └── memory.py            # ChromaDB RAG integration
├── scripts/
│   └── build.py             # Main orchestration script
├── src/                     # Generated product code
├── AGENTS.md                # AI agent context protocol
├── pyproject.toml           # Dependencies (managed by uv)
└── README.md                # This file
```

## Usage

### 1. Configure the Steering Seed

Edit `.speckit/seed.json` to define your project:

```json
{
  "project_metadata": {
    "name": "my-project",
    "version": "0.1.0",
    "description": "My project description"
  },
  "governance": {
    "strict_mode": true,
    "test_coverage_threshold": 0.85,
    "style_guide": "google"
  },
  "tech_stack": {
    "language": "python",
    "framework": "fastapi",
    "database": "chromadb",
    "packaging": "uv"
  },
  "intent": "Your detailed project intent here..."
}
```

### 2. Run the Factory

```bash
uv run python scripts/build.py
```

This will:
1. Sync the environment
2. Bootstrap from the seed
3. Generate spec artifacts (spec.md, plan.md, tasks.md)
4. Initialize the RAG memory store
5. Execute the agent loop (when fully implemented)
6. Validate with linting and tests

## Architecture

See [smactorio_spec.md](smactorio_spec.md) for the complete technical specification.

### Key Components

- **Spec-Kit**: Enforces unidirectional flow from Constitution → Specification → Plan → Tasks
- **DSPy**: Declarative programming with LLMs, replacing brittle prompt engineering
- **Pydantic**: Type-safe validation of all AI-generated code artifacts
- **ChromaDB**: Local vector database for RAG-enhanced context retrieval

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Adding Dependencies

```bash
uv add <package>
uv add --dev <dev-package>
```

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details