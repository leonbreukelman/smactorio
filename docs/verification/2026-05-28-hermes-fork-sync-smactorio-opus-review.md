# Review: Hermes fork-sync conflict detection via SmactorIO

## 1. Verdict: **BLOCK** (implementable in spirit, but two safety-relevant contradictions must be resolved before coding)

The architecture is sound and the safety intent is clear, but as written the plan contradicts its own stated guarantees in two places (isolated checkout; verified-merge semantics) and leans on a race-prone idempotency mechanism. These are design-level, not cosmetic. Fix the items in §3, then this is a PASS.

## 2. Top risks / design bugs

**A. "Isolated checkout" is violated by the systemd lane.** Desired behavior #4 and your stated safety requirement say SmactorIO resolves conflicts *in an isolated checkout*. But Step 3 runs the foreman with `--repo-root /home/leonb/hermes` — the **live** checkout that the hourly checker (Step 1) also fetches/merges/aborts in. Two writers on one working tree on independent timers is a race: an aborted merge in the checker can land mid-foreman-run, and vice versa. This is the single most important issue.

**B. Clean-merge auto-push bypasses all verification.** The whole premise is that `hermes update` is *correctly conservative*. Yet Step 1 has the checker auto-push fast-forwards **and clean merges** to the fork with no test/PR gate. A textually clean merge is not a semantically safe merge — this is exactly the "silently merge upstream" behavior the conservative tool refuses, just relocated. Meanwhile the *conflict* path gets full PR + checks + verified merge. The safe paths are less verified than the unsafe path. Either gate clean merges through the same verified-PR flow, or constrain the checker's auto-push to **fast-forward only** and route any real merge to the issue/SmactorIO lane.

**C. Redaction by scrubbing raw `git` output will leak local paths.** Safety boundary says "do not expose local paths." `git merge`/`status` output contains `/home/leonb/...` and potentially token-bearing remote URLs. Scrub-based redaction is a denylist and will eventually miss something. Build the issue body from an **allowlist of structured fields only** (SHAs, repo-relative conflicted paths, file counts, timestamp) — never embed raw command stdout/stderr.

**D. Idempotency by exact-title search is race-prone.** GitHub search is eventually consistent; two timer firings (or a slow index) can both see "no open issue" and create duplicates. Title edits also break matching. Use a stable machine-readable marker (hidden HTML comment with a key + the prior fork/upstream SHA pair) and match on label + marker, not human title. Parse the prior SHA pair from that marker rather than re-deriving it.

**E. Hermes lane switches from allowlist to denylist path-scoping.** "Allow all changed repo paths except runtime/secret/data/cache/build" is a denylist for an autonomous agent operating in an *agent-framework* repo. Denylists fail open. High-leverage files (`.github/workflows/*`, `setup.py`/`pyproject.toml` build hooks, `conftest.py`, anything executed at install/test time) are easy to omit. Strongly prefer scoping the resolution to **the files named in the conflict issue** (plus an allowlist of source dirs), so SmactorIO can't edit arbitrary repo files under the guise of conflict resolution.

**F. System service writing into a user home dir.** A *system* unit (Step 3 foreman) and a *user* unit (Step 3 checker) both write `/home/leonb/hermes`. If the foreman runs as root, commits/pushes there will leave root-owned files and break user-level `hermes update`. The plan doesn't state `User=leonb`. Confirm UID/ownership and `ReadWritePaths` scoping (only `/home/leonb/hermes` + state/share/cache, never broad `$HOME`).

**G. Backward-compat rename left ambiguous.** "`verification_artifact_prefixes` replaces or aliases `foreman_artifact_prefixes`" — "or" is not a decision. If anything references the old field, you must alias (or update all call sites). Pick one before coding.

## 3. Concrete changes before implementation

1. **Decouple the two writers from the live tree.** Have the checker operate in a throwaway worktree (`git worktree add` / temp clone) and have the foreman use `--repo-root <isolated checkout>`. Reserve `/home/leonb/hermes` as a read source. Add a single cross-process lock (flock) shared by checker + foreman so they never run concurrently against the same remote/tree.
2. **Restrict checker auto-push to fast-forward only.** No automatic merge-commit pushes. Any non-FF case → create/update the conflict issue and let the verified SmactorIO lane handle it. Assert the push refspec contains no `+`/`--force`.
3. **Make the issue body allowlist-rendered** from structured fields; add an explicit redaction/no-abs-path guard as a final pass over the rendered body (defense in depth), not as the primary mechanism.
4. **Replace title-based idempotency** with label + hidden marker key, and parse prior SHA pair from the marker. Handle the create-collision (catch duplicate, reconcile to oldest open issue).
5. **Keep the Hermes lane allowlist-based**, scoped to conflict-issue files / known source dirs. Explicitly deny workflow files, packaging/build hooks, and test-collection files (`conftest.py`) regardless of lane.
6. **Pin `User=leonb`** for the foreman system unit (or run it as a user unit), and verify `ReadWritePaths` excludes broad `$HOME`.
7. **Resolve the field-rename** to an explicit alias with a deprecation, and keep `policy_for_repo` failing **closed** (unknown repo → Signal Hub path scope).
8. **Path-boundary check for binaries/roots:** realpath both sides and compare by path component (you already use trailing slashes — good; also reject `..` and symlink escapes after resolution).

## 4. Missing tests

- **Force-push guard:** assert every push invocation (checker + foreman PR merge) has no `--force` / `+refspec`.
- **Conflict path leaves remote untouched:** assert *no* push call occurs on the conflict branch, and the checkout is clean + not mid-merge afterward.
- **Negative redaction test:** feed sample git output containing `/home/leonb/...` and a fake token; assert neither appears in the rendered issue body.
- **Idempotency race:** search-returns-empty-but-issue-exists → no duplicate; SHA-pair marker parse/round-trip.
- **Concurrency/lock:** checker and foreman cannot both hold the tree/remote; second waiter blocks or no-ops.
- **Verified-merge gating:** foreman refuses to merge when checks are missing/failing; **repeated-failure breaker** trips to "blocked" (your desired behavior #5 has no test).
- **Hermes denylist/allowlist enforcement:** assert rejection of `.github/workflows/*`, `pyproject.toml`/`setup.py`, `conftest.py`, and runtime/cache/build paths even in the Hermes lane.
- **`policy_for_repo` fail-closed:** unknown repo returns Signal Hub policy; Hermes-substring repos don't accidentally match.
- **Ownership/user:** unit declares expected `User=` (assert in the systemd-unit test alongside `ConditionHost`/attestation/paths).
- **Fast-forward-only push test** (after change #2): non-FF case produces an issue, not a push.

---

Net: the conflict-detection-to-issue-to-SmactorIO pipeline is a good design. The blockers are (A) the shared live checkout and (B) clean-merge auto-push bypassing verification — both reintroduce the exact "silent mutation of the fork" risk the system exists to prevent. Resolve those plus the idempotency/redaction hardening and it's ready to implement.

*Note: this is a static review of the plan text per your "review only, no tools" instruction — I did not read the existing `smactorio_policy.py` / foreman sources to confirm current field names or the existing service's `User=`/sandboxing. Validate items B-compat (G) and F against the actual files before coding.*
