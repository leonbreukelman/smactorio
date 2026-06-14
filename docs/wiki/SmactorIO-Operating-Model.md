# SmactorIO Operating Model

## Purpose
Describe how autonomous work is driven by GitHub Issues.

## Audience
Humans and AI agents

## Source of truth
signal-hub/docs/wiki/SmactorIO-Operating-Model.md

## Last verified date
2026-05-17

## Human summary
Issues with specific labels are picked up by SmactorIO for autonomous execution.

## Agent guidance

**Agent contract:**
- Allowed actions: Implement per issue requirements in isolated worktree.
- Prohibited actions: Direct GitHub writes.
- Required checks: All guardrails and verification.
- Evidence to leave: Local commit + verification artifact.
- Stop/block conditions: Fail-closed on security or ambiguity.

## Issue eligibility labels
- smactorio
- autonomy:ready
- risk:low

## Blocked/done/claimed label meanings
- smactorio:claimed : Worker is active
- smactorio:blocked : Needs human intervention
- smactorio:done : Completed and merged

## Lifecycle
Issue -> claim -> worker (disposable checkout) -> verification -> review -> PR -> CI -> merge -> evidence comment

## Fail-closed conditions
Any guardrail failure, secret detection, or scope violation blocks progress.

## How SmactorIO comments evidence back
Via foreman after successful merge.

## Related pages
- [Agent-Start-Here.md](Agent-Start-Here.md)
- [Development-and-Verification.md](Development-and-Verification.md)