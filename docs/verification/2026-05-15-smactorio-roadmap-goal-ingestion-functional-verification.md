# SmactorIO Roadmap Goal Ingestion Functional Verification

Generated: 2026-05-15T21:33:30Z

## Verdict

Implemented and production-verified.

The highest-leverage next component for SmactorIO autonomy is now in place: the Signal Hub finite-state machine consumes roadmap prose as a managed internal source of goals before classification/routing. This lets the existing FSM turn roadmap items into the same signal/action pipeline used by the rest of the operating loop.

## Implemented behavior

- Added roadmap-goal ingestion into the operating-loop FSM before signal classification.
- Converts roadmap prose into managed source records under `internal-smactorio-roadmap-goals`.
- Uses stable content-derived roadmap IDs instead of line-number IDs.
- Preserves word boundaries when truncating long roadmap items.
- Treats explicit truncation as degraded so silent under-ingestion cannot pass as fully OK.
- Increased default ingestion cap to 250; current dev-roadmap dry run consumes all 116 available records with no truncation warning.
- Keeps optional missing-roadmap files non-blocking while redacting local filesystem paths in warnings.
- Added cross-host publish support via `SIGNAL_HUB_CADDY_RSYNC_TARGET` so a runner on another machine can publish to the Caddy-served production host.
- Hardened public page rendering so generated LAN HTML does not leak `internal://`, `/srv/`, or local home paths from raw evidence.

## Review loop

- Plan was adversarially reviewed with latest available Opus via Claude CLI.
- Review verdict was conditional GO.
- Implemented reviewer recommendations:
  - stable content-derived IDs,
  - word-boundary truncation,
  - clearer degraded/warning behavior,
  - public path-leak guardrails.
- Schema-version feedback was intentionally not applied because the shared migration table already assigns Signal Loop to v2 and Project Intelligence to v3; bumping Signal Loop would reintroduce schema drift.

## Tests and verification

### Local/dev copy

Commands passed:

- `python3 -m unittest tests.test_roadmap_goal_ingestion tests.test_scan_for_secrets tests.test_full_autonomy_fsm`
  - 47 tests OK.
- `python3 -m compileall -q scripts tests`
  - OK.
- `python3 -m unittest discover -s tests`
  - 145 tests OK.
- `python3 scripts/ingest_roadmap_goals.py --dry-run`
  - status OK;
  - records: 116;
  - warnings: none.
- Actual FSM run from dev copy with remote Caddy rsync target:
  - run_id: 33;
  - final status: OK;
  - final state: IDLE.

Dev FSM trace highlights:

- `ingest_roadmap_goals`: OK, 116 records, warnings [], errors [].
- `classify_signals`: OK, 220 signals seen, 86 inserted, 134 updated.
- `route_actions`: OK, 86 queued actions, 0 blocked, 0 skipped.
- `publish_lan_static_pages`: OK, remote rsync.
- `verify_http`: OK, five live URLs checked.
- Public leak scan: no blocked public substrings found.

### Production host

Production source was backed up before sync:

- `state/source_backups/20260515T212651Z/pre-roadmap-goal-ingestion-sync.tgz`

Commands passed on production:

- `python3 -m unittest discover -s tests`
  - 147 tests OK.
- Actual production FSM run:
  - run_id: 39;
  - final status: OK;
  - final state: IDLE;
  - started: 2026-05-15T21:29:26+00:00;
  - finished: 2026-05-15T21:29:56+00:00.

Production FSM trace highlights for run 39:

1. `preflight`: OK.
2. `backup_runtime_state`: OK.
3. `scan_sources`: OK.
4. `update_source_cache`: OK.
5. `ingest_roadmap_goals`: OK, 110 records, managed source `internal-smactorio-roadmap-goals`.
6. `classify_signals`: OK, 214 signals seen, 0 inserted, 214 updated.
7. `route_actions`: OK/no-input, 0 queued on the final idempotency run because prior run had already routed new items.
8. `interpret_signals`: OK.
9. `synthesize_daily_brief`: OK.
10. `smactorio_improvement`: OK.
11. `build_project_intelligence_roadmap_page`: OK.
12. `build_dashboard`: OK.
13. `build_operating_loop_page`: OK.
14. `publish_lan_static_pages`: OK, local sync.
15. `verify_http`: OK, five URLs verified.

Production live HTTP/browser checks:

- `http://192.168.30.10:8765/` -> HTTP 200, no blocked public substrings.
- `http://192.168.30.10:8765/autonomy_operating_loop.html` -> HTTP 200, no blocked public substrings.
- `http://192.168.30.10:8765/ai_tech_signal_brief.html` -> HTTP 200, no blocked public substrings.
- `http://192.168.30.10:8765/project_intelligence_roadmap.html` -> HTTP 200, no blocked public substrings.
- `http://192.168.30.10:8765/projects/smactorio/` -> HTTP 200, no blocked public substrings.

Browser smoke confirmed the operating-loop page visibly shows:

- current status and metrics;
- latest FSM run status OK / state IDLE;
- `INGEST_ROADMAP_GOALS` in the transition table;
- canonical display path `public/autonomy_operating_loop.html` rather than an absolute filesystem path;
- system timer next-run information.

System timer status:

- system-scope `leon-signal-hub-refresh.timer`: active.
- user-scope timer: inactive/unused.

## Issues found and fixed during verification

1. Public dashboard leaked an absolute local path.
   - Fixed by rendering repo-relative `public/` display paths.

2. Operating-loop public page could embed raw evidence with local paths.
   - Fixed by render-time redaction and builder-level blocked-substring guard.

3. Roadmap ingestion silently truncated current roadmap items at the old default cap.
   - Fixed by increasing the default cap to 250 and marking explicit truncation as degraded.

4. Optional missing roadmap warning included local absolute path text.
   - Fixed by source-level warning/error path redaction.

## Current known non-blocking note

Superseded by `docs/status/2026-05-15-smactorio-retirement-and-pattern-extraction-boundary.md`.

Production now uses only repo-local canonical SmactorIO / Signal Hub roadmap sources. Earlier same-name external checkout material is retired and must not be installed, mirrored, or added for parity. If Leon later wants a specific reusable mechanism from retired material, it must follow the named pattern-extraction protocol in the retirement boundary note.

## Files changed by this milestone

Core scripts:

- `scripts/ingest_roadmap_goals.py`
- `scripts/run_operating_loop.py`
- `scripts/build_dashboard.py`
- `scripts/build_operating_loop_page.py`
- `scripts/signal_loop_db.py`

Tests:

- `tests/test_roadmap_goal_ingestion.py`
- `tests/test_full_autonomy_fsm.py`
- `tests/test_remote_publish_fallback.py`
- `tests/test_scan_for_secrets.py`

Verification/review docs:

- `docs/verification/2026-05-15-smactorio-roadmap-goal-ingestion-opus-review.md`
- `docs/verification/2026-05-15-smactorio-roadmap-goal-ingestion-functional-verification.md`

## Deployment/sync status

- Production source was updated by explicit rsync path list after backup.
- Public LAN pages were rebuilt and published by the FSM itself.
- No Git commit or push was performed because the working copies are deployed directories, not Git checkouts.
- No public internet deployment was performed.
- No X/list/social mutation was performed.
- Existing system timer remained active; no timer installation or scheduling change was made.
