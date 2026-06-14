# Read-Only Adversarial Plan Review — SmactorIO Improvement OS v1

## Verdict: ACCEPT_WITH_CHANGES

The plan is structurally sound, test-first, and respects the spec's hard rails (subprocess integration after `SYNTHESIZE_DAILY_BRIEF`, no Hermes cron job, stdlib-only, no live LLM). Several contract gaps and test gaps must be closed before Hermes begins coding, but no fundamental architectural redesign is required.

---

## Blockers before implementation

1. **Subprocess output contract missing.** The plan tells the operating loop to parse runner output but never specifies the channel (stdout vs. file) or the JSON shape. Hermes can implement two incompatible halves. Spec: "runner emits a single-line JSON envelope on stdout containing `status`, `run_id`, `selected_candidate`, `input_hash`, `before_sha256`, `after_sha256`, `latest_run_path`."
2. **Exit-code mapping not codified.** Plan implies `0=ok`, `2=skipped|locked`, `3=degraded`, `4=blocked`, but the runner code and the loop's `run_smactorio_improvement_loop` must share one table. Add an exit-code table to the plan body and to a docstring constant in the runner.
3. **`current_step: IMPROVEMENT_RUN_COMPLETED` semantics are undefined.** If `current_step` on the homepage data is supposed to reflect the actual FSM step of `run_operating_loop.py`, the runner overwriting it is a Potemkin label that the next loop run will silently undo. Clarify: either (a) define this as a separate field (`improvement_os.last_step`) and leave `current_step` to the FSM, or (b) make `IMPROVEMENT_RUN_COMPLETED` a real FSM enum value emitted by the loop after the subprocess returns ok.
4. **Candidate execution allowlist not enumerated.** Task 4 GREEN says "Run candidate commands only from a fixed allowlist" but never lists what is in that allowlist for the seed candidate. Without explicit enumeration, Hermes could quietly broaden execution scope. List the allowed commands (e.g., `["scripts/build_project_homepages.py"]`) in the plan.
5. **Seed candidate execution body absent.** The plan creates `improvement_candidates.json` but does not describe what `improve-cockpit-improvement-visibility-001` actually executes. Reviewer cannot evaluate safety/idempotency of an unspecified candidate. Add the candidate's `execution_kind`, target paths, and commands to the plan's closed-choices block.

---

## Missing tests

- Path-traversal / symlink test for `safe_source_path` (e.g., `../../etc/passwd`, `data/project_homepages/smactorio.json/../../`).
- Negative test: candidate referencing a path outside the allowlist returns `blocked` and does not mutate.
- Network-non-call test: assert the runner never imports `urllib`, `socket`, `requests`, `http` — or monkeypatch `socket.socket` to raise.
- Initial-state test: behavior when `data/project_homepages/smactorio.json` is missing or empty.
- Subprocess-timeout test in `tests.test_full_autonomy_fsm`: simulate `subprocess.TimeoutExpired` and assert loop records `degraded` and continues.
- Subprocess-crash test: simulate exit codes 1, 137, and -SIGTERM; verify loop maps to `degraded`/`blocked` rather than raising.
- `--force` after a recent successful run: still respects allowlist, still single journal entry, but produces a new run record.
- stderr capture test: ensure runner stderr is preserved in run evidence (otherwise diagnosing live failures is impossible).
- Static-deploy grep test in Task 7: explicit assertion that the deploy script's source does not contain the string `smactorio_improvement_runner` (the current "no code change unless tests reveal a gap" is too permissive).

---

## Idempotency / concurrency flaws

- **Atomic-write strategy unspecified.** Task 3 GREEN says "atomic JSON writes" but does not commit to `tempfile.NamedTemporaryFile` + `os.replace` on the same filesystem. Without this, a power loss between truncate and write corrupts source data and breaks the idempotency hash forever. Specify it.
- **Hash compares against "latest successful/skipped pointer."** If `latest_run.json` is corrupted or missing, the runner cannot tell whether to skip. Define fallback: missing/corrupt latest pointer = treat as no prior run = proceed (subject to lock).
- **Drift recovery only via `--force`.** If `data/project_homepages/smactorio.json` is manually reverted, the input-hash match means the runner skips. This is consistent with the spec but should be called out so operators know `--force` is the recovery path (otherwise the cockpit silently shows pre-revert state until next candidate appears).
- **Page-rebuild race.** The runner mutates `data/project_homepages/smactorio.json` then invokes `build_project_homepages.py`. The operating loop *also* rebuilds homepages later. If a human runs the static deploy concurrently, there is no cross-process coordination on the public output. Low risk in practice, but document that the lock guards source-data mutation only, not page rendering.

---

## Scheduler integration flaws

- **No explicit subprocess timeout enforcement test.** Plan sets `timeout=120` in `run_smactorio_improvement_loop`, but no test asserts that the loop kills a hung runner and continues. Add it (see missing tests).
- **Unknown exit codes not mapped.** Plan handles 0/2/3/4 explicitly; 1 and other codes are not in the test matrix. Add a catchall: any unmapped non-zero exit → `degraded`, evidence captured, loop continues.
- **JSON-parse failure already partially covered** ("Invalid JSON/non-contract output records degraded/blocked evidence") but the line between `degraded` and `blocked` for parse failure isn't decided. Pick one (recommend `degraded`).
- **No assertion that the runner step appears between `SYNTHESIZE_DAILY_BRIEF` and `REBUILD_DASHBOARD` in the *actual* (non-dry-run) execution path.** The dry-run list is tested; the live ordering is not. Add a unit test that asserts the call order in `run_operating_loop.main` via mocks, not just the printed step list.

---

## Rollback / deployment flaws

- **Rollback only stops the service, not the timer.** `systemctl stop leon-signal-hub-refresh.service` does not prevent the timer from re-launching it mid-rollback. Patch the rollback section to:
  `ssh rtx3070 'sudo systemctl stop leon-signal-hub-refresh.timer leon-signal-hub-refresh.service'`
  and re-enable the timer at the end.
- **`<backup>` placeholder is operator-unfriendly.** Replace with an explicit selector:
  `ls -t state/runtime_backups/smactorio-improvement-os-*.tar.gz | head -n1`
- **Backup scope is broad.** The pre-sync backup tars the entire `tests/` directory and `scripts/run_operating_loop.py`. A rollback would revert unrelated concurrent edits to those files. Tightening to a named file list eliminates this risk; if broad is intentional, acknowledge it in the plan.
- **Hash-verification step under-specified.** "Generate local and remote SHA256 manifests… compare byte-for-byte after replacing path prefixes" — no command shown. Add the exact `find … -exec sha256sum` (or `sha256sum` over an explicit file list) for both sides; otherwise Hermes will improvise and may compare different file sets.
- **Implementation-plan file itself not in Files-to-create.** Task 9's rsync ships `docs/plans/2026-05-15-smactorio-improvement-os-implementation-plan.md`, but the plan never declares its own creation. Either add it to "Files to create" or note it as pre-existing.
- **No post-rollback verification gate.** The rollback section ends with "Verify HTTP 200 and expected pre-change markers" but does not list which markers prove the pre-change state. Capture a pre-change marker set in the preflight evidence (e.g., presence of certain phrases that existed before the change) and reference them in rollback verification.

---

## Fake-proof / Potemkin-loop risks

- **`current_step: IMPROVEMENT_RUN_COMPLETED`** — see Blocker #3. If the FSM does not actually transition here, the homepage marker is a synthetic label. Either codify the transition or rename the field.
- **The "improvement" *is* making improvements visible.** `improve-cockpit-improvement-visibility-001` adds the visibility block that the same loop reads to "prove" it ran. This is borderline self-justifying. Mitigate by adding to acceptance criteria: the run record's `after_sha256` must differ from `before_sha256`, AND the diff must include at least one structurally non-trivial field beyond timestamp/hash (e.g., `selected_candidate.id`). Without this, a timestamp-only change satisfies all current assertions.
- **Proof section content is short bullets/tags** (Task 5 GREEN). Confirm acceptance criterion includes the rendered SHA256 prefix and `run_id` *value*, not just the labels `Proof`. Otherwise a static heading satisfies the marker check.
- **HTTP marker assertion uses Python `assert`**, which is disabled if anyone runs with `-O`. Convert to explicit `if ... raise SystemExit(1)` or check via `unittest.TestCase`.
- **Browser check is fully manual** ("Confirm readable page, no obvious overlap"). Either drop the manual claim from acceptance evidence and rely solely on the HTTP marker check, or use Playwright to assert visibility programmatically. Otherwise the "browser verification" line in the spec is satisfied by a single human glance.

---

## Required plan patches

1. **Add exit-code + JSON-envelope contract block** to plan body (before Task 1):
   ```
   Exit codes: 0=ok, 2=skipped|locked, 3=degraded, 4=blocked, else=degraded.
   Stdout: single-line JSON {status, run_id, selected_candidate, input_hash, before_sha256, after_sha256, latest_run_path, started_at, finished_at}.
   Stderr: free-form; loop captures and stores in evidence.
   ```
2. **Enumerate the v1 candidate execution allowlist** (commands and paths) in "Closed choices".
3. **Add the seed candidate's body** (`execution_kind`, target paths, commands, governance rule) to "Closed choices" so reviewers can audit safety.
4. **Clarify `current_step`** — either move to `improvement_os.last_step` (recommended) or extend the loop's FSM enum to include `IMPROVEMENT_RUN_COMPLETED`.
5. **Specify atomic-write mechanism** in Task 3 GREEN: `tempfile.NamedTemporaryFile(dir=target_dir)` + `os.replace`.
6. **Add the missing tests** listed above to Tasks 1–6 RED sections.
7. **Rollback patches:** stop timer + service together; use `ls -t … | head -n1` to select backup; re-enable timer at the end; capture pre-change marker set in preflight.
8. **Hash-verification patch:** add explicit `sha256sum` commands and file list in Task 9.
9. **HTTP marker check patch:** replace `assert` with explicit raise, and confirm rendered `run_id` + SHA256 prefix appear in the live page (not just the label `Proof`).
10. **Add a `before_sha256 != after_sha256` and "non-trivial diff" assertion** to acceptance criteria to prevent timestamp-only Potemkin runs.
11. **Add a "no outbound network" test** (mock `socket.socket` to raise).
12. **Add the plan file to "Files to create"** or annotate it as pre-existing.

Address blockers 1–5 and required patches 1–4, 7, 9, 10 at minimum; remaining items are strongly recommended.
