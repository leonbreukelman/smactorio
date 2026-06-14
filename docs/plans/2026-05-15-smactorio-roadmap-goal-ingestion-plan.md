# SmactorIO roadmap-goal ingestion into the Signal Hub FSM

Created: 2026-05-15T20:33:44Z
Status: draft for adversarial review

## Plain-English goal

Make the existing Signal Hub FSM consume SmactorIO roadmap items as real local goals, not just static documentation. The loop should be able to:

1. read the SmactorIO roadmap pages/docs,
2. convert actionable roadmap items into structured goal-like source items,
3. feed those items into the existing classify -> route -> interpret -> brief -> SmactorIO improvement path,
4. produce queued local actions and visible evidence,
5. do the same thing twice without duplicates.

## Why this is the next highest-leverage component

The SmactorIO website and first Improvement OS runner are already present. The next bottleneck is not another page section; it is that the roadmap is still mostly prose. The existing FSM can already classify signals, route low-risk work, interpret opportunities against `goals.json`, synthesize a daily brief, run the SmactorIO improvement runner, rebuild pages, publish, and verify HTTP output. Therefore the highest-leverage slice is an adapter that turns roadmap prose into the FSM's existing input shape.

This avoids building a second orchestrator. It uses the current local/LAN-private loop and gives SmactorIO a way to pull outstanding roadmap work into autonomous execution.

## Current baseline discovered

- New SmactorIO canonical implementation surface: Signal Hub / Project OS work under `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`.
- Signal Hub directory is not currently a git repository; rollback/proof must use tests, hashes, backups, and written artifacts.
- The earlier same-name SmactorIO repository is retired and non-canonical; its old roadmap/governance material is not an ingestion source.
- Canonical new-SmactorIO roadmap found: `docs/plans/2026-05-15-smactorio-simple-automation-roadmap.md`.
- Existing FSM entry point: `scripts/run_operating_loop.py`.
- Existing FSM data path: `state/source_state.json` -> `scripts/classify_signals.py` -> SQLite `signals` -> `scripts/route_actions.py` -> SQLite `actions` -> `scripts/interpret_signals.py` -> `scripts/synthesize_daily_brief.py` -> page builders.
- Existing goal configuration: `goals.json` and `goals.yaml`; classifier/interpreter already read `goals.json`.
- Existing SmactorIO improvement runner: `scripts/smactorio_improvement_runner.py` with candidate state under `data/smactorio/` and runtime proof under `state/smactorio/`.

## Design decision

Use the existing FSM input contract instead of creating a new FSM.

Add one deterministic internal-source ingestion step:

`UPDATE_SOURCE_CACHE -> INGEST_ROADMAP_GOALS -> CLASSIFY_SIGNALS`

The new step writes two artifacts:

1. `state/roadmap_goals.json`: structured, redacted, line-referenced roadmap-goal records.
2. A managed internal source inside `state/source_state.json` with id `internal-smactorio-roadmap-goals` whose `items` are shaped like normal scanner items.

Downstream components then work without special cases:

- `classify_signals.py` sees roadmap items as internal source items.
- `route_actions.py` queues safe local actions from high-confidence roadmap items.
- `interpret_signals.py` scores them against `goals.json`.
- `synthesize_daily_brief.py` surfaces them in the daily brief.
- `run_operating_loop.py` records an explicit FSM transition and step result for ingestion evidence.

## How the existing FSM is configured to consume roadmap items as goals

### Existing mechanism

The loop already treats `state/source_state.json` as source-cache input. A source has an `id`, `name`, status fields, and `items`. Each item can include a `title`, `url`, `summary`, and date-like field. `classify_signals.py` converts those items into durable `signals`. The classifier and interpreter already consult `goals.json` for area/goal alignment.

### New configuration

1. Add/keep a SmactorIO goal in `goals.json`:
   - id: `g6-smactorio-autonomous-project-os`
   - area: `smactorio`
   - title: `SmactorIO autonomous project OS`
   - next action: `Convert roadmap items into one safe local FSM step at a time.`

2. Extend classifier keyword routing so roadmap items containing SmactorIO/autonomous project OS/FSM/step-card language map to area `smactorio`, while preserving current areas.

3. Add `scripts/ingest_roadmap_goals.py` that:
   - reads a small allowlisted config of roadmap source docs,
   - extracts only actionable headings/list items from those docs,
   - computes stable ids and content hashes,
   - writes `state/roadmap_goals.json`,
   - merges/replaces the managed internal source in `state/source_state.json`,
   - never writes raw transcripts or secrets,
   - fails closed on malformed source docs or unsafe paths.

4. Add `INGEST_ROADMAP_GOALS` to the FSM state enum and dry-run/live run sequence.

## Roadmap source scope for v1

Allowlisted source docs only:

- `docs/plans/2026-05-15-smactorio-simple-automation-roadmap.md`
- `docs/plans/2026-05-14-signal-hub-project-intelligence-roadmap.md`

Explicitly excluded from v1: any earlier same-name SmactorIO checkout, compliance roadmap, governance catalog, or SDD artifact unless Leon later authorizes a named pattern extraction.

V1 will not mine raw conversations. It will not modify external accounts. It will not add cloud model calls. It will not publish outside the LAN surface.

## Structured roadmap-goal record

Each extracted record should include:

- `id`: stable slug/hash, e.g. `smactorio-roadmap-<hash12>`.
- `goal_id`: `g6-smactorio-autonomous-project-os` unless a source explicitly maps elsewhere.
- `project_area`: `smactorio`.
- `title`: short actionable text.
- `summary`: one-paragraph context, including source doc label and section.
- `source_path`: relative or allowlisted absolute path, redacted from public HTML unless needed as local evidence.
- `source_line`: first source line number when available.
- `source_section`: nearest markdown heading.
- `acceptance_hint`: extracted acceptance/check language when present.
- `recommended_route`: `to_action_low_risk` for local/documentation/test/build actions, `needs_human` for public/spend/destructive/account mutations.
- `risk_level`: `low`, `review_required`, or `blocked`.
- `content_sha256`: stable hash of normalized title/summary/source.
- `observed_at`: ingestion timestamp.

## Internal source item shape

Each record becomes a source item similar to:

```json
{
  "id": "smactorio-roadmap-abc123",
  "title": "SmactorIO roadmap: Add one goal -> step card -> action -> check loop",
  "summary": "Local roadmap item from simple automation roadmap. Goal: one goal, one FSM step card, one safe action, one check, one plain result. Recommended safe next action: implement/test the local ingestion adapter.",
  "url": "internal://smactorio-roadmap/smactorio-roadmap-abc123",
  "date": "2026-05-15T20:33:44Z"
}
```

The internal URL is not externally fetchable and `interpret_signals.py` already strips non-http(s) evidence URLs from public brief links.

## TDD acceptance criteria

1. `scripts/ingest_roadmap_goals.py --dry-run` returns JSON and does not mutate files.
2. The extractor finds the simple SmactorIO loop item from `docs/plans/2026-05-15-smactorio-simple-automation-roadmap.md`.
3. The extractor finds active Signal Hub roadmap phases from `docs/plans/2026-05-14-signal-hub-project-intelligence-roadmap.md` without importing backlog-only component-intelligence items as active goals.
4. Unsafe source paths, missing files, path traversal, symlink escapes, and active-content/credential-like text fail closed or are redacted.
5. A real ingestion writes `state/roadmap_goals.json` and replaces exactly one managed source in `state/source_state.json`.
6. Running ingestion twice with the same source docs is idempotent: same managed item ids, no duplicated source, no duplicate signals/actions after the full loop.
7. `classify_signals.py` maps SmactorIO roadmap items to `project_area='smactorio'` with `goal_id='g6-smactorio-autonomous-project-os'`.
8. `route_actions.py` queues low-risk local roadmap work but blocks/review-routes spend, public-posting, destructive, X-list, credential, or 2FA items.
9. `run_operating_loop.py --dry-run` includes `INGEST_ROADMAP_GOALS` after `UPDATE_SOURCE_CACHE` and before `CLASSIFY_SIGNALS`.
10. A mocked live FSM run records an `ingest_roadmap_goals` step result and continues to classification.
11. An actual local FSM run with `--skip-scan --no-publish` ingests roadmap goals, classifies at least one SmactorIO roadmap signal, and records the step evidence.
12. Secret scan over touched docs/scripts/data/state/public/test artifacts is clean.

## Implementation sequence

### Task 1: Tests first for extraction and idempotent source merge

Create `tests/test_roadmap_goal_ingestion.py` with fixtures that prove:

- markdown extraction returns active goal items from a minimal simple-roadmap fixture,
- backlog-only sections can be excluded,
- ids are stable across runs,
- managed source replacement is idempotent,
- unsafe paths and credential-like content are rejected/redacted,
- `--dry-run` does not mutate state files.

Expected first run: tests fail because the module does not exist.

### Task 2: Implement standalone roadmap-goal ingestion script

Create `scripts/ingest_roadmap_goals.py` with stdlib only:

- `RoadmapSource` dataclass or plain dict spec.
- `normalize_text`, `slugify`, `sha256_text`, `looks_credential_like` helpers.
- `safe_source_path(root, path)` allowlist validation.
- `extract_roadmap_goals(markdown, source_spec)`.
- `build_managed_source(records, generated_at)`.
- `merge_managed_source(source_state, managed_source)`.
- `ingest_roadmap_goals(root=ROOT, dry_run=False)`.
- CLI flags: `--dry-run`, `--source-state`, `--output`, `--max-items`.

### Task 3: Add SmactorIO goal and classifier support

Modify:

- `goals.json`
- `goals.yaml`
- `scripts/classify_signals.py`

Add tests that a roadmap item containing SmactorIO/FSM/step-card language maps to `smactorio` and to the new goal id.

### Task 4: Integrate with the FSM

Modify:

- `scripts/signal_loop_db.py`: add `INGEST_ROADMAP_GOALS` to `FSM_STATES`.
- `scripts/run_operating_loop.py`:
  - include `INGEST_ROADMAP_GOALS` in dry-run steps,
  - add `run_roadmap_goal_ingestion(ctx)`,
  - transition to `INGEST_ROADMAP_GOALS` after `UPDATE_SOURCE_CACHE`,
  - call `[sys.executable, "scripts/ingest_roadmap_goals.py"]`,
  - treat exit 0 as ok and non-zero as blocked only if JSON contract says unsafe/source failure; otherwise degrade conservatively.

### Task 5: Actual FSM proof run

Run:

```bash
cd /home/leonb/projects/ai-tech-signal-brief/leon-signal-hub
python3 -m unittest tests.test_roadmap_goal_ingestion
python3 -m unittest tests.test_full_autonomy_fsm
python3 scripts/ingest_roadmap_goals.py --dry-run
python3 scripts/ingest_roadmap_goals.py
python3 scripts/run_operating_loop.py --dry-run --skip-scan --no-publish
python3 scripts/run_operating_loop.py --skip-scan --no-publish
python3 scripts/scan_for_secrets.py data docs public scripts tests state/roadmap_goals.json state/source_state.json
```

Then query SQLite for:

- latest FSM run status,
- `ingest_roadmap_goals` step evidence,
- count of signals from `internal-smactorio-roadmap-goals`,
- count of queued actions linked to those signals,
- duplicate count after a second ingestion/full-loop pass.

## Functional trace expected

1. `PREFLIGHT`: verifies current source cache.
2. `BACKUP_RUNTIME_STATE`: preserves DB/source/public state.
3. `UPDATE_SOURCE_CACHE`: uses existing source cache when `--skip-scan` is set.
4. `INGEST_ROADMAP_GOALS`: reads roadmap docs, writes managed internal source, records item count/hash.
5. `CLASSIFY_SIGNALS`: turns roadmap items into durable `signals`.
6. `ROUTE_SAFE_ACTIONS`: queues low-risk local actions for roadmap items.
7. `INTERPRET_HIGH_VALUE_SIGNAL`: scores roadmap signals against SmactorIO goal.
8. `SYNTHESIZE_DAILY_BRIEF`: includes resulting local safe work in the brief.
9. `IMPROVE_SMACTORIO`: existing improvement runner remains in place.
10. `RECORD_RUN_OUTCOME`: records final status and returns to IDLE.

## Rollback plan

Before implementation, copy touched files or rely on generated state backups:

- `goals.json`
- `goals.yaml`
- `scripts/classify_signals.py`
- `scripts/run_operating_loop.py`
- `scripts/signal_loop_db.py`
- new `scripts/ingest_roadmap_goals.py`
- new `tests/test_roadmap_goal_ingestion.py`
- `state/source_state.json`
- `state/roadmap_goals.json`

Rollback is remove the new script/test, restore prior goal/classifier/FSM files from backup, and restore or delete the managed source id `internal-smactorio-roadmap-goals` from `state/source_state.json`.

## Adversarial review request

Ask latest available Claude/Opus in read-only mode to challenge:

- whether source-state injection is the right integration seam,
- whether this creates duplicate signals/actions,
- whether modifying `goals.json` is too broad,
- whether internal URLs or source paths can leak,
- whether the FSM should block or degrade on ingestion failure,
- whether tests actually prove an actual run rather than a mocked-only path.

## Review status

Opus/latest-Claude adversarial review completed and saved at `docs/verification/2026-05-15-smactorio-roadmap-goal-ingestion-opus-review.md`.

Verdict: CONDITIONAL GO with required revisions.

Required revisions incorporated before implementation:

1. Add a real SQLite migration for the new `INGEST_ROADMAP_GOALS` FSM state because existing tables have CHECK constraints generated from the old `FSM_STATES` set. Bump schema version and test old-row preservation.
2. Keep the integration seam as a managed internal source in `state/source_state.json`, but treat ingestion failure as degraded rather than blocked where safe.
3. Pin roadmap item dates to source-document mtime/content evidence, not ingestion time, so roadmap items do not permanently win recency scoring.
4. Store absolute source paths only in private `state/roadmap_goals.json`; source-state items must contain only redacted source labels, never `/home/leonb`, `/srv/`, or raw internal filesystem paths.
5. Do not put broad policy prose containing `spend`, `delete`, `X list`, `credential`, or `2FA` into source item summaries. Keep source item summaries focused on the actionable local item to avoid false `blocked_review` routing.
6. Exclude the managed roadmap source from `source_health` liveness counts so it cannot mask external scanner/source-cache failure.
7. Use a standalone ingester lock to avoid concurrent writes to `state/source_state.json`.
8. Include `state/roadmap_goals.json` in runtime backups.
9. Record pre-ingest source hash, post-ingest source hash, and `roadmap_goals_hash` in FSM evidence.
10. Add SmactorIO classifier support narrowly: literal `smactorio` and source-area hint only; do not broadly classify all FSM/agent/autonomous-OS language as SmactorIO.
11. Add tests for migration, no public path/internal URL leaks, false-positive routing, lock behavior, keyword cross-contamination, idempotent counts, and a real non-mocked FSM run.

## Revised implementation notes after review

### Schema migration

`signal_loop_db.py` must bump `SCHEMA_VERSION` and include an idempotent migration that rebuilds `fsm_runs` and `fsm_state_transitions` with the new CHECK constraint values. The migration must preserve existing rows and be tested against a simulated pre-v3 DB.

### Failure semantics

`run_operating_loop.py` should continue when ingestion fails safely:

- `ingest_roadmap_goals` exit 0: transition/step ok.
- Structured status `degraded`, lock contention, malformed non-critical source docs, or JSON parse failure: mark `ctx.degraded = True`, record evidence, continue to classification using existing source cache.
- Corrupt `state/source_state.json` is still caught by source-health checks and can block as before.

### Redaction boundary

Only `state/roadmap_goals.json` may include local source paths for private evidence. The managed source written into `state/source_state.json` must include source labels and section names only. Public HTML verification must assert absence of `/home/leonb`, `/srv/`, and `internal://`.

### Recency boundary

`date` on managed source items should be the source doc modification time, not the ingestion timestamp. Ingestion timestamp can appear in private ingestion metadata, not in item recency fields.

### Liveness boundary

`source_health` must ignore sources with `internal_only: true` or id `internal-smactorio-roadmap-goals` when counting `ok_sources`, `fresh_items`, and `total_items` for liveness. It may still include separate evidence counts for internal roadmap items.
