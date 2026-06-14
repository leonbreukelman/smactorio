# Plan: Hermes fork-sync conflict detection routed through SmactorIO

Date: 2026-05-28
Worktree: `/tmp/rtx3070-hermes-fork-sync-smactorio`
Base: `origin/main` of `leonbreukelman/rtx3070-workshop-ops`
Review: adjusted after read-only Opus review saved at `signal-hub/docs/verification/2026-05-28-hermes-fork-sync-smactorio-opus-review.md`.

## Problem

`hermes update` is correctly conservative: it updates from Leon's fork and refuses to silently merge upstream when the fork has commits not present in `NousResearch/hermes-agent`. The existing hourly fork-sync script can detect conflicts, but conflict outcomes only appear in logs. SmactorIO is also not currently able to act on a Hermes fork conflict because the foreman is hard-coded around the Signal Hub repo/path/test policy and the systemd runtime has noisy/off-host refusal states.

## Desired behavior

1. A scheduled fork-sync check safely fetches `leonbreukelman/hermes-agent` and `NousResearch/hermes-agent`.
2. If Leon's fork can be fast-forwarded to upstream with no merge commit, the check fast-forwards and pushes without force.
3. If upstream requires any merge commit, whether clean or conflicted, the check leaves the fork unchanged and creates/updates one GitHub issue with structured non-secret evidence.
4. A Hermes-specific SmactorIO lane sees that issue, claims it, performs the merge/conflict resolution in an isolated worker checkout seeded from a dedicated SmactorIO mirror (not the live `/home/leonb/hermes` checkout), runs Hermes smokes/tests, opens a PR against Leon's fork, waits for checks, and merges only verified work.
5. If the issue is already satisfied, unsafe, or repeatedly failing, SmactorIO records evidence and blocks instead of mutating the fork.

## Implementation steps

### 1. Add a managed fork-sync publisher script

Add `signal-hub/scripts/hermes_fork_sync_check.py`.

Responsibilities:
- Defaults:
  - fork repo: `leonbreukelman/hermes-agent`
  - upstream repo: `NousResearch/hermes-agent`
  - local checkout/source for remote config only: `/home/leonb/hermes`
  - scratch clone root: `/home/leonb/.local/share/smactorio/fork-sync/hermes-agent`
  - conflict issue repo: `leonbreukelman/hermes-agent`
  - conflict title: `SmactorIO: verify Hermes upstream sync`
- Use a shared lock file with the Hermes SmactorIO lane so the checker and foreman cannot simultaneously push/update the same fork.
- Fetch `origin` and `upstream` in a throwaway clone/worktree without printing credentials.
- Compute fork/base/upstream SHAs.
- If already current, print JSON status and exit 0.
- If fast-forward is possible, fast-forward and push to origin using a refspec without `+` and without any `--force` flag, then exit 0.
- If a merge commit would be required, do not push from the checker. Simulate the merge in scratch space only to collect structured repo-relative conflict-file evidence, abort/clean scratch state, and create/update a SmactorIO issue.
- Issue body must be rendered from an allowlist of structured fields only:
  - fork SHA, upstream SHA, timestamp, conflict files or clean-merge-required marker, and command names (not raw stdout/stderr)
  - acceptance criteria for SmactorIO
  - stop conditions: no force-push, no secrets, no branch protection changes, no destructive repo operations
  - expected verification: Hermes update tests/smokes and relevant changed-path tests
- Add a final defense-in-depth assertion that rendered issue/comment text contains no absolute local paths and no token-shaped strings.
- Idempotency:
  - Search open issues by labels and parse a hidden marker `<!-- smactorio:hermes-fork-sync {json} -->` from issue bodies.
  - If one exists for the stable lane key, update body and add a fresh comment only when the upstream/fork SHA pair changed.
  - If search returns empty but create collides/races, reconcile to the oldest open issue with the marker instead of creating duplicates.
  - Otherwise create it with labels: `smactorio`, `autonomy:ready`, `risk:low`, `type:maintenance`, `area:hermes-fork-sync`.

Tests:
- Unit-test conflict/non-FF issue body rendering and no local-path/token leakage.
- Unit-test idempotent create/update using marker parsing and a fake command runner.
- Unit-test conflict handling does not leave scratch dirty/mid-merge and does not push.
- Unit-test fast-forward pushes contain no `+` refspec and no `--force` flag.

### 2. Generalize SmactorIO policy from Signal Hub only to repo-specific lanes

Modify `signal-hub/scripts/smactorio_policy.py` and `smactorio_issue_foreman.py`.

Add policy fields while preserving Signal Hub defaults:
- `allowed_change_prefixes`: currently `("signal-hub/", ".github/workflows/")`.
- `secret_scan_paths`: currently `(".github/workflows", "signal-hub")`.
- `secret_scan_changed_paths_only`: false by default.
- `verification_test_commands`: default Signal Hub unit suite command.
- `verification_test_cwd`: default `signal-hub`.
- `verification_artifact_prefixes`: replaces or aliases `foreman_artifact_prefixes`.
- `commit_pathspecs`: default `("signal-hub", ".github/workflows")`.
- `discard_verification_side_effect_pathspecs`: default `("signal-hub", ".github/workflows")`.

Add `policy_for_repo(repo: str) -> SmactorioPolicy`:
- Default keeps existing Signal Hub behavior for `leonbreukelman/rtx3070-workshop-ops`; unknown repos get a closed policy that claims/mutates nothing.
- Hermes lane for `leonbreukelman/hermes-agent`:
  - keep path scoping allowlist-based and derive allowed material paths from the issue marker's conflict-file list only; clean merge-commit cases with no conflict-file list block for human review instead of granting broad source access;
  - explicitly deny `.github/workflows/*`, `pyproject.toml`, `setup.py`, `setup.cfg`, `conftest.py`, runtime/cache/build/dist/node_modules paths, and secret-like paths unless a future separate high-trust lane is created;
  - scan only changed text files for secrets;
  - write verification artifacts under `.smactorio/verification/`;
  - commit repo paths through policy pathspecs while guards reject generated/runtime/forbidden paths;
  - use allowed Hermes roots `("/home/leonb/hermes/", "/home/leonb/projects/hermes-agent/")` so `/home/leonb/.local/bin/hermes` symlinks/wrappers resolving into those installs pass runtime preflight;
  - keep required host `rtx3070` and required attestation `SMACTORIO_RUNTIME_ATTEST=rtx3070-smactorio-systemd`.

Update foreman behavior:
- `main()` and `run_once()` should choose `policy_for_repo(repo)` when no policy is supplied; unknown repos fail closed and cannot be claimed.
- `run_verification()` should use policy fields instead of hard-coded Signal Hub paths and commands.
- `write_verification_artifact()` and `commit_all()` should use policy artifact/commit pathspecs.
- Keep `foreman_artifact_prefixes` as an explicit backward-compatible alias/property for the new `verification_artifact_prefixes` field until all call sites are migrated.
- Worker/reviewer prompts should say repository-specific checks instead of only "Signal Hub unit suite".
- Existing tests for Signal Hub behavior must continue to pass.

### 3. Add Hermes-specific systemd lane

Add:
- `signal-hub/infra/systemd/system/smactorio-hermes-fork.service`
- `signal-hub/infra/systemd/system/smactorio-hermes-fork.timer`
- `signal-hub/infra/systemd/user/hermes-fork-sync-check.service`
- `signal-hub/infra/systemd/user/hermes-fork-sync-check.timer`

Service design:
- `smactorio-hermes-fork.service` runs `smactorio_issue_foreman.py --repo leonbreukelman/hermes-agent --repo-root /home/leonb/.local/share/smactorio/repos/hermes-agent --base main --state-db /home/leonb/.local/state/smactorio/hermes-fork.sqlite`.
- The foreman prepares/fetches that dedicated SmactorIO seed clone if missing; it does not use `/home/leonb/hermes` as its mutable repo root.
- The actual issue work still happens in the foreman's existing per-run isolated checkout under SmactorIO share storage.
- It uses the same runtime attestation, GH config dir, dedicated Hermes home, `User=leonb`, and sandboxing posture as the main SmactorIO service.
- Add `ConditionHost=rtx3070` to avoid noisy refusal loops on 4090 while preserving runtime checks in code.
- Use a shared lock path such as `/home/leonb/.local/state/smactorio/hermes-fork.lock` for both the fork-sync checker and the Hermes foreman lane.
- Read/write paths include the dedicated SmactorIO seed clone, SmactorIO state/share/config, cache, and no broad home write access.
- The user timer runs `hermes_fork_sync_check.py` hourly and publishes non-FF/conflict work into `leonbreukelman/hermes-agent`.

Tests:
- Assert both systemd units carry `ConditionHost=rtx3070`, attestation, env file, lock file, repo/root arguments, and conservative read/write paths.

### 4. Runtime preflight fixes

Fix the observed policy/preflight failures without broadening too far:
- Keep the host gate on `rtx3070`.
- Keep provider allowlist as `xai`/`grok` for the rtx3070 worker profile.
- Allow Hermes binaries that resolve under `/home/leonb/hermes/` and `/home/leonb/projects/hermes-agent/` rather than allowing all of `/home/leonb/.local/bin`.
- Add tests showing `/home/leonb/.local/bin/hermes` can be accepted when it resolves to one of the allowed Hermes installs, but an unrelated binary remains rejected.
- Add tests that the Hermes lane rejects workflow files, packaging hooks, `conftest.py`, and token/cache/build/runtime paths unless a future explicit policy allows them.

### 5. Verification

Run targeted checks first:
- `python3 -m unittest signal-hub.tests.test_smactorio_policy -q`
- `python3 -m unittest signal-hub.tests.test_smactorio_issue_foreman -q`
- new `test_hermes_fork_sync_check.py`
- `python3 -m py_compile signal-hub/scripts/hermes_fork_sync_check.py signal-hub/scripts/smactorio_issue_foreman.py signal-hub/scripts/smactorio_policy.py`

Run safety checks:
- `python3 signal-hub/scripts/scan_for_secrets.py signal-hub/scripts signal-hub/tests signal-hub/infra/systemd`
- `git diff --check origin/main...HEAD`
- `git status --short --branch`

Optional live dry-runs when safe:
- `python3 signal-hub/scripts/hermes_fork_sync_check.py --dry-run --json`
- `python3 signal-hub/scripts/smactorio_issue_foreman.py --repo leonbreukelman/hermes-agent --repo-root /home/leonb/.local/share/smactorio/repos/hermes-agent --base main --dry-run`

## Non-goals / safety boundaries

- Do not force-push Leon's fork.
- Do not let the fork-sync checker itself resolve semantic conflicts.
- Do not let SmactorIO run on 4090 for this lane; 4090 may hold the repo but rtx3070 is the intended autonomous worker.
- Do not expose local paths, GH tokens, API keys, env values, or private logs in GitHub issues.
- Do not make the default Signal Hub SmactorIO lane less restrictive.

## Expected commit outcome

A single branch/commit in `leonbreukelman/rtx3070-workshop-ops` that:
- adds the fork-sync conflict issue publisher,
- adds a Hermes SmactorIO lane,
- keeps Signal Hub SmactorIO behavior compatible,
- adds tests for policy, issue publication, systemd units, and runtime preflight,
- leaves the worktree clean and ready to push/open a PR.
