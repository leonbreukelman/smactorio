FROM python:3.12-slim-bookworm

# 1. Install uv (The Rust-based Python package manager)
# We copy from the official image to ensure binary integrity
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. System Dependencies for Vector DBs and Compilers
# Agents may need to compile C extensions or run local vector stores
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Spec-Kit CLI via uv tool
# "uv tool install" creates isolated environments for CLI tools, preventing
# dependency conflicts with the main project.
RUN uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# 4. Configure the Workspace
WORKDIR /workspaces/factory