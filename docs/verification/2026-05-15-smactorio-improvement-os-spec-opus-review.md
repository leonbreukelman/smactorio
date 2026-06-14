# Opus Review — SmactorIO Improvement OS Spec

Review date: 2026-05-15T03:56:01Z
Reviewer: Claude Code Opus, read-only, max effort
Verdict: ACCEPT_WITH_CHANGES

## Summary

Opus accepted the overall structure but found implementation-blocking ambiguity that could let the first implementation become a Potemkin loop: a runner that merely records that it can record improvements, without executing a concrete improvement.

## Required changes incorporated into the revised spec

1. First run must make one concrete file mutation outside `state/smactorio/`, with before/after hashes and visible cockpit proof.
2. Candidate records now require a structured `execution` block instead of a free-text action.
3. Idempotency hash now uses a canonical projection that excludes mutable status, scores, timestamps, journal, and run records.
4. Runner gets a lock file to prevent manual/scheduled concurrency corruption.
5. Scheduler integration is pinned: run after `SYNTHESIZE_DAILY_BRIEF` and before page rebuild/publish.
6. Operating loop calls the runner as a subprocess with a JSON stdout contract and explicit exit-code handling.
7. Evidence/proof are explicitly defined.
8. Governance now has path/action allowlists, not just recorded intent.
9. v1 forbids live LLM calls and new outbound network calls.
10. Tests now include hash determinism, concurrency, operating-loop integration, page rebuild failure, governance enforcement, and HTTP freshness.
11. Path differences between local source checkout and live rtx3070 checkout are explicit.
12. Backup format and retention are explicit.
13. Open questions were closed with recommended defaults.

## Full Opus report

```text
# Adversarial Spec Review: SmactorIO Improvement OS

## Verdict

ACCEPT_WITH_CHANGES — Structure is solid and the governance instincts are right, but at least 7 implementation-blocking ambiguities and one fundamental "is the demo real?" question will let an implementer claim victory by tomorrow while building a Potemkin loop. None of the blockers are large, but they must be closed before code starts.

## Top blockers / required changes

1. First-run is circular. The first run needs a concrete file mutation and execution mechanism.
2. Idempotency hash is under-specified and will self-break.
3. Path / working-directory mismatch between local source checkout and rtx3070 live checkout.
4. Scheduler insertion point not pinned and invocation semantics undefined.
5. No concurrency control.
6. Evidence / proof are never defined.
7. Governance rule has no enforcement.
8. Verification commands need confirmation.

## Important improvements

- Add runner timeout.
- Define run-record schema and retention.
- Define backup format and retention.
- Define page-rebuild failure handling.
- Define negative-priority handling.
- Add internal path allowlist.
- Surface last_run_at and next_scheduled_at.
- Forbid live LLM calls in v1 explicitly.
- Define whether candidate tests are advisory or gating.

## Missing tests

- Hash determinism.
- End-to-end idempotency.
- Operating-loop integration.
- Lock/concurrency.
- Backup round trip.
- Page-rebuild-failure recovery.
- Schema rejection.
- Governance enforcement.
- HTTP marker/freshness.
- run_operating_loop dry-run marker.
- Secret-scan scope.
- systemd unit validity if units change.

## Suggested spec edits

- Require concrete file mutation outside state with before/after hashes.
- Add candidate `execution` block and idempotency projection.
- Auto-park priority below 1.
- Enforce strategy write allowlists.
- Pin canonical hash projection.
- Add lock file, timeout, stdout JSON contract, exit codes.
- Pin scheduler insertion after daily brief synthesis and before page rebuild.
- Add missing tests.
- Define tarball backup and retention.
- Reconcile dev path vs rtx3070 path.
- Define working SmactorIO as a run with a real diff record.
- Forbid live LLM/network calls in v1.
- Close open questions before coding.
```
