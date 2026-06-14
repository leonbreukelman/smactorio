# SmactorIO Service RSVL-MR Review Record

Date: 2026-05-17
Status: reviewed; required edits incorporated into spec and plan
Target: replace `maei-orchestrator.service` with `smactorio.service` as the GitHub-issue-first runtime.

## User goal captured

Leon wants SmactorIO to become the runtime foreman:

```text
Open an issue in https://github.com/leonbreukelman/rtx3070-workshop-ops
-> SmactorIO notices it
-> SmactorIO works it through branch/code/tests/review/PR/evidence/merge when safe
-> repo stays clean
```

The design must preserve and improve the MÆI repo-discipline standard: no dirty repos, orphan branches, stash mess, runtime artifacts, fake evidence, or PR handoff to Leon.

## Preflight facts

- Repo: `/home/leonb/projects/rtx3070-workshop-ops`
- Branch: `main`, clean, tracking `origin/main` at inspection time
- Remote: `git@github.com:leonbreukelman/rtx3070-workshop-ops.git`
- Open issue: #1, labeled `smactorio`, `type:ops`, `autonomy:ready`, `risk:low`
- Current service: `maei-orchestrator.service` active/enabled as a system service
- Replacement service: `smactorio.service` absent
- Current SmactorIO runner: local SQLite action runner, not GitHub-issue-first

## RSVL-MR lanes

### Lane 1: MÆI pattern extraction

Useful patterns to reuse:

- persisted work state machine
- stable dedupe key
- leases and retry state
- append-only transitions
- attempt history
- delayed source acknowledgment/claiming
- deterministic issue-to-branch naming
- branch lifecycle guard
- stale issue re-check before dispatch
- startup recovery for expired leases
- small YAML/service config
- tests for queue state, idempotency, issue routing, branch lifecycle, and post-dispatch verification

Patterns to avoid:

- copying the full multipurpose MÆI orchestrator
- mixing GitHub polling and signal-store ingestion for the same event
- prompt-only repo discipline
- warning-only verification
- treating dry-run as real success
- storing runtime DB/logs/state inside the repo
- using stash as recovery
- reusing spent branches

### Lane 2: SmactorIO current-state inspection

What exists:

- existing source/test/docs under `signal-hub/`
- current runner: `scripts/smactorio_improvement_runner.py`
- runner tests: `tests/test_smactorio_improvement_runner.py`
- current runner can consume local queued DB actions and stop at `ready_for_operator`
- current runner does not create branch/commit/push/PR/merge
- current local DB inbox is empty

Recommended smallest first slice:

- add policy/config skeleton
- add `scripts/smactorio_issue_foreman.py`
- add `tests/test_smactorio_issue_foreman.py`
- run in dry-run mode first
- select GitHub issue #1 from labels, no side effects
- do not install/enable systemd yet

### Lane 3: Failure-mode review

Top risks:

- MÆI and SmactorIO both running issue work
- fake dashboard/runtime progress without GitHub deliverables
- dirty repo/stash/orphan branch mess
- spent branch reuse
- crash after claim causing stuck work
- issue-body prompt injection
- `risk:low` issue causing broad infra/credential changes
- secrets/runtime artifacts committed or leaked in comments
- runaway retries/spend
- bad systemd restart loop

Mandatory gates:

- one foreman active
- GitHub visible state for meaningful transitions
- strict issue eligibility
- atomic GitHub-backed claim
- clean repo/no stash/no forbidden files
- isolated per-issue worktree
- worker has no broad secrets or push authority
- forbidden path/action denylist
- test/secret/path/CI evidence before PR success
- independent review/verifier before merge
- bounded repair loop for failed CI/review
- merge only after CI/review/label gates
- issue closure/comment evidence after merge
- branch/worktree cleanup after success/failure
- spend/retry caps
- systemd dry-run before execution mode

## Independent adversarial review findings

An independent review found these required corrections:

1. Add a hard no-handoff rule: SmactorIO/Hermes must not stop by asking Leon to review code/PRs.
2. Fix migration ordering: MÆI may remain active only during dry-run; live SmactorIO mutation requires MÆI inactive or proven non-mutating/scope-disjoint.
3. Define exact GitHub claim labels/comments, lease expiry, conflict handling, stale recovery, and tests.
4. Add review/repair loop before auto-merge.
5. Add independent verifier/review worker before merge.
6. Make worker authority boundaries explicit: no GitHub mutation, no push authority, scrub secrets.
7. Replace broad `/home/leonb/.hermes/.env` service EnvironmentFile with dedicated minimal SmactorIO credential file.
8. Add concrete GitHub auth, branch protection, and check preflight.
9. Make required CI checks exact and head-SHA-bound.
10. Run path-scope/runtime-artifact gates before PR and merge.
11. Clarify service-unit exception policy as a dedicated migration phase, not ordinary low-risk work.
12. Replace vague “policy permits” wording with repo-stored config/labels/gates.
13. Add issue closure/completion evidence requirements.
14. Add branch/worktree cleanup gates.
15. Make repo cleanliness measurable with `git status --porcelain=v1 --untracked-files=all` and stash-delta checks.
16. Add concrete spend/retry/runtime caps.
17. Harden systemd service with timeouts, lock, minimal env, verification, and MÆI inactive preflight.
18. Add command-injection tests for issue title/body and worker command argv.
19. Add GitHub-visible redacted failure evidence for aborts after issue selection.
20. Update this review record from pending to reviewed.

Resolution: incorporated into:

- `signal-hub/docs/specs/2026-05-17-smactorio-service-github-issue-runtime-spec.md`
- `signal-hub/docs/plans/2026-05-17-smactorio-service-github-issue-runtime-plan.md`

## Synthesis decision

Chosen approach:

Build SmactorIO as a narrow GitHub issue foreman, not as a copy of the entire MÆI orchestrator.

Why:

- It matches Leon's simple mental model.
- It uses GitHub as the visible source of truth.
- It reuses MÆI's strongest lessons without importing MÆI's complexity.
- It makes repo discipline enforceable in code.
- It gives a safe migration path from MÆI service to SmactorIO service.
- It keeps the no-handoff rule explicit: SmactorIO/Hermes delivers verified merged work or quarantines with evidence.

Rejected alternatives:

1. Keep evolving the local SQLite action runner.
   - Rejected because it does not consume GitHub issues directly and hides the real work queue from GitHub.
2. Copy the whole MÆI orchestrator.
   - Rejected because it brings timers, blackboard, cortex/janitor lanes, and complexity the user explicitly does not want.
3. Disable MÆI immediately before SmactorIO is proven.
   - Rejected because dry-run can proceed safely first, while live mutation requires MÆI inactive or proven non-mutating.
4. Start with auto-merge/service installation.
   - Rejected because dry-run and one controlled branch/PR/evidence path must prove safety first.

## Artifacts produced

- Spec: `signal-hub/docs/specs/2026-05-17-smactorio-service-github-issue-runtime-spec.md`
- Plan: `signal-hub/docs/plans/2026-05-17-smactorio-service-github-issue-runtime-plan.md`
- Review record: `signal-hub/docs/verification/2026-05-17-smactorio-service-rsvl-mr-review.md`

## Implementation-ready slice

Start with Milestone 0 and Milestone 1 from the plan:

```text
Policy is explicit.
GitHub issue #1 is visible to SmactorIO.
SmactorIO can select it safely.
No side effects happen yet.
The old local SQLite candidate machinery is no longer the future inbox.
```

No blocker exists for that first implementation slice.
