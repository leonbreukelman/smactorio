# SmactorIO manual FSM walkthrough — Track 001

Created: 2026-05-15T01:04:03Z
Updated: 2026-05-15T01:25:39Z
Project: SmactorIO / autonomous project operating system
Status: active manual walkthrough

This file is the current SmactorIO-named walkthrough and supersedes the earlier piOS-named bootstrap artifact.

## Operating format

Each FSM state is documented with two roles:

1. Operator: performs a real action and records the actual artifact changed or observed.
2. Commentator: explains what happened and why, concisely.

Each state must show:

- Input: exact user/project input entering the state.
- Processing: what was normalized, checked, rejected, accepted, or transformed.
- Output: concrete artifact, file, state row, page, test result, or decision.
- Evidence: command result, file path, URL, hash, or verification result.
- Next state: where the FSM moves next.

## State 000 — INTAKE_AND_NAME_CHECK

Operator action:
- Captured Leon's initial proposal to use a pi-derived OS name as the example project track.
- Verified pi value/symbol locally.
- Checked live web context for name collision risk.
- Created the first walkthrough and capsule artifacts.

Input:
```text
Use pi + OS as the example project, and have Hermes act as both operator and commentator while manually stepping through the FSM with real effects.
```

Processing:
- Normalized the umbrella concept from Signal Hub to Project OS.
- Preserved Signal Hub as the current module/surface rather than the whole system name.
- Flagged naming ambiguity: Pi OS commonly points to Raspberry Pi OS.

Output:
- Initial provisional name rejected by Leon in the next state.
- Module name retained: Signal Hub.
- Next FSM state: NAME_REFACTOR_AND_PROJECT_CONTRACT.

Evidence:
- Local math check output: `3.141592653589793` and `π`.
- Web check returned Raspberry Pi OS as the dominant public collision for Pi OS.
- Earlier bootstrap artifact: `docs/walkthroughs/2026-05-15-pios-fsm-track-001.md`.

## State 001 — NAME_REFACTOR_AND_PROJECT_CONTRACT

Operator action:
- Replaced the pi-derived working name with SmactorIO per Leon's direction.
- Checked name reuse boundary and kept only the name, not old project content.
- Wrote a concrete SmactorIO autonomous project operating contract.
- Wrote a redacted internal work capsule for the contract.

Input:
```text
Avoid the piOS issue. Reuse SmactorIO. Refactor the north star to add more autonomy by intelligently testing and quantifying perceived boundary blockers instead of accepting superficial risk prose.
```

Processing:
- Preserved Signal Hub as the current private LAN intelligence/status surface.
- Promoted SmactorIO to the umbrella autonomous project operating system name.
- Reframed blockers as testable risk claims with assets, mechanisms, blast radius, max loss, reversibility, probes, evidence, residual risk, and autonomy decision.
- Defined an authority envelope: proceed autonomously when measured residual risk is inside bounds; ask Leon only for high/unknown residual risk, real spend, public/external mutation, destructive/irreversible changes, or product judgment.

Output:
- Contract artifact: `docs/contracts/2026-05-15-smactorio-autonomy-contract.md`.
- Capsule artifact: `data/internal_work_capsules/smactorio-contract-2026-05-15.json`.
- Current walkthrough artifact: `docs/walkthroughs/2026-05-15-smactorio-fsm-track-001.md`.
- Next FSM state: INGEST_CONTRACT_AND_VERIFY_IDEMPOTENCY.

Evidence:
- Name-reuse check: earlier same-name SmactorIO material is retired/non-canonical and was not imported.
- Public web check showed existing Smactory names, but SmactorIO remains the better reused project-specific name than the pi-derived option.

Commentator note:
- This state changes the contract from cautious autonomy to evidence-seeking autonomy. The loop should not stop at "risky"; it should prove what is actually at risk, reduce uncertainty, and only escalate the irreducible remainder.

## State 002 — INGEST_CONTRACT_AND_VERIFY_IDEMPOTENCY

Operator action:
- Backed up the SQLite state before mutation.
- Tried to ingest the SmactorIO contract capsule.
- Hit a real validation blocker: the secret scanner quarantined the capsule because a hyphenated phrase accidentally matched an OpenAI-key-shaped substring.
- Treated that as a real blocker test, not prose: inspected the exact scanner match, removed the unsafe substring shape, reran validation, then ingested successfully.
- Ran ingestion twice after the fix to prove idempotency.
- Secret-scanned the contract, capsule, and walkthrough.

Input:
```text
SmactorIO contract capsule at data/internal_work_capsules/smactorio-contract-2026-05-15.json
```

Processing:
- Before retry: `internal_work_capsules=2`, `source_candidates=5`.
- First ingest result: quarantined with reason category `openai_key`.
- Fix: changed the unsafe hyphenated label to `risk_scoring` and removed absolute local path references from capsule evidence labels.
- Successful ingest run 1: valid=1, quarantined=0.
- Successful ingest run 2: valid=1, quarantined=0.

Output:
- SQLite capsule row is now valid and redacted.
- No source-candidate row is used for the earlier same-name SmactorIO repository; that old project is retired/non-canonical unless Leon explicitly reauthorizes a named pattern extraction.
- Idempotency verified: second successful ingest did not add another capsule.

Evidence:
- Backup: `state/runtime_backups/smactorio-contract-before-ingest-20260515T012539Z.db`.
- After valid ingest: `internal_work_capsules=3`.
- Capsule row: `manual-2026-05-15-smactorio-contract`, project `signal-hub`, status `valid`, redaction `redacted`, quarantine reason `null`.
- Secret scan output over touched artifacts: `[]`.
- Contract hash: `6a8e3578830a08d607b8231196e67a1e531f5ba4cabf8c27e435bb95eb1bb1e5`.
- Capsule hash: `47301ae683a953bdee052018706385fab0758e34671c2f4716c30cbc5ff1b31a`.

Commentator note:
- This is exactly why the blocker-testing contract matters. The system found a boundary issue, identified the actual mechanism, fixed the input, and continued safely without asking Leon to adjudicate a fake emergency.

Next FSM state:
- RENDER_CONTRACT_TO_PROJECT_STATE_SURFACE.
