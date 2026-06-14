# SmactorIO GitHub Issue Runtime Implementation Verification

Date: 2026-05-17
Branch: `smactorio/github-issue-runtime`
Issue: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/1

## Delivered runtime

- Added `scripts/smactorio_issue_foreman.py` as the SmactorIO foreman.
- Added `scripts/smactorio_policy.py` for bounded autonomous issue selection.
- Added `scripts/smactorio_repo_guard.py` for clean-worktree/stash/branch discipline.
- Added `scripts/smactorio_runtime_state.py` for SQLite runtime state outside the repo.
- Added hardened systemd units under `signal-hub/infra/systemd/system/` and an installer/provisioner at `signal-hub/scripts/install_smactorio_service.sh`.
- The installer creates `/home/leonb/.config/smactorio/env`, writes GitHub auth from `gh auth token` without printing it, provisions a dedicated SmactorIO `HERMES_HOME`, copies Hermes config, and filters GitHub/SSH/cloud/admin credentials out of the worker-facing `.env`.
- Added worker sandboxing with bubblewrap so the worker sees the isolated checkout, a temporary HOME, and a dedicated SmactorIO Hermes home instead of Leon's normal home, GitHub CLI config, SSH keys, or foreman GitHub token.
- The worker checkout is a disposable full local clone with its own `.git` directory; this avoids exposing the canonical repo's `.git` metadata and prevents linked-worktree git failures inside the sandbox.
- The service preflight refuses to run the non-dry-run runtime while `maei-orchestrator.service` is still active, so migration cutover cannot accidentally run both orchestrators at once.
- Issue intake is fail-closed: a ticket must carry `smactorio`, `autonomy:ready`, and `risk:low`, must not carry blocked/high-risk labels, must not contain explicit forbidden high-risk phrases, and is reloaded/rechecked immediately before claim.
- Open PRs are checked before claim so SmactorIO does not start duplicate work for an issue that already has an active PR.
- Branch names include a longer run-id suffix, pushes are non-force, and remote branches are best-effort deleted if a post-push failure blocks the run.
- Added local branch cleanup and disposable checkout cleanup so SmactorIO issue branches/checkouts do not become local orphans.
- Removed admin merge override; SmactorIO blocks with evidence instead of bypassing branch protection.
- Local verification uses trusted guardrail scripts from the installed service checkout, not worker-modified guardrail scripts from the issue worktree, runs with GitHub/SSH credential env removed, and is repeated after the verification artifact commit so the final PR head is what was checked.
- Foreman privileged git steps rewrite the worker `.git/config` from scratch and remove hooks before verification, commit, or push.
- Canonical repo update uses token-backed HTTPS fetch/pull through `GIT_ASKPASS`, so the hardened service does not depend on `/home/leonb/.ssh` or SSH agent access.
- The PR merge gate requires the exact `signal-hub-guardrails` check to complete with `SUCCESS`; skipped/neutral/substring-matched checks do not pass.
- The runtime performs an independent read-only Hermes review after local verification and before push/PR creation; it requires `SMACTORIO_VERDICT: PASS` and fails if the reviewer modifies the checkout.
- PR merge uses `gh pr merge --match-head-commit <verified-sha>` after head-bound check verification, closing the post-check race window.
- Stale-claim recovery removes expired `smactorio:claimed` labels so a crash does not block an issue forever.
- Added tests proving required ready/low-risk issue selection, shell-safe/low-collision branch naming, dry-run no-write behavior, exact fail-closed PR guardrail gating, head-SHA matched merge, independent review pass-marker enforcement, token-backed HTTPS repo update, worker credential scrubbing, argv-only worker commands, worker sandbox wrapping, sandboxed Hermes startup, sandboxed git operation in a full worker clone, worker `.git` metadata lockdown, repo guard behavior, external runtime state, claim markers, and systemd hardening.

## Runtime contract

The service watches GitHub issues in `leonbreukelman/rtx3070-workshop-ops`, selects one eligible open issue, claims it, creates an isolated worktree/branch, runs a worker, verifies local checks, opens a PR, waits for checks, merges the PR, comments evidence, labels the issue done, and cleans up the worktree.

The worker is not the GitHub merge operator.  The foreman owns push/PR/merge/evidence so Leon is not handed developer work.

## Local verification before PR

Commands run:

```text
python3 -m unittest tests.test_smactorio_issue_foreman -q
python3 - <<'PY'
# bubblewrap smoke: worker can start hermes --help, sees temp HOME, and has no GitHub token
PY
bash -n signal-hub/scripts/install_smactorio_service.sh
systemd-analyze verify signal-hub/infra/systemd/system/smactorio.service signal-hub/infra/systemd/system/smactorio.timer
python3 scripts/smactorio_issue_foreman.py --dry-run --repo leonbreukelman/rtx3070-workshop-ops --repo-root /home/leonb/projects/rtx3070-workshop-ops --state-db /home/leonb/.local/state/smactorio/test.sqlite
python3 -m unittest discover -s tests -q
git diff --check
python3 signal-hub/scripts/scan_for_secrets.py signal-hub/scripts/smactorio_issue_foreman.py signal-hub/scripts/smactorio_policy.py signal-hub/scripts/smactorio_repo_guard.py signal-hub/scripts/smactorio_runtime_state.py signal-hub/tests/test_smactorio_issue_foreman.py signal-hub/infra/systemd
python3 signal-hub/scripts/check_path_scope.py --from-file /tmp/smactorio-runtime-changed-paths.txt --allow-prefix signal-hub/ --allow-prefix .github/workflows/
```

Observed status before PR packaging:

- Targeted runtime tests: passed.
- Systemd unit verification: passed.
- Dry-run issue selection: selected issue #1 and performed no GitHub writes.
- Signal Hub unit suite: passed after reverting generated public test outputs.
- Whitespace check: passed.
- Secret scan: passed.
- Changed-path scope check: passed.
