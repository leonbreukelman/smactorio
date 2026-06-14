# SmactorIO Low-Risk Issue Eligibility Checklist

This document defines the minimal structure and labels required for a GitHub issue to be eligible for autonomous pickup by the SmactorIO runtime in this repository.

## Required Trigger Labels
- `smactorio`
- `autonomy:ready`
- `risk:low`

## Recommended Type Label
- `type:docs` (for documentation changes)
- `type:ops` (for operational / infrastructure changes)

## Required Sections in Issue Body
Every eligible low-risk SmactorIO issue **must** include:

1. **Goal** — Clear problem statement or improvement objective.
2. **Allowed Paths** — Explicit list of files/directories the worker may touch (scoped to `signal-hub/docs/` for pure docs work).
3. **Non-Goals / Guardrails** — Explicit out-of-scope items.
4. **Acceptance Criteria** — Measurable, testable outcomes.
5. **Verification Command(s)** — Safe, reproducible commands (e.g. unit tests, secret scans).
6. **Rollback Expectation** — How to revert the change if needed.
7. **Human-Blocker Conditions** — Any of the following make the issue ineligible for autonomous execution:
   - Requires 2FA / browser login
   - Involves secrets, credentials, or env dumps
   - Changes billing / spend / provider costs
   - Production deploys or destructive operations
   - Production / security / compliance risk
   - Ambiguous product judgment requiring human decision

## Evidence & Runtime Contract
The SmactorIO runtime is expected to produce evidence of work via:
- Claim comment on the issue
- Completion or blocked comment
- Linked PR (if code change)
- Verification artifact under `signal-hub/docs/verification/`
- Final issue state (closed or labeled appropriately)

## Verification
Run the following safe verification commands (narrow for docs-only change):

```bash
cd signal-hub
python3 -m unittest discover -s tests -q
python3 scripts/scan_for_secrets.py signal-hub
```

These commands validate that the repository remains in a clean, secret-free state and that existing tests continue to pass. No broader runtime behavior is modified by this checklist.

## Rollback
Delete or revert this Markdown file under `signal-hub/docs/`. No database or runtime state is affected.

This checklist itself was created as a low-risk SmactorIO-eligible documentation improvement.