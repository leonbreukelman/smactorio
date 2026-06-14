# Opus adversarial review — SmactorIO roadmap-goal ingestion plan

Reviewed: 2026-05-15T20:33:44Z
Reviewer: Claude Code using latest available Opus requested via `claude --print --model opus --permission-mode plan`
Plan reviewed: `docs/plans/2026-05-15-smactorio-roadmap-goal-ingestion-plan.md`
Verdict: CONDITIONAL GO with required revisions

## Summary

The reviewer agreed that injecting a managed internal roadmap source into `state/source_state.json` is a defensible integration seam because it reuses the existing FSM classify/route/interpret/brief pipeline. The review found one correctness blocker and several silent-correctness/leak risks that must be addressed before implementation.

## Required changes accepted

1. Add real SQLite schema migration for the new FSM state because existing tables have CHECK constraints based on the old `FSM_STATES` set.
2. Confirm/update FSM state transition handling for `UPDATE_SOURCE_CACHE -> INGEST_ROADMAP_GOALS -> CLASSIFY_SIGNALS`.
3. Pin roadmap item observed dates to source-document mtime or source content hash, not ingestion time, to avoid recency gaming.
4. Prevent false-positive blocking from broad roadmap narrative text containing words like spend/delete/X list/2FA; source items should include only the actionable local item, while risky surrounding policy remains in private structured state.
5. Exclude the managed roadmap source from `source_health` liveness counts so it cannot mask scanner failure.
6. Redact source paths at the source-state/public boundary; no `/home/leonb`, `/srv/`, or `internal://` should appear in public HTML.
7. Use a lock in the standalone ingester to avoid races with the operating loop.
8. Include `state/roadmap_goals.json` in runtime backup coverage.
9. Record pre-ingest and post-ingest hashes/evidence, including `roadmap_goals_hash`.
10. Treat ingestion failure as degraded where safe, not blocked. Continue with prior source cache or prior roadmap_goals state.
11. Add SmactorIO classifier keywords narrowly: literal `smactorio` only at first; avoid broad `FSM`/`agent OS` cross-contamination.
12. Add tests for migration, no public path/internal URL leaks, false-positive routing, concurrency/lock, keyword cross-contamination, idempotent counts, and real FSM proof.

## Implementation consequence

The plan was patched to split the work into a safe v1:

- Add schema migration and FSM state support.
- Add deterministic redacted roadmap-source ingestion.
- Add a narrowly-scoped SmactorIO goal and classifier keyword.
- Add lock, backup, hashing, degrade-on-failure semantics.
- Verify with unit tests and an actual local FSM run.

## Review output excerpt

> Conditional GO with required revisions. The chosen seam (inject a managed internal source into state/source_state.json) is defensible — it reuses every downstream step cleanly. However, the plan as written has at least one correctness blocker (FSM_STATES CHECK constraint migration) and several silent-correctness/leak risks (recency gaming, false-positive blocking terms, source-path leakage path, inputs_hash drift, unmonitored backups). Do not implement until the items in Required plan changes are added.
