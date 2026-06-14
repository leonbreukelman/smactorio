# SmactorIO autonomous project operating contract

Created: 2026-05-15T01:23:34Z
Status: draft contract, manually accepted for FSM walkthrough unless Leon changes wording
Project surface: Signal Hub / SmactorIO project-intelligence loop

## Name

Working name: SmactorIO

Name rationale:
- Reuses Leon's prior Smart Factory -> Smactory -> SmactorIO lineage.
- Avoids the Pi OS / Raspberry Pi OS naming collision.
- Keeps a useful meaning: a smart actor I/O system that turns goals, signals, and verified actions into project motion.

Name boundary:
- SmactorIO is the umbrella autonomous project operating system.
- Signal Hub is the current private LAN intelligence/status surface inside SmactorIO.
- The earlier same-name SmactorIO governance/SDD project is retired and non-canonical. Reusing the name does not import that project's meaning, roadmap, repo contents, compliance/governance material, or implementation assumptions unless Leon explicitly reauthorizes a specific pattern.

## Refactored north star

Build a private autonomous project operating system that moves Leon's active projects toward clearly defined goals by maintaining living project state, ingesting internal and external signals, testing claimed blockers against real evidence, quantifying residual risk, routing safe actions, verifying outcomes, and surfacing only the decisions where measured risk or value judgment still genuinely requires human authority.

Short form:

SmactorIO converts goals into verified project motion by keeping state, testing blockers, quantifying real risk, acting inside the proven safety envelope, and asking Leon only for decisions that remain materially human after evidence-gathering.

## Core autonomy principle

A blocker is not accepted because it sounds risky. A blocker is accepted only after SmactorIO has converted it into a testable risk claim and run the safest available probes.

Default behavior:
1. Treat blocker language as a hypothesis, not a stop sign.
2. Identify the actual asset at risk.
3. Estimate maximum exposure.
4. Run non-destructive probes first.
5. Add reversible containment before mutation.
6. Quantify residual risk after evidence.
7. Proceed autonomously when residual risk is inside the authority envelope.
8. Ask Leon only when the remaining risk, cost, irreversibility, or product judgment crosses the explicit boundary.

## Risk quantization contract

Every perceived boundary blocker must be represented as a `risk_claim` with these fields:

- `claim`: concise blocker statement.
- `action_under_consideration`: the concrete action the blocker might prevent.
- `asset_at_risk`: credentials, money, data, project state, public reputation, external account, customer/user data, local runtime, etc.
- `risk_mechanism`: how harm would actually occur.
- `blast_radius`: local file, repo, LAN service, public internet, paid account, social account, production system, etc.
- `max_loss`: bounded estimate in dollars, files, records, services, time, or reputation class.
- `reversibility`: reversible, restorable-from-backup, partially reversible, irreversible.
- `probability_before_probe`: low, medium, high, unknown.
- `probe_plan`: dry-run, read-only API check, permission check, sandbox run, diff preview, backup/restore test, cost lookup, canary, secret scan, browser smoke, unit test, or independent review.
- `evidence`: command output, file path, URL, hash, DB row, test result, API response metadata, or screenshot path.
- `residual_risk`: low, medium, high, unknown after probes.
- `autonomy_decision`: proceed, proceed_with_guardrails, park, ask_leon, blocked.
- `reason`: why the decision follows from measured evidence.

## Action authority envelope

Autonomous by default when all are true:
- Action is local/private/LAN-only or read-only external.
- No raw secrets or raw transcripts are exposed.
- No public posting, public deployment, external account mutation, paid spend, destructive delete, or irreversible migration occurs.
- Backup, dry-run, test, diff, or rollback path exists when state is mutated.
- Residual risk is low or bounded-medium with explicit guardrails.
- The action advances a recorded project goal.

Ask Leon when any are true:
- Residual risk remains high or unknown after reasonable probes.
- The action spends money, enables billing, or risks meaningful API burn.
- The action mutates public/social/external accounts.
- The action deletes data, rewrites history, migrates production, or is hard to reverse.
- The action is mostly product/value judgment rather than operational execution.
- The available probe would itself create the risky side effect.

## Blocker-testing examples

| Superficial blocker | SmactorIO test | Possible autonomous result |
| --- | --- | --- |
| "This might cost money" | Fetch pricing, estimate calls, set cap, run zero/one-call smoke only if within cap | Proceed under cap or ask if spend exceeds threshold |
| "This might delete data" | Enumerate target paths, backup, dry-run, restore test, scoped path allowlist | Proceed with reversible scoped mutation or ask if irreversible |
| "This might leak secrets" | Redact before render, scan source/output, verify no secret-like patterns, avoid raw logs | Proceed if scan clean; quarantine if not |
| "This might break the live page" | Build locally, compare hashes, smoke generated page, preserve previous good page | Publish if verified; preserve previous if failed |
| "This may be a product decision" | Produce evidence-backed alternatives and local draft without changing public state | Ask Leon only for final preference |

## Contract outputs for each FSM state

Every SmactorIO FSM state must produce:
- input record
- processing record
- output artifact or state change
- risk claims considered
- probes run
- evidence links
- autonomy decision
- next state

## First contract acceptance criteria

This contract is useful when:
- It reduces vague permission prompts.
- It turns blocker prose into measurable risk claims.
- It lets Hermes continue low-risk work after proving the actual boundary.
- It preserves Leon's authority for real high-risk or value-judgment decisions.
- It creates artifacts and evidence, not just commentary.
