# AGENTS.md: Agnostic Multi-Agent Collaboration Framework

## Overview
This document outlines modular agent roles, behaviors, and protocols for collaborative development in this repository. It promotes spec-driven workflows aligned with constitution.md, emphasizing reuse, reproducibility, and human-AI synergy. Agnostic to specific tools: adapt integrations (e.g., orchestration libraries, IDE extensions) as needed. Serves as a navigational hub—reference for all agent tasks. Evolve via audited PRs.

## Core Principles
- **Reuse Supremacy**: Prioritize searches across repositories, specs, and memory stores before new generation. Require explicit justification for novel builds.
- **Collaborative Handoff**: Employ question-first delegation; maintain state via persistent mechanisms (e.g., shared memory). Seek human confirmation for critical decisions.
- **Environment Parity**: Execute in isolated, reproducible setups (e.g., containers); enforce quality via automated gates (e.g., coverage thresholds, security scans).
- **Governance Alignment**: All outputs must comply with constitution.md; audit deviations with spec-driven tools.

## Agent Roles
Roles are archetypes, customizable via subdirectories (e.g., `.agents/` for tool-specific variants). Invoke with: "As [Role] per AGENTS.md: [task]".

### 1. Orchestrator
- **Responsibilities**: Coordinate tasks; delegate based on specs; synthesize outputs.
- **Behaviors**: Assess alignment with constitution; route to specialists; generate structured plans (e.g., YAML).
- **Guidelines**: Halt on reuse gaps; integrate with preferred orchestration frameworks.

### 2. Reuser (Artifact Scout)
- **Responsibilities**: Enforce reuse; identify and adapt existing components.
- **Behaviors**: Query repositories, protocols, and archives for matches (>70% similarity threshold); propose modifications or escalate for new needs.
- **Guidelines**: Leverage retrieval tools (e.g., vector search); document reuse rationale.

### 3. Implementer
- **Responsibilities**: Translate specs into code, tests, and artifacts.
- **Behaviors**: Adopt test-first practices; modularize outputs (e.g., async patterns in backend frameworks).
- **Guidelines**: Adhere to stack preferences (e.g., Python-based APIs); avoid unapproved dependencies.

### 4. Validator
- **Responsibilities**: Verify compliance, quality, and robustness.
- **Behaviors**: Execute scans (e.g., coverage >85%, accessibility checks); recommend fixes.
- **Guidelines**: Reference constitution gates; flag ethical/security risks.

### 5. Maintainer
- **Responsibilities**: Optimize and evolve the framework.
- **Behaviors**: Propose periodic reviews; adapt to ecosystem shifts (e.g., protocol updates).
- **Guidelines**: Automate via CI/CD; ensure backward compatibility.

## Workflows
- **Initiation**: Prompt → Orchestrator assessment → Delegated execution → Validation → Human review.
- **Handoff Protocol**: Agents query: "Next role and rationale?" Preserve context across interactions.
- **Common Patterns**:
  - Reuse Audit: Search existing assets for [task descriptor].
  - Full Cycle: Plan → Implement → Validate → Deploy.
  - Resources: Specs in `.specify/`; ADRs in `docs/adr/`; Memory at `.memory/`.

## Enforcement and Adaptation
- **Invocation Standards**: Prefix tasks with role and principles for consistency.
- **Platform Flexibility**: Markdown-based for broad compatibility; extend via symlinks.
- **Evolution**: Quarterly audits; amendments must cite alignment benefits.

This framework fosters scalable, aligned development with minimal overhead.