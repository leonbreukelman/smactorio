<!--
Sync Impact Report
- Version change: 0.1.0 → 1.0.0
- Modified principles: N/A (template → concrete)
- Added sections:
	- Preamble
	- Architectural Mandates (Backend/API Rules, Frontend Rules)
	- DevOps Governance
	- Enforcement
- Removed sections:
	- Generic SECTION_2/SECTION_3 placeholders
- Templates requiring updates:
	- .specify/templates/plan-template.md ✅ updated (Constitution Check refers to this constitution)
	- .specify/templates/spec-template.md ✅ aligned (no conflicting constraints)
	- .specify/templates/tasks-template.md ✅ aligned (no conflicting constraints)
- Follow-up TODOs:
	- TODO(RATIFICATION_DATE): Set original ratification date once decided
-->

# smactorio Constitution

## Preamble

This constitution enforces minimalism, reproducibility, and zero-drift evolution.
All specs, code, and deploys MUST align with this document or
halt until reconciled. Violations trigger `/speckit.analyze` audits.
The constitution MAY only evolve via spec-approved amendments.

## Core Principles

### Monolithic Simplicity

Build smactorio as a single, deployable unit (for example a
Next.js + Docker stack). Microservices are FORBIDDEN unless a
spec demonstrates at least a 10x scale or complexity benefit
over a monolith. Local tooling is PREFERRED over remote SaaS.
External dependencies MUST be minimal, explicit, and audited;
unvetted dependency wildcards (for example loose NPM ranges)
are FORBIDDEN.

### Test-First Discipline

Test-driven development (TDD) is MANDATORY. For every change:
tests MUST be written first, then executed to fail, then code
implemented to make them pass. CI MUST enforce at least 85%
line coverage measured via the chosen test runner (for example
Vitest or Jest). No code MAY be merged without a fully green
CI run. Edge cases including authentication, authorization,
and performance MUST have explicit smoke tests in specs and
tests.

### Data & UX Atomicity

All long-lived data MUST be represented in JSON or YAML.
User interfaces MUST be built from atomic, reusable components;
bespoke one-off UI components are FORBIDDEN unless justified
and documented in a spec. The UI MUST comply with WCAG 2.2 AA
accessibility guidelines, and web surfaces SHOULD target
Lighthouse scores of 95 or higher for performance, accessibility,
best practices, and SEO. Documentation content MUST be authored
in Markdown with no inline rich embeds that cannot be rendered
in plain text contexts.

## Architectural Mandates

### Backend/API Rules

- **No Duplication**: Before introducing new utilities or
	clients, contributors MUST search for and prefer existing
	helpers. A shared `data-client` layer (for database or
	storage access) and `api-client` layer (for outbound HTTP)
	MUST be reused wherever possible.
- **Router Purity**: HTTP or RPC routers MAY perform
	validation, authentication hooks, and direct calls into
	client layers only. Business logic MUST reside in clients
	or domain modules, not in routers. Error handling MUST be
	centralized via middleware; log-then-rethrow patterns in
	every route handler are FORBIDDEN.
- **Forbidden Patterns**: Service layers are FORBIDDEN unless
	documented complexity exceeds five distinct endpoints or
	operations for a domain. Async waterfalls that serialize
	independent work are FORBIDDEN; contributors MUST prefer
	`Promise.all` or equivalent concurrency primitives when
	operations do not depend on each other.

### Frontend Rules

- **Component Hierarchy**: Components MUST follow an
	Atom → Molecule → Organism hierarchy, with clear boundaries
	and reuse. Global state management MUST NOT be introduced
	without an explicit spec; if needed, a minimal store (for
	example Zustand) is the upper bound for complexity.
- **Performance Guardrails**: The primary application bundle
	MUST remain under 2MB gzipped. Routes and heavy features
	MUST be lazy-loaded. Components affecting large portions of
	the tree SHOULD be memoized where it measurably reduces
	re-renders. At least once per quarter, the team MUST review
	and document render performance and bundle size.

## DevOps Governance

- **CI/CD Pipeline**: GitHub Actions (or an equivalent CI) MUST
	run linting, tests, and build steps on every pull request.
	Production deploys to Vercel, Netlify, or an equivalent
	platform MUST only occur from green CI on protected branches.
	Security scans (for example Snyk or an equivalent) MUST run
	at least weekly. Production errors MUST be captured via a
	central error monitoring service (for example Sentry).
	Secrets MUST be supplied via environment variables or a
	dedicated secrets manager and MUST NOT be committed to the
	repository.
- **Spec Supremacy**: All changes MUST originate from
	`/speckit.specify` artifacts (for example specs, plans, and
	tasks). The codebase is treated as "compiled spec"; when
	code, infrastructure, or documentation diverge from the
	authoritative specs, they MUST either be reverted or the
	specs amended first.

## Governance

This constitution supersedes informal practices and ad-hoc
team preferences. All pull requests and reviews MUST consider
and, where relevant, explicitly cite principle compliance.

Amendments to this constitution MUST:

1. Be proposed via a `/speckit.specify` artifact that states
	 the motivation, impacted principles, and migration impact.
2. Undergo review and approval in the same manner as
	 production code (including CI checks where applicable).
3. Include an explicit version bump according to semantic
	 versioning:
	 - MAJOR: Backward-incompatible changes to principles or
		 governance (for example removing or redefining
		 non-negotiable rules).
	 - MINOR: Addition of new principles or sections, or
		 materially expanded guidance.
	 - PATCH: Clarifications and non-semantic refinements that
		 do not change obligations.

At least once per quarter, the team MUST review this
constitution for relevance against current technology and
project context (for example WASM adoption or major framework
changes) and propose amendments where needed.

AI agents generating code or documentation for this repository
MUST reference this constitution as a primary source of runtime
and design guidance. Human contributors SHOULD ensure that
prompts, scripts, and onboarding material link back to this
document.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): set original
ratification date | **Last Amended**: 2025-11-24
