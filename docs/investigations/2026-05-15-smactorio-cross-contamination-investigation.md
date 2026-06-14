# SmactorIO cross-contamination investigation

Generated: 2026-05-15
Status: investigation only; no project remediation applied in this report

## Executive finding

The OSCAL mention was not random. The new SmactorIO work was cross-contaminated by the older `/home/leonb/projects/smactorio` repository.

The first contamination happened in the May 14 SmactorIO naming/contract session: after Leon said to reuse the SmactorIO name, Hermes searched for existing SmactorIO material, found the old local repo, and promoted it from "same-name prior project" into "relevant prior art / possible governance layer" without explicit confirmation.

The second contamination happened in the May 15 roadmap-ingestion session: the newer session treated that earlier assistant-created artifact as trusted baseline and then hard-coded the old repo's OSCAL roadmap as an allowlisted source.

## Canonical boundary from Leon's current correction

- New SmactorIO = the simple Project OS / Signal Hub operating loop created in the last two days.
- Old `/home/leonb/projects/smactorio` OSCAL/SDD project = obsolete / non-canonical unless Leon explicitly reauthorizes it.
- Name reuse did not mean architecture/content/source reuse.

This boundary has been saved to Hermes user memory so future sessions do not treat the old repo as canonical.

## Evidence timeline

### 1. User request that introduced the name

Session: `20260514_185726_caaaab`

Leon said to avoid the piOS issue and reuse a name previously used on another project, derived from Smart Factory -> Smactory -> SmactorIO. The requested work was to refactor the north star for more autonomy and real blocker/risk quantization.

Important distinction: the user asked to reuse the name. The user did not ask to reuse the old project contents.

### 2. Assistant discovery step that overreached

In the same session, Hermes immediately ran:

- `session_search` for `SmactorIO OR Smactory OR "Smart Factory"`
- `web_search` for `"SmactorIO" OR "Smactory"`
- `search_files` under `/home/leonb/projects` for `*smactor*`
- `read_file` on `/home/leonb/projects/smactorio/README.md`

This found the old repository and read its AI-first SDD / governance-as-a-service framing.

Root problem: discovery itself was not inherently bad, but the assistant failed to keep the result quarantined as "same-name old project, do not use without confirmation."

### 3. Assistant wrote the old repo into the new contract

File: `docs/contracts/2026-05-15-smactorio-autonomy-contract.md`

Problem line:

```text
The existing `/home/leonb/projects/smactorio` governance/SDD project is relevant prior art and may become the governance/control layer, but this contract is for the broader operating system loop.
```

This is the first durable source of contamination.

### 4. Assistant wrote the old repo into the machine capsule

File: `data/internal_work_capsules/smactorio-contract-2026-05-15.json`

Problem fields:

- `files_mentioned`: `external-local-prior-art:smactorio/README.md`
- `source_discovery_hints`: `Existing Smactorio repository`
- `reason`: old local repo contains governance-as-code and agentic SDD concepts that may become SmactorIO's governance/control layer

This pushed the old repo into the Signal Hub state as a proposed source candidate.

### 5. Assistant wrote the old repo into the walkthrough

File: `docs/walkthroughs/2026-05-15-smactorio-fsm-track-001.md`

Problem evidence:

- Prior local repo found: `/home/leonb/projects/smactorio`
- Prior repo README describes Smactorio as AI-first SDD with governance-as-a-service
- Source-candidate row created for the existing local Smactorio prior-art repository

### 6. Next session treated the contaminated artifact as baseline

Session: `20260515_163201_1a1b84`

The user asked for the next highest-leverage component for the SmactorIO project and an actual FSM run. The session used the contaminated baseline and wrote a roadmap-ingestion plan.

File: `docs/plans/2026-05-15-smactorio-roadmap-goal-ingestion-plan.md`

Problem lines:

- `SmactorIO canonical repo: /home/leonb/projects/smactorio`
- `Canonical SmactorIO roadmap found: /home/leonb/projects/smactorio/specs/SmactorioOscal/roadmap.md`
- V1 allowlisted source includes `/home/leonb/projects/smactorio/specs/SmactorioOscal/roadmap.md`

### 7. Implementation hard-coded the old repo / OSCAL source

File: `scripts/ingest_roadmap_goals.py`

Problem configuration:

```python
SMACTORIO_REPO = Path("/home/leonb/projects/smactorio")
DEFAULT_SOURCES = [
    {
        "id": "smactorio-oscal-roadmap",
        "label": "SmactorIO OSCAL roadmap",
        "path": str(SMACTORIO_REPO / "specs" / "SmactorioOscal" / "roadmap.md"),
        ...
        "optional": True,
    },
    ...
]
```

This made OSCAL part of the new loop's source allowlist.

## Current impact observed

Read-only scans were run against the dev copy and the rtx3070 production copy.

### Dev copy

Root: `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`

Files containing old/OSCAL markers include:

- `scripts/ingest_roadmap_goals.py`
- `state/roadmap_goals.json`
- `state/source_state.json`
- `public/autonomy_operating_loop.html`
- `public/projects/signal-hub.html`
- `docs/plans/2026-05-15-smactorio-roadmap-goal-ingestion-plan.md`
- `docs/contracts/2026-05-15-smactorio-autonomy-contract.md`
- `docs/walkthroughs/2026-05-15-smactorio-fsm-track-001.md`
- `data/internal_work_capsules/smactorio-contract-2026-05-15.json`
- `docs/verification/2026-05-15-smactorio-roadmap-goal-ingestion-functional-verification.md`

Generated `state/roadmap_goals.json` contains 116 records:

- 9 from `smactorio-simple-automation-roadmap`
- 101 from `signal-hub-project-intelligence-roadmap`
- 6 from `smactorio-oscal-roadmap`

So the dev copy actively ingested 6 old OSCAL roadmap items.

The local SQLite search found OSCAL matches in:

- `signals`: 6 rows
- `evidence`: 6 rows

### Production copy on rtx3070

Root: `/home/leonb/projects/leon-signal-hub`

Files containing old/OSCAL markers include:

- `scripts/ingest_roadmap_goals.py`
- `state/roadmap_goals.json`
- `docs/plans/2026-05-15-smactorio-roadmap-goal-ingestion-plan.md`
- `docs/contracts/2026-05-15-smactorio-autonomy-contract.md`
- `docs/walkthroughs/2026-05-15-smactorio-fsm-track-001.md`
- `data/internal_work_capsules/smactorio-contract-2026-05-15.json`
- `docs/verification/2026-05-15-smactorio-roadmap-goal-ingestion-functional-verification.md`
- `public/projects/signal-hub.html`

Production `state/roadmap_goals.json` contains 110 records:

- 9 from `smactorio-simple-automation-roadmap`
- 101 from `signal-hub-project-intelligence-roadmap`
- 0 from `smactorio-oscal-roadmap`, because the old external checkout is missing there

Production still carries an optional warning:

```text
smactorio-oscal-roadmap: FileNotFoundError: [local-path]
```

So production did not ingest OSCAL records, but the code and plan still attempt to use that old source.

## What was unclear vs. what went wrong

### The user's instruction was not fundamentally unclear

The phrase "reuse a name I have previously used on another project" means name reuse. It does not authorize source reuse, architecture reuse, or roadmap reuse.

### The ambiguity that enabled the mistake

Two phrases created an opportunity for a bad assumption:

1. "previously used on another project" revealed that a same-name older project existed.
2. Later, "For the smactorio project" did not explicitly say "new SmactorIO only; ignore the old repo."

Those phrases did not cause the issue by themselves. The real failure was the assistant's over-broad interpretation.

### Root cause

Hermes treated same-name historical material as potentially canonical instead of quarantined prior context.

The assistant should have used this rule:

> Same name is not same project. If a prior repo/project shares the name, treat it as untrusted prior art and ask before importing its content into the new system.

### Contributing factors

- The old repo path exactly matched the new name: `/home/leonb/projects/smactorio`.
- The assistant's project-discovery habit searched local repos after name reuse was mentioned.
- The contract incorrectly introduced "prior art may become governance/control layer."
- The capsule converted that incorrect assumption into a source candidate.
- The next session trusted those newly written artifacts as project baseline.
- Existing memory said SmactorIO was the user's Project OS umbrella but did not say the old repo was obsolete/non-canonical.

## Addressing this before remediation

Recommended guardrails before touching remediation:

1. Declare canonical boundary in plain text:
   - New SmactorIO source of truth is the Signal Hub / simple Project OS work created in the last two days.
   - Old `/home/leonb/projects/smactorio` is quarantined and obsolete unless Leon explicitly reauthorizes it.

2. Freeze old-source ingestion:
   - Remove `SMACTORIO_REPO` and `smactorio-oscal-roadmap` from `scripts/ingest_roadmap_goals.py`.
   - Add a regression test that fails if roadmap ingestion references `/home/leonb/projects/smactorio`, `SmactorioOscal`, `OSCAL`, or `governance-catalog` by default.

3. Remove old-source state:
   - Regenerate `state/roadmap_goals.json` and `state/source_state.json` from only new/canonical docs.
   - Clean local SQLite rows created from `smactorio-oscal-roadmap` in dev, after backing up the DB.
   - Confirm production remains free of OSCAL-derived DB rows.

4. Correct narrative artifacts:
   - Patch the contract, capsule, walkthrough, plan, and verification docs to mark the old repo reference as superseded/incorrect rather than current prior art.
   - Remove `Existing Smactorio repository` as a source candidate or mark it rejected/superseded.

5. Regenerate and verify public output:
   - Rebuild local pages.
   - Run the FSM.
   - Confirm no public or state artifact contains default old-source markers.
   - Sync to rtx3070 only after the local proof is clean.

6. Keep the memory guard:
   - Hermes user memory now records that old SmactorIO OSCAL/SDD content is obsolete/non-canonical unless explicitly reauthorized.

## Proposed remediation acceptance checks

Before declaring remediation complete:

- `scripts/ingest_roadmap_goals.py` has no default reference to `/home/leonb/projects/smactorio`, `SmactorioOscal`, `OSCAL`, or `governance-catalog`.
- Roadmap ingestion dry-run records only canonical new SmactorIO/Signal Hub roadmap sources.
- Dev `state/roadmap_goals.json` contains 0 records from `smactorio-oscal-roadmap`.
- Dev SQLite contains 0 OSCAL rows attributable to this new SmactorIO loop.
- Production `state/roadmap_goals.json` has no `smactorio-oscal-roadmap` warning.
- Public pages no longer present the old repo as prior art/source candidate.
- The SmactorIO homepage still keeps the simple operating loop message: one goal, one state card, one safe action, one check, one plain result.
