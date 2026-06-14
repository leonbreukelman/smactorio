# Fresh Session Prompt — Implement SmactorIO Improvement OS v1

Use this prompt in a new Hermes session.

---

You are Hermes Agent working for Leon. Your task is to implement SmactorIO Improvement OS v1 in the Signal Hub project and show Leon a working SmactorIO cockpit by the end of the session.

Load and follow these skills before acting:

- `signal-hub-operating-loop-verification`
- `disciplined-project-delivery`
- `writing-plans`
- `test-driven-development`
- `systematic-debugging`
- `claude-code`
- `requesting-code-review`
- `subagent-driven-development` if the final plan has separable implementation slices

## User outcome

Leon should be able to open:

`http://192.168.30.10:8765/projects/smactorio/`

and see a working SmactorIO Improvement OS section showing:

- what is being improved
- the selected improvement candidate
- the internal-first governance rule
- latest improvement run result
- proof/checks
- last run time
- next scheduled run/timer context

The system must also be wired into the existing scheduled Signal Hub runner so that the daily rtx3070 timer triggers the SmactorIO improvement loop. Do not create a duplicate Hermes cron job for v1.

## Project paths

Local/source checkout:

`/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`

Live rtx3070 source checkout:

`/home/leonb/projects/leon-signal-hub`

Live Caddy public root:

`/srv/leon-signal-hub/public`

Live URL:

`http://192.168.30.10:8765/projects/smactorio/`

Existing live scheduler:

- timer: `leon-signal-hub-refresh.timer`
- service: `leon-signal-hub-refresh.service`
- command: `/usr/bin/python3 scripts/run_operating_loop.py`
- host: `rtx3070`

## Required spec and review inputs

Read these first:

- `docs/specs/2026-05-15-smactorio-improvement-os-spec.md`
- `docs/verification/2026-05-15-smactorio-improvement-os-spec-opus-review.md`
- `data/project_homepages/smactorio.json`
- `scripts/build_project_homepages.py`
- `scripts/run_operating_loop.py`
- `docs/systemd/leon-signal-hub-refresh.service`
- `docs/systemd/leon-signal-hub-refresh.timer`

If any file is missing locally, search for it before asking Leon. Ask only for true blockers.

## Important constraints

1. Keep the visible product simple.
2. V1 must not call live LLMs.
3. V1 must not introduce new outbound network calls beyond existing `run_operating_loop.py` behavior.
4. V1 must not mutate public/social/external accounts.
5. V1 must not create a new Hermes cron job.
6. Use the existing rtx3070 systemd timer integration.
7. The first run must make one real source-data mutation outside `state/smactorio/`, visible on the cockpit, with before/after SHA256.
8. A second run must prove idempotency: no duplicate journal entry.
9. Use stdlib JSON/dataclasses; do not add dependencies unless unavoidable.
10. Avoid strings that resemble credential prefixes. Do not create identifiers that look like API keys.
11. The repo may not be a git repo. Use backups and SHA256 hashes rather than assuming git restore/commit exists.
12. Do not stop after writing a plan. Plan, review, patch, implement, verify, deploy to LAN, and hand off proof.

## Required workflow

### Phase 0 — Preflight and state discovery

1. Confirm current time with `date -u`.
2. Confirm local path exists.
3. Inspect whether the local checkout is a git repo. If not, say so in the plan and use backups/hashes.
4. Inspect local changed/source files relevant to SmactorIO.
5. Verify live rtx3070 timer state with:
   - `ssh rtx3070 'systemctl status leon-signal-hub-refresh.timer --no-pager | sed -n "1,40p"'`
   - `ssh rtx3070 'systemctl status leon-signal-hub-refresh.service --no-pager | sed -n "1,60p"'`
6. Confirm `scripts/run_operating_loop.py --skip-scan` exists by reading/parser inspection, not by guessing.
7. Confirm `scripts/scan_for_secrets.py` accepts positional paths.

### Phase 1 — Write implementation plan

Write a detailed plan under:

`docs/plans/2026-05-15-smactorio-improvement-os-implementation-plan.md`

The plan must include:

- goal
- acceptance criteria
- exact files to create/modify
- test-first sequence
- runner schema and idempotency design
- candidate seed data
- homepage rendering changes
- operating-loop integration changes
- live rtx3070 backup/sync/deploy steps
- verification commands
- rollback plan

The plan must close all open choices from the spec. Defaults:

- Add a short Improvement OS section to the SmactorIO homepage.
- Insert `RUN_SMACTORIO_IMPROVEMENT_LOOP` after `SYNTHESIZE_DAILY_BRIEF` and before page rebuild/publish.
- Invoke the runner as a subprocess.
- Continue the daily brief/dashboard on runner skip/lock/degraded; block only on corrupt/unsafe data that makes the cockpit untrustworthy.
- Use runtime state under `state/smactorio/` plus visible summary in `data/project_homepages/smactorio.json`.
- Create a timestamped tarball backup on rtx3070 before live sync.

### Phase 2 — Opus adversarial plan review

Run read-only Claude Code Opus review of the plan before implementation.

Use Claude Code print mode, read-only/no tools if possible. Save the report under:

`docs/verification/2026-05-15-smactorio-improvement-os-plan-opus-review.md`

Review prompt should ask for:

- verdict: ACCEPT / ACCEPT_WITH_CHANGES / REJECT
- blockers before implementation
- missing tests
- idempotency/concurrency flaws
- scheduler integration flaws
- rollback/deployment flaws
- fake-proof/Potemkin-loop risks

If Opus returns ACCEPT_WITH_CHANGES or REJECT, patch the plan before coding and include a short “Review changes incorporated” section in the plan.

Do not skip this review unless Claude Code/Opus is genuinely unavailable. If unavailable, save the exact blocker and use a fallback independent review, clearly labeled.

### Phase 3 — Implement v1 with tests first

Expected files to create:

- `data/smactorio/component_map.json`
- `data/smactorio/improvement_candidates.json`
- `scripts/smactorio_improvement_runner.py`
- `tests/test_smactorio_improvement_runner.py`

Likely files to modify:

- `data/project_homepages/smactorio.json`
- `scripts/build_project_homepages.py`
- `scripts/run_operating_loop.py`
- `scripts/deploy_static_public_to_caddy.py` only if needed and only if state-mutating runner is not accidentally run during static deploy
- `tests/test_page_manifest_and_navigation.py`
- `tests/test_full_autonomy_fsm.py`
- `tests/test_deploy_static_public_to_caddy.py` if deploy behavior changes
- `docs/systemd/*` only if documented behavior changes

Implementation requirements:

1. Candidate schema and component schema validation.
2. Deterministic score computation.
3. Deterministic idempotency hash using canonical JSON projection from the spec.
4. Lock file at `state/smactorio/.runner.lock`.
5. Run records under `state/smactorio/improvement_runs/` and latest pointer at `state/smactorio/latest_run.json`.
6. First candidate: `improve-cockpit-improvement-visibility-001`.
7. First concrete action updates `data/project_homepages/smactorio.json` with visible `improvement_os` data and a single journal entry.
8. Homepage renders an `Improvement OS` section with required markers.
9. Operating loop calls runner as subprocess at pinned step and handles exit codes safely.
10. No duplicate journal entry on second run without `--force`.
11. Do not use new dependencies.

### Phase 4 — Local verification

Run at minimum:

```bash
python3 -m unittest tests.test_smactorio_improvement_runner
python3 scripts/smactorio_improvement_runner.py --dry-run
python3 scripts/smactorio_improvement_runner.py --force
python3 scripts/smactorio_improvement_runner.py
python3 -m unittest tests.test_page_manifest_and_navigation
python3 -m unittest tests.test_full_autonomy_fsm
python3 -m unittest discover -s tests -q
python3 scripts/scan_for_secrets.py data docs public scripts tests
```

After the first forced run, inspect `data/project_homepages/smactorio.json` and `public/projects/smactorio/index.html` for the Improvement OS markers.

After the second non-force run, prove no duplicate journal entry.

### Phase 5 — Live rtx3070 sync and verification

Before sync, create live backup:

```bash
ssh rtx3070 'cd /home/leonb/projects/leon-signal-hub && mkdir -p state/runtime_backups && tar -czf state/runtime_backups/smactorio-improvement-os-$(date -u +%Y%m%dT%H%M%SZ).tar.gz data/project_homepages/smactorio.json data/smactorio scripts/run_operating_loop.py scripts/build_project_homepages.py tests public/projects/smactorio docs/systemd 2>/dev/null || true'
```

Sync exact intended files only. Preserve relative paths; use `rsync -avR` from the local repo root.

Verify SHA256 hashes for changed source/data/test/doc files between local and rtx3070.

On rtx3070 run:

```bash
cd /home/leonb/projects/leon-signal-hub
python3 -m unittest tests.test_smactorio_improvement_runner
python3 scripts/smactorio_improvement_runner.py --force
python3 scripts/smactorio_improvement_runner.py
python3 -m unittest tests.test_page_manifest_and_navigation
python3 -m unittest tests.test_full_autonomy_fsm
python3 scripts/run_operating_loop.py --skip-scan
python3 scripts/scan_for_secrets.py data docs public scripts tests
```

If the full discovery scan is safe and needed, run the full `scripts/run_operating_loop.py`; otherwise `--skip-scan` is acceptable for integration proof.

Copy/sync public output to `/srv/leon-signal-hub/public` if the operating loop or deploy helper did not already do it.

Verify live URL:

```bash
python3 - <<'PY'
from urllib.request import urlopen
url='http://192.168.30.10:8765/projects/smactorio/?verify=smactorio-os'
body=urlopen(url, timeout=10).read().decode('utf-8', 'replace')
for marker in ['SmactorIO', 'Improvement OS', 'Selected candidate', 'Governance rule', 'Latest improvement run', 'Proof']:
    assert marker in body, marker
print('ok', len(body))
PY
```

Use browser tools for visual and console verification of the live URL.

Confirm timer remains active:

```bash
ssh rtx3070 'systemctl status leon-signal-hub-refresh.timer --no-pager | sed -n "1,40p"'
```

### Phase 6 — Final handoff

Final response must be plain-English first, not a log dump.

Include:

- whether SmactorIO is working now
- live URL
- what improvement ran
- what changed visibly
- proof that the existing scheduled runner is wired
- idempotency proof
- tests/scans result summary
- backup path
- anything still not implemented

Do not claim done unless live browser/HTTP verification passed.

## Expected definition of done

Done means:

- The spec was followed.
- The implementation plan was written and Opus-reviewed.
- The plan was patched based on valid findings.
- The runner exists and executed one real improvement.
- The SmactorIO cockpit visibly shows the improvement run.
- The existing scheduled Signal Hub runner invokes the SmactorIO improvement loop.
- A manual proof run completed before waiting on the timer.
- A second run proved idempotency.
- Local and rtx3070 tests/scans passed.
- Live URL works and is visually readable.
- Rollback backup exists.

---
