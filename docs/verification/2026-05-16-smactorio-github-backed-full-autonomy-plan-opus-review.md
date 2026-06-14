# Opus Adversarial Review: SmactorIO GitHub-backed Full Autonomy Plan

Source reviewed: `docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan.md`
Reviewer: Claude Opus via Claude Code
Date: 2026-05-16

# Adversarial Review — SmactorIO GitHub-backed Full Autonomy Plan

## 1. Verdict

**Approve with changes.** The plan correctly scopes the current slice to docs/site/bootstrap and defers runtime FSM work, and it covers the right phases at the right level. But several places leave enough ambiguity that an autonomous agent could pass acceptance checks while still creating duplicate issues, leaking state, bypassing review, or overwriting the remote. The Phase 0 reconciliation, dedup key, score scale, locking, and PR/merge policy must be tightened before any runtime phase is executed.

## 2. Blocking flaws

These would cause unsafe or chaotic autonomy if implemented as written.

1. **Phase 0 sync is undefined and bidirectional-unsafe.** "Compare current local … against remote signal-hub/ baseline. Sync source files needed for docs/site/tests/builders." The local tree is *not* a checkout of the remote, and the remote already contains content. An autonomous agent could (a) blindly copy local → remote and clobber remote-only files, or (b) interpret "sync" as `rsync --delete`. No explicit path mapping `leon-signal-hub/<x>` ↔ `signal-hub/<x>` is given, no divergence audit step is required, and no "do not delete remote-only files" rule is stated.
2. **PR vs direct-push policy is left to the agent.** Phase 0 task 10: "Create a PR **or**, if the repo policy is intentionally direct-private, push a verified checkpoint." An adversarial agent will choose the cheaper path (direct push to `main`). The plan also does not require branch protection on `main`, nor a distinct bot identity, nor a rule that the agent may not both author and merge its own PR.
3. **Dedup key is under-specified.** `<!-- smactor:dedup=<sha256> -->` does not say sha256 *of what*. Title? Title+body? Normalized title? An agent will pick whichever yields convenient non-collision and create near-duplicates by changing trivial body text. The plan needs a normalized canonical string definition and a documented test that two semantically equal candidates collide.
4. **Priority score has no scale, no bounds, no tie-break.** Phase 4 sets `min_autonomous_score = 6` but the formula sums/subtracts seven undefined terms. 6 of what? 0–10 axes? 0–100? Unbounded integer? An autonomous scorer can trivially clear or trivially fail the threshold depending on interpretation. Also no per-axis floor (e.g. impact must be ≥ N) and no tie-break rule, so selection becomes nondeterministic across two Candidates with identical scores.
5. **Single-writer lock has no mechanism.** "Add a single-writer lock" without naming flock / DB row / lease+ttl / stale-lock recovery is not enough. Two cron-triggered runs will both think they hold the lock if the first crashed without releasing.
6. **Review phase has no provenance.** Phase 6 requires `spec_review` and `plan_review` artifacts, but does not require that the reviewer be a *different* actor than the implementer, nor that the artifact include a verifiable model/agent identity. An autonomous agent can write its own `*_review.md` and self-approve.
7. **"Patch the spec for Opus blockers" is editing the spec from inside the loop.** Phase 1 tasks 3 and 6 let the same actor amend the spec and the plan that are being reviewed. There must be a rule that spec/plan revisions after the Opus review go into a new dated file (`-v2.md`) rather than mutating the reviewed artifact, otherwise the audit trail is rewritable.

## 3. Missing tests / acceptance criteria

- No test asserts the **path scope and denylist** are honored — e.g. a unit/CI check that runs `git ls-files | grep -E '^(state/|.*\.db$|.*\.sqlite.*$|logs/|\.env)'` and fails if non-empty. Phase 0 acceptance ("Runtime state remains ignored/uncommitted") is asserted but not enforced.
- No **secret scan tool/baseline** is named. "Secret scan is clean" is meaningless without naming the scanner, ruleset, and how exceptions are recorded.
- No **dedup-collision test** for the candidate key (see flaw 3).
- No **priority-score golden fixture** path is named, despite Phase 4 acceptance "reproducible from a fixture."
- No **idempotency assertion** for the two consecutive `--dry-run` invocations at the end of Verification. The plan runs the loop twice but does not say *what must match* between runs (state trace? selected candidate id? no new issue created?).
- No **page marker test contract**. Phase 2 lists strings but does not require a structured marker (e.g. `<meta name="smactor:marker" content="priority-gate">`) so any agent can satisfy the test by inserting the literal string anywhere on the page.
- No **runner timeout/hang test**. Phase 5 says subprocess failure must not crash the loop, but a hung runner with no timeout will stall the FSM indefinitely.
- No **issue-volume cap**. Nothing prevents an agent from filing 50 candidate issues in one run.
- No **starvation test** for the priority queue. Tie-break and aging policy is unspecified, so an old P3 issue can be perpetually outranked by churning P2s.

## 4. Rollback / GitHub lifecycle concerns

- **Reverting on `main` is conditionally allowed** ("only if direct-private repo policy allows it"). An autonomous agent will read that as "yes." Default should be: revert always lands via a branch+PR, never direct-to-main, regardless of repo privacy.
- **No protected-branch requirement** is stated. Without `main` protection, `git revert` and `git push --force` are both indistinguishable in policy.
- **Tag immutability is not enforced.** Phase rollback uses `smactor/<yyyy-mm-dd>-<short-slug>` tags as anchors, but nothing forbids an agent from moving or deleting a tag.
- **Issue lifecycle on rollback is hand-wavy.** "Update the SmactorIO issue/page proof if needed" — there must be an explicit rule: on revert, the originating Candidate's issue is reopened with a `rollback` label and the proof page shows the revert SHA. Otherwise the GitHub backlog desyncs from git history.
- **Stale candidate cleanup is missing.** Candidates that are superseded or killed are never closed. Over time the queue accumulates ghost issues that still match selection.
- **Branch reuse semantics are missing.** Phase 3 mentions "branch/PR reuse" but does not say: same dedup key reuses the same branch name, force-push to that branch is forbidden, and the prior PR must be reopened (not duplicated) if it was closed.
- **No commit author identity rule.** Autonomous commits should be authored by a clearly-named bot identity, not Leon, so an audit can distinguish.
- **Dry-run output is not committed.** Phase 6 requires a dry-run report before proof publication but does not require it be stored under `docs/verification/` with a deterministic name tied to the Candidate id.

## 5. Site / roadmap update concerns

- **Marker strings are easily satisfied cosmetically** (see Missing tests). Use a structured marker per page section.
- **`/projects/smactorio/` will show empty fields** for "GitHub issue/branch/PR/commit" during the bootstrap slice. The plan does not say whether to render "—", hide the row, or stage a placeholder. An agent will pick one inconsistently across page rebuilds.
- **Spec/plan/review link list will grow unbounded.** No rule that only the latest reviewed spec is linked from the homepage with older versions in an archive list. Otherwise the cockpit grows to dozens of links.
- **Simple roadmap update risks confusing the human.** Adding the full development-loop and GitHub-backing sections on the *simple* roadmap may violate the "do not overwhelm Leon" goal. The plan should explicitly cap the simple roadmap at one screen and move the development loop detail behind a link/disclosure.
- **No regeneration determinism check.** Building pages twice in a row should produce byte-identical output (modulo timestamps in a single allowlisted field). Without this, the homepage will churn diffs on every run.

## 6. Concrete patch recommendations

Apply these edits to the plan before approving for execution:

1. **Phase 0 — replace task 3-4 with explicit reconciliation steps:**
   - Add a "Divergence audit" step: produce `docs/verification/2026-05-16-bootstrap-divergence.md` listing local-only, remote-only, and conflicting files, with file-by-file disposition.
   - Add an explicit path-mapping table: `leon-signal-hub/<x>` ↔ `signal-hub/<x>` enumerated, including any rename.
   - Forbid deletion of remote-only files in this slice. Adds-and-updates only.
   - Require `git check-ignore` and explicit staged-file diff review against the allowlist before commit; abort if any path outside the allowlist is staged.
2. **Phase 0 task 10 — pick one:** for this slice, require PR + human merge. No "or push directly." Add a separate decision artifact if direct-push will ever be allowed, and not as part of this plan.
3. **Phase 0 — name the secret scanner and pass criteria.** State the tool, ruleset, and that any finding fails the slice; record an `allowlist.yml` for known false positives signed by the operator.
4. **Phase 1 — forbid in-place spec/plan mutation after review.** "Patch the spec for Opus blockers" must produce a `-v2.md` next to the original, and the v1 file is immutable. Same for this plan.
5. **Phase 3 — define the dedup key precisely.** E.g. `sha256(lowercase(normalize_whitespace(title)) + "\n" + normalized_candidate_kind)`. Document the normalization function. Add a unit test with two title variants that must collide and two that must not.
6. **Phase 4 — bound and define the priority score.**
   - Each input axis is integer 0–5.
   - Effective score = `impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface`, clamped to `[-15, 25]`.
   - Restate `min_autonomous_score = 6` against that explicit range.
   - Add a per-axis floor: `impact >= 2 AND confidence >= 2 AND evidence_strength >= 1`.
   - Tie-break: lower `risk`, then older `created_at`, then lower issue number.
   - Name the golden fixture: `tests/fixtures/candidate_priority_golden.json`.
7. **Phase 4 — specify the lock.** "Single-writer lock implemented as `flock` on `state/smactorio.lock` with a 30-minute lease and a stale-lock recovery rule (lock files older than 60 minutes are considered abandoned and logged)." State that locks are never stored under a git-tracked path.
8. **Phase 5 — add timeouts and migration.** Runner subprocess timeout (e.g. 30 minutes default, configurable) with SIGTERM then SIGKILL. Add a named DB migration script for the FSM state rename and a backfill step for prior run records.
9. **Phase 6 — separate-actor review rule.** A review artifact must record `reviewer_actor_id` distinct from `implementer_actor_id`. If they are equal, the phase is marked `needs-review` and not advanced. State `max_requeue_count = 3` for dry-run findings, with deletion+recreation also counting against the limit (track by dedup key, not issue id).
10. **Phase 7 — render contract.**
    - Empty GitHub fields render as `—` with `data-empty="true"`.
    - Page markers are structured: `<meta name="smactor:section" content="priority-gate">`, etc. Tests look up by selector, not substring.
    - Homepage spec/plan link list shows only the latest reviewed version; older versions go to `/projects/smactorio/history/`.
11. **Rollback section — tighten.**
    - All reverts land via a branch + PR, regardless of repo privacy.
    - `main` must be a protected branch before any autonomous slice runs; if not, this slice halts.
    - On revert, the originating Candidate issue is reopened with `rollback` label and the proof page records the revert SHA.
    - Tags `smactor/*` are append-only; moving or deleting an existing tag is forbidden.
12. **Verification — assert idempotency.** After the two consecutive `--dry-run` invocations, diff the state traces and fail if the second run created any new GitHub issue, branch, or PR.
13. **Add rate caps to the plan's invariants section:** max 3 new issues per run, max 1 PR per Candidate per day, max 5 candidates selected per 24h, max 10 outstanding open `smactorio` issues before the agent must triage instead of create.
14. **Add commit-identity rule.** All autonomous commits authored by `smactorio-bot <bot@…>`, and the plan's done-definition checks `git log` for any human-author commits on the bootstrap branch as a regression signal.
15. **Done-definition addendum.** Add: "Branch protection on `main` confirmed," "no path outside the allowlist is staged," "no `smactorio` issue created without dedup marker," and "homepage renders identically on two consecutive builds."

With these patches the plan moves from approve-with-changes to safe to execute as the documentation/site/bootstrap slice, with runtime phases gated behind their own review.
