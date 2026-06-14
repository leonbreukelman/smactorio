# SmactorIO Improvement OS v1 Implementation Plan

> **For Hermes:** Implement this plan test-first. The local checkout is not a git repository, so use timestamped backups plus SHA256 proof instead of git restore/commits.

**Goal:** Make SmactorIO's first self-improvement loop visible, runnable, idempotent, scheduled through the existing Signal Hub systemd runner, and proof-backed on the LAN cockpit.

**Architecture:** Add source seed data under `data/smactorio/`, a stdlib-only runner at `scripts/smactorio_improvement_runner.py`, and a short rendered `Improvement OS` homepage section in `scripts/build_project_homepages.py`. The existing full operating loop invokes the runner as a subprocess after `SYNTHESIZE_DAILY_BRIEF` and before page rebuild/publish. Runtime evidence lives under `state/smactorio/`.

**Tech Stack:** Python 3 stdlib (`json`, `hashlib`, `fcntl`, `subprocess`, `unittest`), static HTML builders, existing systemd timer on `rtx3070`, existing Caddy public root.

---

## Preflight evidence

- Current UTC observed: 2026-05-15T04:17:59Z.
- Local/source path exists: `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`.
- Local/source checkout is not a git repository (`git rev-parse --show-toplevel` failed), so rollback must use tarball backups and exact SHA256 checks.
- Existing live timer: `leon-signal-hub-refresh.timer` is active/waiting on `rtx3070`, next trigger 2026-05-15 06:21:13 CDT.
- Existing live service: `leon-signal-hub-refresh.service` last completed with status 0 and JSON status `ok`.
- Existing scheduled command: `/usr/bin/python3 scripts/run_operating_loop.py` in `/home/leonb/projects/leon-signal-hub`.
- `scripts/run_operating_loop.py` already supports `--skip-scan`, `--dry-run`, and `--no-publish`.
- `scripts/scan_for_secrets.py` accepts positional paths.
- Local pre-change backup created: `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/state/runtime_backups/smactorio-improvement-os-local-prechange-20260515T041843Z.tar.gz`.

## Acceptance criteria

1. `data/smactorio/component_map.json` exists and validates against the v1 component schema.
2. `data/smactorio/improvement_candidates.json` exists and validates against the v1 candidate schema.
3. `scripts/smactorio_improvement_runner.py` implements `--dry-run`, `--no-homepage-update`, `--force`, and `--timeout-seconds`.
4. First completed run selects `improve-cockpit-improvement-visibility-001` and mutates `data/project_homepages/smactorio.json` outside `state/smactorio/`.
5. The run record contains before/after SHA256 for the mutated homepage data file, `before_sha256 != after_sha256`, and the diff includes a non-trivial structural field such as `improvement_os.selected_candidate.id`, not only a timestamp.
6. A second run without `--force` returns skipped and does not duplicate the journal entry.
7. Lock contention returns exit code 2 with `status: locked` and no source mutation.
8. `public/projects/smactorio/index.html` visibly includes: `Improvement OS`, `What is being improved`, `Selected candidate`, `Governance rule`, `Latest improvement run`, `Proof`, and `Next scheduled run`.
9. `scripts/run_operating_loop.py --dry-run` includes `RUN_SMACTORIO_IMPROVEMENT_LOOP` after `SYNTHESIZE_DAILY_BRIEF` and before page rebuild steps.
10. Runtime operating loop calls the SmactorIO runner as a subprocess and continues safely for ok/skipped/locked/degraded/blocked statuses.
11. Local and rtx3070 targeted tests, full unittest discovery, and secret scan pass.
12. rtx3070 source checkout has a timestamped rollback backup before sync.
13. Live Caddy URL `http://192.168.30.10:8765/projects/smactorio/` returns 200 and contains a fresh `last_run_at` from the manual proof run.
14. `leon-signal-hub-refresh.timer` remains active.

## Files to create

- `data/smactorio/component_map.json`
- `data/smactorio/improvement_candidates.json`
- `scripts/smactorio_improvement_runner.py`
- `tests/test_smactorio_improvement_runner.py`
- `docs/plans/2026-05-15-smactorio-improvement-os-implementation-plan.md`
- `docs/verification/2026-05-15-smactorio-improvement-os-plan-opus-review.md`

## Files to modify

- `scripts/build_project_homepages.py`
- `scripts/run_operating_loop.py`
- `tests/test_page_manifest_and_navigation.py`
- `tests/test_full_autonomy_fsm.py`
- `scripts/deploy_static_public_to_caddy.py` only if tests show accidental state-mutating runner invocation risk. Default decision: do not add the improvement runner to static deploy build steps.
- `data/project_homepages/smactorio.json` only through the runner during proof execution, not by hand editing except seed compatibility if tests require it.

## Closed choices

- Homepage rendering: add one short `Improvement OS` section directly to `/projects/smactorio/`; no detail page in v1.
- Scheduler integration: insert `RUN_SMACTORIO_IMPROVEMENT_LOOP` after `SYNTHESIZE_DAILY_BRIEF`, before `REBUILD_DASHBOARD` / page rebuild / publish.
- Invocation: subprocess, not import.
- Runner failures: ok/skipped/locked/degraded/blocked are recorded as step results and do not break the daily brief/dashboard unless source data is corrupt/unsafe or JSON contract is unusable.
- Source mutation allowlist: only `data/project_homepages/smactorio.json` and `data/smactorio/improvement_candidates.json` are source-mutatable by the v1 runner; runtime records stay under `state/smactorio/**`; generated HTML comes only from the existing builder.
- V1 seed candidate body: `improve-cockpit-improvement-visibility-001`, `execution.kind=update_project_homepage`, `execution.path=data/project_homepages/smactorio.json`, `preferred_strategy=internal_existing`, allowed source mutations are the allowlisted homepage keys (`current_step`, `current_work`, `journal`, `proof`, `template_notes`, `improvement_os`) plus candidate status metadata.
- V1 candidate command allowlist: the runner may execute only `[python3, scripts/build_project_homepages.py]`, `[python3, -m, unittest, tests.test_smactorio_improvement_runner]`, `[python3, -m, unittest, tests.test_page_manifest_and_navigation]`, and `[python3, scripts/scan_for_secrets.py, data/project_homepages/smactorio.json, data/smactorio, public/projects/smactorio/index.html]`. Any other candidate-declared command is blocked.
- `current_step` in `data/project_homepages/smactorio.json` is the SmactorIO cockpit step card, not the Signal Hub SQLite FSM state. The runner may set this project-homepage step to `IMPROVEMENT_RUN_COMPLETED` / `IMPROVEMENT_RUN_SKIPPED`; `run_operating_loop.py` separately records the real scheduled integration step as `RUN_SMACTORIO_IMPROVEMENT_LOOP` / `smactorio_improvement_loop` in step results.
- Static deploy helper: must build static pages but must not run the state-mutating improvement runner.
- Backups: tarball before local changes already exists; live tarball before rsync is required.

---

## Runner subprocess contract

The runner and operating loop must share this contract:

- Exit 0: `ok` or `completed`.
- Exit 2: `skipped` or `locked`.
- Exit 3: `degraded`.
- Exit 4: `blocked`.
- Any other non-zero, timeout, crash, or invalid JSON: treat as `degraded` in the operating loop, capture evidence, and continue where safe.
- Stdout: one single JSON object containing at least `status`, `run_id`, `selected_candidate_id`, `input_hash`, `mutations`, `checks`, and `errors`; for convenience it may also include `started_at`, `finished_at`, `latest_run_path`, `before_sha256`, and `after_sha256`.
- Stderr: free-form diagnostic text; `run_operating_loop.py` captures and stores a bounded tail in step evidence.
- JSON parse failure: record `degraded`, include stdout/stderr tails, continue to rebuild the existing pages where safe.

Atomic source-data writes must use a temporary file in the target directory plus `os.replace`, not truncate-and-write. Missing or corrupt `state/smactorio/latest_run.json` is treated as no prior run. If source data is manually reverted while the input hash is unchanged, `--force` is the explicit recovery path. The SmactorIO lock guards source-data mutation only; static page rendering can still be run by the existing page builders.

## Test-first task sequence

### Task 1: Write runner schema and seed-data tests

**Objective:** Establish validation contracts before creating production code.

**Files:**
- Create: `tests/test_smactorio_improvement_runner.py`
- Later create: `scripts/smactorio_improvement_runner.py`
- Later create: `data/smactorio/component_map.json`
- Later create: `data/smactorio/improvement_candidates.json`

**RED tests:**
- Component map accepts valid seed data.
- Component map rejects unknown top-level keys, duplicate IDs, bad IDs, credential-looking IDs/labels, path traversal shapes, and symlink/path escape attempts.
- Candidate schema accepts valid seed data.
- Candidate schema rejects bad statuses, unknown execution kinds, unsafe paths, and malformed scores.

**Run expected failure:**

```bash
python3 -m unittest tests.test_smactorio_improvement_runner
```

Expected: fail because `smactorio_improvement_runner` does not exist yet.

**GREEN implementation:**
- Add importable validation helpers in `scripts/smactorio_improvement_runner.py`:
  - `load_json(path)`
  - `validate_component_map(payload)`
  - `validate_candidates(payload, component_ids=None)`
  - `looks_credential_like(value)`
  - `safe_source_path(path)`
- Add seed JSON files with all initial components and first candidate from the spec.

**Verification:** same unittest command passes for schema tests.

### Task 2: Add deterministic scoring and idempotency tests

**Objective:** Prove deterministic selection and hash behavior before mutation code.

**Files:**
- Modify: `tests/test_smactorio_improvement_runner.py`
- Modify: `scripts/smactorio_improvement_runner.py`

**RED tests:**
- `compute_priority(scores)` follows `impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface`.
- Candidate with priority below 1 is auto-parked.
- Ties resolve by higher reversibility, then lower regression surface, then lexical candidate ID.
- `compute_input_hash(...)` is stable across repeated calls and JSON key reordering.
- Candidate `status`, timestamps, scores, journal entries, runtime run records, generated HTML, and proof/check fields do not affect the hash.

**GREEN implementation:**
- Add canonical projection exactly matching the spec.
- Exclude mutable fields.
- Use `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)` and SHA256.

**Verification:** targeted unittest passes.

### Task 3: Add dry-run, mutation, run-record, and idempotency tests

**Objective:** Prove the first run performs a real source-data mutation and a second run skips safely.

**Files:**
- Modify: `tests/test_smactorio_improvement_runner.py`
- Modify: `scripts/smactorio_improvement_runner.py`

**RED tests:**
- `--dry-run` returns a JSON plan and does not mutate files.
- First run updates `data/project_homepages/smactorio.json` with `improvement_os`, current step `IMPROVEMENT_RUN_COMPLETED`, and exactly one journal entry titled `Improvement OS loop completed`.
- First run records before/after SHA256 for `data/project_homepages/smactorio.json`, proves the hashes differ, and proves the semantic diff includes `improvement_os.selected_candidate.id` or equivalent non-trivial structure.
- Latest pointer is written at `state/smactorio/latest_run.json`.
- Second run without `--force` returns `skipped`, does not mutate source, and does not append another visible journal entry.
- `--force` after a recent successful run may create a run record but still does not duplicate the same journal entry and still respects path/command allowlists.
- `--no-homepage-update` does not mutate homepage data.

**GREEN implementation:**
- Add `run_improvement(...)` with root-injection support for tests.
- Add atomic JSON writes.
- Add latest-run pointer and retention of latest 30 run records.
- Use idempotency hash compared with latest successful/skipped pointer.
- Use a stable journal de-dup key/title before appending.

**Verification:** targeted unittest passes.

### Task 4: Add lock, governance, candidate-test, and failure-handling tests

**Objective:** Prove v1 fails closed around concurrency, unsafe paths, and failed verification.

**Files:**
- Modify: `tests/test_smactorio_improvement_runner.py`
- Modify: `scripts/smactorio_improvement_runner.py`

**RED tests:**
- Concurrent runner attempts produce one active run and one locked/skipped result.
- Internal-existing candidate writing outside the allowlist returns blocked and does not mutate source.
- Candidate referencing a path outside the allowlist, including `../../etc/passwd`-style traversal, returns blocked.
- Page rebuild failure records degraded or rolls back/preserves prior file backup.
- Candidate tests gate completed status.
- Runner does not make outbound network calls; monkeypatching `socket.socket` to raise must not affect the runner.
- Secret scanner is invoked/scoped for `data/project_homepages/smactorio.json`, `data/smactorio`, and `public/projects/smactorio/index.html`.

**GREEN implementation:**
- Add lock file `state/smactorio/.runner.lock` using `fcntl.flock`.
- Add strategy/path allowlist enforcement.
- Run `scripts/build_project_homepages.py` after mutation unless dry-run/no-homepage-update.
- Preserve a pre-mutation backup copy when page rebuild/checks fail; record backup path in the run record.
- Run candidate commands only from a fixed allowlist; use subprocess with timeout.
- On build/test/scan failure, keep source mutation evidence, mark degraded/blocked as appropriate, and preserve backup copy path in run record.

**Verification:** targeted unittest passes.

### Task 5: Render Improvement OS on the cockpit

**Objective:** Make the runner's visible summary readable on the project homepage.

**Files:**
- Modify: `scripts/build_project_homepages.py`
- Modify: `tests/test_page_manifest_and_navigation.py`

**RED tests:**
- Generated SmactorIO page contains the required Improvement OS markers.
- Existing shell/nav/link tests still pass.
- HTML escapes all `improvement_os` values and still rejects active-content markers.

**GREEN implementation:**
- Add `render_improvement_os(record)` helper.
- Insert the section after the current step card and before current work.
- Add required markers to `REQUIRED_MARKERS["smactorio"]`.
- Keep long proof as short bullets/tags, not a large dump.

**Verification:**

```bash
python3 -m unittest tests.test_page_manifest_and_navigation
python3 scripts/build_project_homepages.py
```

### Task 6: Integrate runner into the full operating loop

**Objective:** Wire the existing systemd-backed daily runner without adding a Hermes cron job.

**Files:**
- Modify: `scripts/run_operating_loop.py`
- Modify: `tests/test_full_autonomy_fsm.py`

**RED tests:**
- Dry-run step list contains `RUN_SMACTORIO_IMPROVEMENT_LOOP` immediately after `SYNTHESIZE_DAILY_BRIEF` and before rebuild/publish steps.
- Mocked subprocess status `ok` records a normal step and continues.
- Mocked `skipped`/`locked` exit 2 records skipped/degraded evidence and continues.
- Mocked `degraded` exit 3 records degraded and continues.
- Mocked `blocked` exit 4 records blocked/degraded evidence and continues rather than breaking the daily brief.
- Mocked timeout, exit 1, exit 137, and negative signal-style return code record degraded evidence and continue.
- Invalid JSON/non-contract output records degraded evidence and continues where safe.
- Mocked live execution order proves `smactorio_improvement_loop` runs after `synthesize_daily_brief` and before the first rebuild step, not only in the dry-run list.

**GREEN implementation:**
- Add `run_smactorio_improvement_loop(ctx, timeout=120)`.
- Call it after successful `synthesize_daily_brief` and before `if no_publish:` branch/page rebuild.
- Record `run_step_results` entry named `smactorio_improvement_loop` with JSON evidence.
- Add `RUN_SMACTORIO_IMPROVEMENT_LOOP` to the dry-run list.
- Keep exit mapping aligned with the spec.

**Verification:**

```bash
python3 -m unittest tests.test_full_autonomy_fsm
python3 scripts/run_operating_loop.py --dry-run
```

### Task 7: Verify static deploy does not mutate state

**Objective:** Ensure manual/static publish remains a page-builder pipeline, not an autonomous improvement run.

**Files:**
- Inspect/modify only if needed: `scripts/deploy_static_public_to_caddy.py`
- Inspect/modify only if needed: `tests/test_deploy_static_public_to_caddy.py`

**Default expected result:** Existing deploy build steps include `build_project_homepages.py` but not `smactorio_improvement_runner.py`; no code change needed unless tests reveal a gap. Add an explicit source-text assertion that `scripts/deploy_static_public_to_caddy.py` does not contain `smactorio_improvement_runner`.

**Verification:**

```bash
python3 -m unittest tests.test_deploy_static_public_to_caddy
```

### Task 8: Local proof run and full verification

**Objective:** Generate the first real improvement, prove idempotency, and scan for secrets locally.

**Commands:**

```bash
cd /home/leonb/projects/ai-tech-signal-brief/leon-signal-hub
python3 -m unittest tests.test_smactorio_improvement_runner
python3 scripts/smactorio_improvement_runner.py --dry-run
python3 scripts/smactorio_improvement_runner.py --force
python3 scripts/smactorio_improvement_runner.py
python3 scripts/build_project_homepages.py
python3 -m unittest tests.test_page_manifest_and_navigation
python3 -m unittest tests.test_full_autonomy_fsm
python3 -m unittest tests.test_deploy_static_public_to_caddy
python3 -m unittest discover -s tests -q
python3 scripts/scan_for_secrets.py data docs public scripts tests
```

**Proof to capture:**
- Runner JSON for force run and second non-force run.
- SHA256 of `data/project_homepages/smactorio.json` and `public/projects/smactorio/index.html`.
- Count of `Improvement OS loop completed` journal entries equals 1.
- `public/projects/smactorio/index.html` contains all required markers.

### Task 9: Live rtx3070 backup, sync, and verification

**Objective:** Move the exact intended files to the live source checkout and prove the scheduled runner integration live.

**Backup command:**

```bash
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && mkdir -p state/runtime_backups && tar -czf state/runtime_backups/smactorio-improvement-os-$(date -u +%Y%m%dT%H%M%SZ).tar.gz data/project_homepages/smactorio.json data/smactorio scripts/run_operating_loop.py scripts/smactorio_improvement_runner.py scripts/build_project_homepages.py tests/test_smactorio_improvement_runner.py tests/test_page_manifest_and_navigation.py tests/test_full_autonomy_fsm.py tests/test_deploy_static_public_to_caddy.py public/projects/smactorio docs/systemd 2>/dev/null || true'
```

**Sync exact intended files only:**

```bash
cd /home/leonb/projects/ai-tech-signal-brief/leon-signal-hub
rsync -avR \
  data/smactorio/component_map.json \
  data/smactorio/improvement_candidates.json \
  data/project_homepages/smactorio.json \
  scripts/smactorio_improvement_runner.py \
  scripts/build_project_homepages.py \
  scripts/run_operating_loop.py \
  tests/test_smactorio_improvement_runner.py \
  tests/test_page_manifest_and_navigation.py \
  tests/test_full_autonomy_fsm.py \
  tests/test_deploy_static_public_to_caddy.py \
  docs/plans/2026-05-15-smactorio-improvement-os-implementation-plan.md \
  docs/verification/2026-05-15-smactorio-improvement-os-plan-opus-review.md \
  rtx3070:/home/leonb/projects/leon-signal-hub/
```

**Hash verification:**

Use the same explicit file list for local and remote manifests:

```bash
files='data/smactorio/component_map.json data/smactorio/improvement_candidates.json data/project_homepages/smactorio.json scripts/smactorio_improvement_runner.py scripts/build_project_homepages.py scripts/run_operating_loop.py tests/test_smactorio_improvement_runner.py tests/test_page_manifest_and_navigation.py tests/test_full_autonomy_fsm.py tests/test_deploy_static_public_to_caddy.py docs/plans/2026-05-15-smactorio-improvement-os-implementation-plan.md docs/verification/2026-05-15-smactorio-improvement-os-plan-opus-review.md'
(cd /home/leonb/projects/ai-tech-signal-brief/leon-signal-hub && sha256sum $files | sort -k2) > /tmp/smactorio-local.sha256
ssh rtx3070 "cd /home/leonb/projects/leon-signal-hub && sha256sum $files | sort -k2" > /tmp/smactorio-remote.sha256
diff -u /tmp/smactorio-local.sha256 /tmp/smactorio-remote.sha256
```

**Remote verification:**

```bash
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 -m unittest tests.test_smactorio_improvement_runner'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 scripts/smactorio_improvement_runner.py --force'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 scripts/smactorio_improvement_runner.py'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 -m unittest tests.test_page_manifest_and_navigation'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 -m unittest tests.test_full_autonomy_fsm'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 scripts/run_operating_loop.py --skip-scan'
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && python3 scripts/scan_for_secrets.py data docs public scripts tests'
```

**Publish if needed:**

```bash
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && rsync -a --delete --chmod=D755,F644 public/ /srv/leon-signal-hub/public/'
```

### Task 10: HTTP/browser final verification

**Objective:** Prove the actual LAN cockpit is fresh, readable, and the active timer remains active.

**HTTP marker command:**

```bash
python3 - <<'PY'
from urllib.request import urlopen
url='http://192.168.30.10:8765/projects/smactorio/?verify=smactorio-os'
body=urlopen(url, timeout=10).read().decode('utf-8', 'replace')
for marker in ['SmactorIO','Improvement OS','What is being improved','Selected candidate','Governance rule','Latest improvement run','Proof','Next scheduled run']:
    if marker not in body:
        raise SystemExit(f'missing marker: {marker}')
if 'improve-cockpit-improvement-visibility-001' not in body:
    raise SystemExit('missing selected candidate id')
if 'sha256' not in body.lower():
    raise SystemExit('missing sha256 proof marker')
print('ok', len(body))
PY
```

**Browser checks:**
- Navigate to `http://192.168.30.10:8765/projects/smactorio/?verify=smactorio-os`.
- Confirm readable page, no obvious overlap, Improvement OS section visible.
- Check console for JavaScript errors; static page should have none.

**Timer check:**

```bash
ssh rtx3070 'systemctl status leon-signal-hub-refresh.timer --no-pager | sed -n "1,40p"'
```

## Rollback plan

1. Stop both `leon-signal-hub-refresh.timer` and `leon-signal-hub-refresh.service` during rollback so the timer cannot relaunch mid-restore.
2. On rtx3070, select the latest backup with `ls -t state/runtime_backups/smactorio-improvement-os-*.tar.gz | head -n1`.
3. Extract from `/home/leonb/projects/leon-signal-hub`.
4. Rebuild project homepages and dashboard.
5. Copy `public/` to `/srv/leon-signal-hub/public`.
6. Verify HTTP 200 and the pre-change markers `Project cockpit`, `Current step card`, `Living roadmap`, and absence of a completed Improvement OS proof block if rolling fully back.
7. Re-enable/start `leon-signal-hub-refresh.timer` and confirm it is active.

Minimum command shape:

```bash
ssh rtx3070 'sudo systemctl stop leon-signal-hub-refresh.timer leon-signal-hub-refresh.service && cd /home/leonb/projects/leon-signal-hub && backup=$(ls -t state/runtime_backups/smactorio-improvement-os-*.tar.gz | head -n1) && tar -xzf "$backup" && python3 scripts/build_project_homepages.py && python3 scripts/build_dashboard.py && rsync -a --delete public/ /srv/leon-signal-hub/public/ && sudo systemctl start leon-signal-hub-refresh.timer'
```

## Review status

Opus review completed and saved at `docs/verification/2026-05-15-smactorio-improvement-os-plan-opus-review.md`. Verdict: ACCEPT_WITH_CHANGES.

Review changes incorporated before implementation:

- Added shared runner stdout JSON and exit-code contract.
- Added explicit seed candidate body and candidate command/path allowlist.
- Clarified that `current_step` is the SmactorIO cockpit step card, while `run_operating_loop.py` records the real scheduled integration step separately.
- Added atomic-write, missing/corrupt latest-pointer, timeout, crash, invalid-JSON, no-network, symlink/path traversal, `--force`, and non-trivial-diff test requirements.
- Tightened static deploy guard so deploy does not invoke the state-mutating runner.
- Tightened live backup scope, hash verification commands, HTTP marker proof, and rollback timer handling.
