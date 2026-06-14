# SmactorIO Improvement OS Specification

Created: 2026-05-15T03:56:01Z
Revised: 2026-05-15T04:05:00Z
Status: revised after read-only Opus adversarial review
Owner: Leon
Primary surface: Signal Hub project cockpit at `/projects/smactorio/`
Opus review artifact: `docs/verification/2026-05-15-smactorio-improvement-os-spec-opus-review.md`

## 1. Plain-English intent

SmactorIO should become the private autonomous project operating system that improves itself and other projects without becoming chaotic.

The operating system repeatedly asks:

1. What goal are we trying to achieve?
2. What is the current state?
3. What component could improve goal-to-progress motion?
4. What evidence says this is worth improving?
5. Can we use what already exists internally?
6. If not, can a safe external source/tool/pattern help?
7. If not, can an external thing be adapted?
8. If not, should custom work be built?
9. What is the smallest safe action?
10. How do we test it?
11. How do we roll it back?
12. What did we learn, and how does the cockpit show the result?

The first implementation must make this loop visible, runnable, idempotent, scheduled, and proof-backed. It must not become a broad research or LLM pipeline in v1.

## 2. Naming and boundary

Working boundary:

- **SmactorIO**: the autonomous project operating system. It owns the self-improvement loop, project-state loop, candidate scoring, and improvement governance.
- **Signal Hub**: the private LAN cockpit/status/evidence surface for SmactorIO and other projects.
- **Project Cockpit**: one project homepage inside Signal Hub, for example `/projects/smactorio/`.
- **Scheduled Signal Hub runner**: the existing live rtx3070 systemd timer `leon-signal-hub-refresh.timer`, which runs `scripts/run_operating_loop.py` daily. Current Hermes cron jobs do not include a Signal Hub job, so v1 must integrate with the existing systemd-backed Signal Hub runner and must not create a duplicate Hermes cron job.

Path boundary:

- Local/source checkout for implementation: `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`
- Live rtx3070 source checkout: `/home/leonb/projects/leon-signal-hub`
- Live Caddy-served public root: `/srv/leon-signal-hub/public`
- Live URL: `http://192.168.30.10:8765/projects/smactorio/`

## 3. North Star

SmactorIO converts goals into verified project motion by keeping state, discovering improvement opportunities, choosing the highest-value safe next action, executing within a clear authority envelope, verifying results, and showing Leon only the decisions that genuinely require human judgment.

Short human-facing version:

> One clear goal, one visible state, one safe improvement, one proof check, one plain result.

## 4. What exactly is being improved?

SmactorIO improves:

> A project's ability to turn a well-defined goal into verified progress with less human coordination, less confusion, better evidence, safer changes, and faster learning.

For v1, the concrete improvement target is SmactorIO itself, specifically the visible improvement cycle inside the SmactorIO project cockpit.

The first improvement run must execute one concrete file mutation outside `state/smactorio/`, verifiable by before/after SHA256 and visible on the cockpit. A run that merely writes a runtime record is not enough.

## 5. V1 non-negotiables

1. No live LLM calls.
2. No new outbound network calls except the network behavior already present in `scripts/run_operating_loop.py`.
3. No public/social/external account mutation.
4. No paid services or new billing exposure.
5. No raw transcript ingestion.
6. No broad source-discovery loop.
7. No scheduler replacement.
8. One candidate, one safe action, one proof check per run.
9. Idempotent second run: no duplicate journal entry and no duplicate candidate completion.
10. Existing Signal Hub daily brief/dashboard must continue working if SmactorIO runner skips or degrades.

## 6. Pillars

The Improvement OS has these pillars:

1. **Goal clarity**: maintain a visible North Star and current goal.
2. **State truth**: keep one current FSM state card that reflects real evidence.
3. **Component awareness**: know which components can be improved.
4. **Discovery**: find candidate improvements from internal and later external sources.
5. **Extraction**: extract usable claims, patterns, tools, risks, or ideas from sources.
6. **Candidate backlog**: store possible improvements as structured candidates, not immediate tasks.
7. **Prioritization**: score candidates by impact, effort, risk, confidence, reversibility, dependencies, evidence strength, and regression surface.
8. **Governance**: prefer existing internal capabilities before adding tools or custom code.
9. **Execution**: implement one small safe candidate at a time.
10. **Verification**: prove the change worked and did not break the working system.
11. **Learning**: update the cockpit, journal, component map, and reusable process docs where appropriate.

## 7. Component map contract

Source file:

`data/smactorio/component_map.json`

This is source data, not runtime-only state. It should be created during implementation before the first runner invocation.

Minimum structure:

```json
{
  "schema_version": 1,
  "project": "smactorio",
  "components": [
    {
      "id": "project-cockpit",
      "name": "Project Cockpit",
      "type": "surface",
      "purpose": "Show goal, current state, journal, decisions, proof, and links.",
      "current_evidence": ["data/project_homepages/smactorio.json", "public/projects/smactorio/index.html"],
      "improvement_questions": ["Is the current step clear?", "Can Leon see proof without reading logs?"],
      "risk_level": "low"
    }
  ]
}
```

Initial components:

- `north-star`
- `project-cockpit`
- `fsm-step-card`
- `journal-history`
- `internal-source-discovery`
- `external-source-discovery`
- `value-extraction-prompts`
- `candidate-backlog`
- `candidate-scoring`
- `safe-execution-runner`
- `verification-tests`
- `rollback-backups`
- `scheduled-runner`
- `human-decision-gates`

Schema rules:

- Reject unknown top-level keys.
- Reject duplicate component IDs.
- Reject component IDs that do not match `^[a-z0-9][a-z0-9-]{1,63}$`.
- Reject credential-looking IDs or labels.
- Do not over-model this into a knowledge graph in v1.

## 8. Improvement candidate contract

Source file:

`data/smactorio/improvement_candidates.json`

This is source data. Runtime run records go under `state/smactorio/`.

Minimum structure:

```json
{
  "schema_version": 1,
  "candidates": [
    {
      "id": "improve-cockpit-improvement-visibility-001",
      "status": "candidate",
      "title": "Show the Improvement OS loop on the SmactorIO cockpit",
      "component_id": "project-cockpit",
      "goal_link": "smactorio-north-star",
      "problem": "The cockpit shows the project, but not yet the self-improvement engine that decides what to improve next.",
      "evidence": ["Leon asked for a visible OS component that improves SmactorIO itself."],
      "strategy_order": ["internal_existing", "external_existing", "external_adapted", "custom_build"],
      "preferred_strategy": "internal_existing",
      "expected_gain": "Leon can see the improvement target, selected candidate, proof, and next action without reading logs.",
      "risks": ["Could clutter the cockpit if too much detail is shown."],
      "rollback": "Restore data/project_homepages/smactorio.json from backup and rebuild project homepages.",
      "execution": {
        "kind": "update_project_homepage",
        "path": "data/project_homepages/smactorio.json",
        "allowed_keys": ["current_step", "current_work", "journal", "proof", "template_notes", "improvement_os"],
        "summary": "Add or update the visible Improvement OS summary and latest selected candidate on the SmactorIO cockpit."
      },
      "tests": [
        "python3 -m unittest tests.test_smactorio_improvement_runner",
        "python3 -m unittest tests.test_page_manifest_and_navigation",
        "python3 scripts/scan_for_secrets.py data/project_homepages/smactorio.json data/smactorio public/projects/smactorio/index.html"
      ],
      "scores": {
        "impact": 5,
        "effort": 2,
        "risk": 1,
        "confidence": 5,
        "reversibility": 5,
        "dependency_unblock": 5,
        "evidence_strength": 5,
        "regression_surface": 1,
        "priority": 21
      }
    }
  ]
}
```

Candidate statuses:

- `candidate`: discovered but not selected.
- `selected`: chosen for the next improvement run.
- `running`: currently being executed.
- `completed`: implemented and verified.
- `parked`: useful but not now.
- `blocked`: cannot proceed without a real blocker.
- `rejected`: intentionally not worth doing.

Execution kinds allowed in v1:

- `update_project_homepage`: mutate only allowlisted keys in `data/project_homepages/smactorio.json`.
- `update_candidate_status`: mutate candidate `status`, `selected_at`, `completed_at`, `last_run_id`, and `evidence` fields.
- `run_command_allowlist`: run only explicitly allowlisted local verification commands.

Do not interpret free-text `smallest_safe_action` as executable instructions. The runner executes only the structured `execution` block.

## 9. Prioritization rule

Priority is deterministic:

```text
priority = impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface
```

Scale each score from 1 to 5.

Rules:

- Priority below 1 auto-parks the candidate.
- Ties resolve by higher reversibility, then lower regression surface, then lexical candidate ID.
- Scores are recomputed by the runner; stored scores are updated only after validation.
- Scores are excluded from the idempotency hash.

## 10. Governance enforcement: internal first, external second, adapt third, custom last

Every selected candidate must record a strategy decision and must obey a path/action allowlist.

Strategy levels:

1. `internal_existing`: use existing files/tools/processes. Runner may mutate only:
   - `data/project_homepages/smactorio.json`
   - `data/smactorio/improvement_candidates.json`
   - `state/smactorio/**`
   - generated `public/projects/smactorio/index.html` through the existing builder
2. `external_existing`: v1 may record a candidate only. It may not fetch, vendor, or add external artifacts automatically.
3. `external_adapted`: v1 may record a candidate only. It may not modify code automatically.
4. `custom_build`: v1 implementation code may create scripts/tests during the implementation session, but the scheduled runner must not autonomously write arbitrary code.

If a candidate declares `internal_existing` but tries to write outside the allowlist, the run must abort with `status: blocked`.

Candidate tests are gating for completed status. A candidate cannot be marked `completed` unless its specified verification commands pass or are explicitly recorded as unavailable with a degraded/blocking decision.

## 11. Runtime runner

Script:

`scripts/smactorio_improvement_runner.py`

Required CLI flags:

- `--dry-run`: produce plan JSON without mutation.
- `--no-homepage-update`: run scoring and state evidence but do not update `data/project_homepages/smactorio.json`.
- `--force`: allow a manual second run even if the idempotency hash matches.
- `--timeout-seconds N`: default 120 seconds.

Lock:

- Lock file: `state/smactorio/.runner.lock`
- If another live runner holds the lock, return `status: locked`, exit code 2, and do not mutate source data.
- Lock file should include PID and started timestamp.

Run records:

- Directory: `state/smactorio/improvement_runs/`
- File name: `YYYYMMDDTHHMMSSZ-<run_id>.json`
- Latest pointer: `state/smactorio/latest_run.json`
- Retention: keep the last 30 run records by default.

Run-record schema:

```json
{
  "schema_version": 1,
  "run_id": "20260515T040500Z-improve-cockpit-improvement-visibility-001",
  "started_at": "2026-05-15T04:05:00Z",
  "finished_at": "2026-05-15T04:05:08Z",
  "status": "ok",
  "input_hash": "sha256hex",
  "selected_candidate_id": "improve-cockpit-improvement-visibility-001",
  "strategy": "internal_existing",
  "execution_kind": "update_project_homepage",
  "mutations": [
    {
      "path": "data/project_homepages/smactorio.json",
      "before_sha256": "sha256hex",
      "after_sha256": "sha256hex"
    }
  ],
  "checks": [
    {"name": "build_project_homepages", "status": "ok"},
    {"name": "candidate_tests", "status": "ok"},
    {"name": "secret_scan", "status": "ok"}
  ],
  "evidence": ["public/projects/smactorio/index.html", "data/project_homepages/smactorio.json"],
  "errors": []
}
```

Exit codes and stdout contract:

- Exit 0: `ok` or `completed`.
- Exit 2: `skipped` or `locked`.
- Exit 3: `degraded`.
- Exit 4: `blocked`.
- Any other non-zero: failed/unhandled.
- stdout must be a single JSON object with `status`, `run_id`, `selected_candidate_id`, `input_hash`, `mutations`, `checks`, and `errors`.

## 12. Idempotency hash

The input hash must use a canonical projection that excludes mutable output fields.

Canonical form:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

Projection:

```json
{
  "components": [
    {"id": "...", "type": "...", "purpose": "..."}
  ],
  "candidates": [
    {"id": "...", "component_id": "...", "title": "...", "preferred_strategy": "...", "execution": {"kind": "...", "path": "..."}}
  ],
  "north_star": "...",
  "operating_rule": "..."
}
```

Excluded from the hash:

- candidate `status`
- scores
- timestamps
- journal entries
- current step
- runtime run records
- generated public HTML
- proof/check results

Required behavior:

- Same semantic inputs produce the same hash across repeated runs and Python restarts.
- Key reordering in JSON files must not change the hash.
- After a successful run, a second run without `--force` returns `skipped` and does not append another journal entry.
- `--force` may create a run record, but must still not duplicate the same human-visible journal entry unless it records a materially different result.

## 13. First concrete v1 improvement

The first completed improvement must be:

**Show the Improvement OS loop on the SmactorIO cockpit.**

Concrete action:

1. Select `improve-cockpit-improvement-visibility-001`.
2. Update `data/project_homepages/smactorio.json` with an `improvement_os` summary containing:
   - `what_is_being_improved`
   - `governance_rule`
   - `selected_candidate`
   - `latest_run_status`
   - `last_run_at`
   - `next_scheduled_run`
   - `proof`
3. Update the current step card to `IMPROVEMENT_RUN_COMPLETED` or `IMPROVEMENT_RUN_SKIPPED` as appropriate.
4. Add one journal entry for the first successful improvement run.
5. Rebuild the project homepage.
6. Run tests and secret scan.
7. Record before/after hashes.

This is a real improvement because the cockpit gains a visible self-improvement surface and a proof-backed selected candidate, not just a hidden runtime record.

## 14. Homepage rendering

`public/projects/smactorio/index.html` must show either a short `Improvement OS` section or a linked detail page.

V1 default: add a short homepage section. Split into a detail page later only if it becomes dense.

Minimum visible markers:

- `Improvement OS`
- `What is being improved`
- `Selected candidate`
- `Governance rule`
- `Latest improvement run`
- `Proof`
- `Next scheduled run`

The cockpit must remain readable. Long data stays in JSON/run records.

## 15. Integration with scheduled Signal Hub runner

Integration target:

`scripts/run_operating_loop.py`

Pinned insertion point:

After `SYNTHESIZE_DAILY_BRIEF` succeeds and before `REBUILD_DASHBOARD` / page rebuild / publish.

Step name:

`RUN_SMACTORIO_IMPROVEMENT_LOOP`

Invocation:

- Call `scripts/smactorio_improvement_runner.py` as a subprocess, not an import.
- Timeout: 120 seconds by default.
- Capture stdout JSON and stderr tail.
- Record a normal `run_step_results` entry.

Handling:

- Exit 0: continue.
- Exit 2 with `skipped` or `locked`: continue and record skipped/degraded evidence.
- Exit 3: continue as degraded.
- Exit 4: mark the SmactorIO step blocked/degraded, but do not crash the daily brief unless cockpit data is corrupt or unsafe.
- Other non-zero or invalid JSON: mark degraded/blocked and continue to rebuild existing pages where safe.

Dry run:

`python3 scripts/run_operating_loop.py --dry-run` must include `RUN_SMACTORIO_IMPROVEMENT_LOOP`.

## 16. Tests

Required new test file:

`tests/test_smactorio_improvement_runner.py`

Required tests:

1. Component map schema accepts valid seed data.
2. Component map schema rejects duplicate IDs, bad IDs, unknown top-level keys, and credential-looking IDs.
3. Candidate schema accepts valid seed data.
4. Candidate schema rejects bad statuses, unknown execution kinds, unsafe paths, and malformed scores.
5. Priority scoring is deterministic and auto-parks priority below 1.
6. Tie-breakers are deterministic.
7. Idempotency hash is stable across repeated calls, Python restarts if practical, and JSON key reordering.
8. First run updates `data/project_homepages/smactorio.json` and records before/after hashes.
9. Second run without `--force` returns skipped and does not create a duplicate journal entry.
10. Concurrent runner attempts produce one active run and one locked/skipped result.
11. Dry run does not mutate files.
12. Governance enforcement blocks writes outside the internal allowlist.
13. Page rebuild failure either rolls back the source mutation or records a degraded state with previous file backup preserved.
14. Candidate tests gate completed status.
15. Secret scanner includes `data/smactorio/` and relevant output paths.

Required updates to existing tests:

- `tests/test_page_manifest_and_navigation.py`: generated SmactorIO page contains Improvement OS markers.
- `tests/test_full_autonomy_fsm.py`: operating-loop dry-run and/or mocked run includes `RUN_SMACTORIO_IMPROVEMENT_LOOP` and handles ok/skipped/degraded/blocked runner statuses.
- `tests/test_deploy_static_public_to_caddy.py`: deploy/build pipeline includes the new runner/page-builder behavior only if needed and does not run the state-mutating runner during static deploy unless explicitly intended.
- `tests/test_build_operating_loop_page.py`: operating-loop page can show SmactorIO step evidence if exposed.

Verification commands:

```bash
python3 -m unittest tests.test_smactorio_improvement_runner
python3 -m unittest tests.test_page_manifest_and_navigation
python3 -m unittest tests.test_full_autonomy_fsm
python3 -m unittest discover -s tests -q
python3 scripts/scan_for_secrets.py data docs public scripts tests
```

Confirmed existing commands/flags:

- `scripts/run_operating_loop.py --skip-scan` exists.
- `scripts/scan_for_secrets.py` accepts positional paths.

## 17. Backup and rollback

Before broad local or live mutation, create a backup.

Live backup tarball path:

`/home/leonb/projects/leon-signal-hub/state/runtime_backups/smactorio-improvement-os-YYYYMMDDTHHMMSSZ.tar.gz`

Include at minimum:

- `data/project_homepages/smactorio.json`
- `data/smactorio/`
- `scripts/run_operating_loop.py`
- `scripts/smactorio_improvement_runner.py`
- `scripts/build_project_homepages.py`
- relevant tests
- `public/projects/smactorio/index.html`
- `docs/systemd/` if changed

Retention:

- Keep the last 10 SmactorIO improvement backups or the last 7 days, whichever retains more.

A restore helper is preferred if implementation time allows:

`scripts/smactorio_restore.py <backup_tarball>`

Minimum rollback without helper:

1. Stop or avoid running the timer during restore.
2. Extract backup into the live source checkout.
3. Rebuild project homepages and dashboard.
4. Copy `public/` to `/srv/leon-signal-hub/public`.
5. Verify HTTP 200 and expected markers.

## 18. Deployment and verification

Local/source verification:

1. Run targeted tests.
2. Build project homepages.
3. Run the improvement runner once.
4. Run it a second time and prove idempotency.
5. Run navigation/page tests.
6. Run secret scan.

Live rtx3070 verification:

1. Create live backup tarball.
2. Sync exact intended files only from local source checkout to rtx3070 source checkout.
3. Verify SHA256 hashes for changed source/test/data/doc files.
4. Run targeted tests on rtx3070.
5. Run `python3 scripts/smactorio_improvement_runner.py --force` once or run the full operating loop once if the state is safe.
6. Run `python3 scripts/run_operating_loop.py --skip-scan` or `systemctl start leon-signal-hub-refresh.service` to prove scheduled integration.
7. Verify service returns `status: ok` or acceptable `degraded` without breaking the daily brief/dashboard.
8. Verify `http://192.168.30.10:8765/projects/smactorio/` returns 200 and includes the required markers.
9. Browser visual check: readable, no layout overlap.
10. Browser console check: no errors.
11. Confirm `leon-signal-hub-refresh.timer` remains active.

HTTP freshness marker:

The live page must include a fresh `last_run_at` from the manual improvement run, not only an old static success.

## 19. Acceptance criteria for “working SmactorIO by tomorrow”

Leon should be able to open:

`http://192.168.30.10:8765/projects/smactorio/`

and see:

1. The original project cockpit still works.
2. An `Improvement OS` section is visible.
3. The page states what is being improved.
4. The page shows the selected candidate.
5. The page shows the governance rule.
6. At least one improvement run completed a real source-data mutation outside `state/smactorio/`.
7. The run record lists at least one mutated file with before/after SHA256.
8. The current step card and journal reflect the improvement run.
9. The existing scheduled Signal Hub runner is wired to trigger the improvement loop.
10. A manual proof run has already triggered the improvement loop, so proof does not depend on waiting for tomorrow's timer.
11. A second run proves idempotency and does not duplicate the same journal entry.
12. Tests and secret scans passed locally and on rtx3070.
13. Rollback backup exists.

## 20. First implementation plan requirements

A fresh implementation session must:

1. Read this spec and the Opus review artifact.
2. Inspect the local source checkout and live rtx3070 scheduler state.
3. Write a detailed implementation plan under `docs/plans/`.
4. Run a read-only Opus adversarial review of the plan.
5. Patch the plan based on valid Opus findings.
6. Implement the v1 slice using tests first.
7. Verify locally.
8. Back up and sync to rtx3070.
9. Verify on rtx3070.
10. Trigger one manual improvement run and one operating-loop integration run.
11. Verify live cockpit in browser.
12. Final handoff with plain-English result, URL, proof, backup path, and any remaining risk.

Do not stop after the plan. Implementation is part of the required fresh-session prompt.
