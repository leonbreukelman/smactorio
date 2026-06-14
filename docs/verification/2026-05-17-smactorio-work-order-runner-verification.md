# SmactorIO work-order runner verification

Generated: 2026-05-17T00:04:42Z
Review-fix update: 2026-05-17T00:30:39Z

## Scope

This PR wires the existing SmactorIO improvement runner to consume one queued low-risk SmactorIO action from `state/signal_loop.db` as a bounded work order.

The runtime runner does not create branches, issues, commits, pushes, or PRs. It selects and claims one queued action, records the intended GitHub lifecycle as local evidence, runs exact allowlisted local checks, and moves the action to either `ready_for_operator` or `blocked`.

## Safety decisions

- Runtime state, logs, DB files, caches, backups, env files, and credentials were not staged.
- Work-order checks are exact allowlisted commands; no shell execution is used.
- A final tracked-worktree cleanliness check runs from nested project roots as well as repo roots.
- If Git metadata is unavailable, `tracked_worktree_clean` now records an explicit failed check and blocks the work order instead of silently skipping the safety proof.
- SQLite write transactions are not held while subprocess checks run.
- Claimed work orders are recovered to `blocked` with evidence if post-claim finalization fails.
- Startup reconciliation now blocks a stale prior `risk_checked` SmactorIO work order with evidence before claiming any new queued work order.
- Finalization refuses to overwrite a concurrent/operator status change.

## Verification

- `python3 -m unittest tests.test_smactorio_improvement_runner -v` -> 21 tests passed, including review-fix regressions for missing Git metadata and stale `risk_checked` recovery.
- `python3 -m unittest discover -s tests -q` from `signal-hub/` -> 170 tests passed.
- Independent adversarial review of the review-fix diff -> ACCEPT.
- `git diff --check` -> clean.
- Scoped secret scan -> no findings.
- GitHub guardrails -> passed before review fixes; re-check required on the pushed review-fix commit.

## Remaining work

The next slice should move from local ready-for-operator evidence to a separately reviewed PR path that actually creates the implementation branch/commit/PR for a selected work order. This runner remains intentionally bounded and non-mutating outside local DB evidence.
