# SmactorIO GitHub-backed Full Autonomy Spec

Status: revised after Opus review
Date: 2026-05-16
Owner: SmactorIO / Signal Hub
Review artifact: `docs/verification/2026-05-16-smactorio-github-backed-full-autonomy-spec-opus-review.md`

## 1. Plain answer

Prioritization should be a standalone governed step.

It should not be buried inside classification, and it should not be hidden inside final candidate selection.

The split is:

1. Classification says what the item is.
   - Example: bug, feature, research, ops, roadmap goal, error/log finding, user-requested product direction.
   - It may provide scoring hints, but it must not decide what runs next.
2. Normalization turns the item into one canonical Candidate shape.
   - Same schema whether the source was GitHub, roadmap prose, code, logs, or a conversation capsule.
3. Prioritization scores the Candidate deterministically.
   - The score is reproducible and auditable from evidence.
4. Candidate selection chooses what actually enters the development loop.
   - Selection uses priority plus dependencies, locks, work-in-progress limits, operator pins/vetoes, branch state, and current system safety.

Reason: classification is local to one item; selection is global to the queue; prioritization is the bridge between them. Mixing them makes the loop hard to audit and easy to game.

## 2. Full-autonomy goal

SmactorIO should become a self-sufficient, self-improving project operating system that can:

- consume internal sources first: code, GitHub Issues/Projects, roadmap docs, project pages, test failures, logs, run records, conversations summarized as safe capsules;
- consume external sources later: docs, release notes, public repos, RSS/web changes, ecosystem signals;
- let internal project intent steer which external signals matter;
- turn signals into normalized Candidates;
- score and select one bounded unit of work;
- move that unit through a governed development loop;
- commit and push every meaningful checkpoint to GitHub;
- use GitHub history, branches, tags, PRs, and revert commits for version control and rollback;
- update Signal Hub project pages so Leon sees the current state in plain English;
- learn from dry-run findings, failures, and reviews by feeding them back into the Candidate queue.

## 3. Current-state alignment

Observed current state before this spec:

- Signal Hub and SmactorIO source are present locally at `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub`.
- That local directory is not itself a git checkout.
- A private GitHub repo already exists: `leonbreukelman/rtx3070-workshop-ops`.
- That repo contains a `signal-hub/` subtree, but it is behind the local SmactorIO/Signal Hub work.
- Existing SmactorIO docs already define much of the development loop.
- The remaining architecture gap is making prioritization, GitHub-backed lifecycle, and the development loop first-class and visible.

Decision: use the existing private GitHub repo as the backing GitHub home for this Signal Hub/SmactorIO work unless Leon later chooses to split SmactorIO into its own repo.

### 3.1 Bootstrap Candidate

Because local source is ahead of the GitHub baseline, the first GitHub-backed autonomy step is itself a governed Candidate:

```text
candidate_id: bootstrap-github-backed-smactorio-source-001
purpose: package the current safe Signal Hub/SmactorIO source into the existing private GitHub repo without committing runtime state or clobbering unrelated ops files
```

Bootstrap rules:

1. Use a branch first. Do not make the first sync as an unreviewed destructive overwrite of `main`.
2. Compare local source against the current `leonbreukelman/rtx3070-workshop-ops` `signal-hub/` subtree before staging.
3. Path scope is `signal-hub/**` plus repo-level ignore/test/security configuration only when needed.
4. Denylist runtime and sensitive paths by default: `state/`, logs, databases, caches, backups, `.env*`, credentials, raw account manifests, and unreviewed broad `data/` dumps.
5. Allowlist only source-safe structured data needed to rebuild the SmactorIO pages, such as `signal-hub/data/project_homepages/smactorio.json` and `signal-hub/data/smactorio/*.json`, after secret scan.
6. Run the repo secret scanner before commit.
7. Push to GitHub and use the commit/branch/PR/revert path as rollback. Tarballs are not the normal rollback mechanism.

## 4. Source model

### 4.1 Internal sources

Internal sources are authoritative by default:

- GitHub Issues: canonical backlog items.
- GitHub Project fields: visible triage, priority, state, risk, source, ownership.
- Repository docs: specs, plans, reviews, verification reports, contracts, roadmap.
- Repository code/tests: implementation truth and regression surface.
- Local Signal Hub state: run records, errors, logs, classified signals, generated page status.
- Conversation capsules: compact, redacted summaries of project-relevant sessions, not raw transcript dumps by default.
- Project pages: current plain-English state shown to Leon.

### 4.2 External sources

External sources are advisory until grounded against internal intent:

- upstream project docs and release notes;
- relevant public GitHub repos;
- vendor docs;
- RSS/web/source-monitor deltas;
- public standards or ecosystem changes.

External items must not directly trigger implementation. They become Candidates only after they are linked to an internal project goal, open issue, roadmap item, failure, or explicit user direction.

## 5. FSM placement

The top-level Signal Hub FSM should expose SmactorIO autonomy as a first-class state:

```text
SYNTHESIZE_DAILY_BRIEF
  -> RUN_SMACTORIO_IMPROVEMENT_LOOP
  -> REBUILD_PROJECT_PAGES
  -> PUBLISH_LOCAL_SITE
  -> IDLE
```

Inside `RUN_SMACTORIO_IMPROVEMENT_LOOP`, SmactorIO runs a sub-FSM:

```text
INTAKE_WORK_SOURCES
  -> CLASSIFY_WORK_ITEMS
  -> NORMALIZE_CANDIDATES
  -> PRIORITIZE_CANDIDATES
  -> SELECT_DEVELOPMENT_CANDIDATE
  -> RUN_DEVELOPMENT_LOOP
  -> VERIFY_AND_DRY_RUN
  -> PUBLISH_PROOF_AND_ROLLBACK_ANCHOR
  -> LEARN_AND_REQUEUE
```

Failure from any sub-state goes to:

```text
QUARANTINE_CANDIDATE
```

with reason, evidence, and next unblock condition.

## 6. State responsibilities

| State | Responsibility | Output |
| --- | --- | --- |
| `INTAKE_WORK_SOURCES` | Read GitHub, roadmap docs, code/test failures, logs, conversations, local state. | Raw work signals with source/provenance. |
| `CLASSIFY_WORK_ITEMS` | Label each item by type, source, area, risk hint, urgency hint, and confidence. | Classified work item. |
| `NORMALIZE_CANDIDATES` | Convert each item into canonical Candidate schema. | Candidate record linked to evidence and/or issue. |
| `PRIORITIZE_CANDIDATES` | Compute deterministic priority score and breakdown. | `priority_score`, `priority_breakdown`, tie-break fields. |
| `SELECT_DEVELOPMENT_CANDIDATE` | Choose exactly one finishable item for the next development loop. | Selected Candidate, branch/issue/PR target. |
| `RUN_DEVELOPMENT_LOOP` | Execute problem -> research -> spec -> spec review -> plan -> adversarial review -> implementation. | Branch commits, spec/plan/review artifacts. |
| `VERIFY_AND_DRY_RUN` | Run automated tests and operator-as-user dry run. | Verification report and findings. |
| `PUBLISH_PROOF_AND_ROLLBACK_ANCHOR` | Push, update issue/project/site, tag or record rollback anchor. | PR/commit/tag/proof links. |
| `LEARN_AND_REQUEUE` | Convert findings into new or updated Candidates. | Queue updates and page/journal update. |

## 7. Candidate schema

A Candidate is the durable handoff unit between intake, scoring, selection, and development.

Required fields:

```text
id
candidate_dedup_key
source_type
source_ref
issue_number
project_area
type
moscow_hint
problem_statement
evidence_refs
expected_user_value
risk_summary
dependencies
scores
priority_score
priority_breakdown
classification_confidence
selection_status
autonomy_gate
branch_name
artifact_paths
rollback_plan
```

Candidate records may live as:

- GitHub Issue body metadata;
- GitHub Project fields;
- committed docs under `docs/smactorio/candidates/<id>/candidate.md`;
- local cache/state for faster runner operation.

GitHub is canonical for backlog/status. Local state is a cache and execution journal.

### 7.1 Idempotency keys

Every Candidate must have a reproducible deduplication key:

```text
candidate_dedup_key = sha256(source_type + ":" + source_ref)
```

Rules:

1. `INTAKE_WORK_SOURCES` skips or updates any signal whose dedup key already maps to an open Candidate.
2. `NORMALIZE_CANDIDATES` searches GitHub Issues before creating a new one.
3. GitHub Issue bodies include a hidden marker:

```text
<!-- smactor:dedup=<candidate_dedup_key> -->
```

4. Branch creation reuses an existing branch when `branch_name` already exists.
5. PR creation searches for an existing open PR from that branch before creating a new one.
6. The second consecutive run must not create duplicate Issues, Candidates, branches, PRs, or page claims for the same source signal.

## 8. Prioritization model

### 8.1 Primary score

Use the existing simple additive score as the primary score:

```text
priority_score =
  impact
+ confidence
+ reversibility
+ dependency_unblock
+ evidence_strength
- effort
- risk
- regression_surface
```

Each term is scored as an integer 0 to 5. The effective range is -15 to +25 before selection tie-breakers.

Meaning:

- `impact`: how much this advances the North Star or current roadmap.
- `confidence`: how sure we are that the item and solution are understood.
- `reversibility`: how easy it is to undo safely.
- `dependency_unblock`: how many future items this unlocks.
- `evidence_strength`: how concrete the proof/source is.
- `effort`: expected implementation size.
- `risk`: chance of harmful side effects, external mutation, security/privacy issue, or product confusion.
- `regression_surface`: amount of existing behavior likely to be disturbed.

### 8.2 Tie breakers

Tie-breakers are used by selection, not by rewriting the priority score:

1. Operator pin with reason.
2. Time criticality: deadline, active failure, broken page, failed scheduled loop, security issue.
3. Dependency unblock.
4. Small safe win quota: prefer effort 0-1 when it keeps momentum without hiding higher-risk blockers.
5. Age/staleness bonus logged only at selection time.

### 8.3 MoSCoW usage

MoSCoW is a prioritization hint, not a classification authority.

- Classification may emit `moscow_hint` when the source already makes urgency obvious.
- Prioritization may use that hint as evidence.
- Selection must not treat a MoSCoW label as sufficient to bypass score, risk, dependency, or human-gate rules.

### 8.4 RICE and WSJF usage

RICE and WSJF are useful as views, not as the first source of truth.

- RICE view: `(reach_proxy * impact * confidence) / max(effort, 1)`.
- WSJF view: `(impact + time_criticality + risk_reduction) / max(effort, 1)`.

For SmactorIO v1.5, keep the additive score canonical because it is easier to explain, audit, and debug. Add RICE/WSJF views later on the cockpit once the basic loop is stable.

### 8.5 Autonomous selection floor

Default thresholds:

```text
min_autonomous_score = +6
max_risk_for_autonomy = medium
min_classification_confidence = 2
```

Rules:

- Candidates below `min_autonomous_score` require an operator pin with reason.
- Autonomous Candidates must also satisfy per-axis floors: `impact >= 2`, `confidence >= 2`, and `evidence_strength >= 1`.
- High-risk Candidates require human review even when the score is high.
- Low-confidence risk classification is treated as `Needs Review` during selection.
- Deterministic ties resolve by lower risk, then older `created_at`, then lower issue number or stable Candidate id.
- The floor may be changed later, but only through a committed spec/plan update.

## 9. Candidate selection policy

Selection chooses one coherent, finishable unit.

Selection rules:

1. Refuse to run if the repo has unknown dirty work that cannot be classified.
2. Prefer `Ready` Candidates with high priority score.
3. Respect dependencies and quarantine cycles.
4. Do not select work requiring unapproved public/social/spend/destructive actions.
5. Do not select work that requires a missing credential or 2FA unless a safe local-only slice exists.
6. Do not select more than one implementation unit per run.
7. If no item is safe, write a blocked status and update the page rather than forcing a change.
8. Operator pin can force selection but must not alter score.
9. Re-validate risk during selection; low-confidence risk classification becomes `Needs Review`.
10. Refuse to start if an unexpired SmactorIO branch/PR is already in progress.
11. Acquire a single-writer lock before moving a Candidate to `Selected`.
12. Reject concurrent improvement-loop invocations with a clear status instead of running twice.
13. Requeue findings at most twice for the same source signal before escalating to human review.

## 10. Development loop

The governed development loop for a selected Candidate is:

1. Problem/root-cause or well-defined goal.
2. Research and reuse-first search.
3. Solution spec.
4. Independent spec review by the configured reviewer model.
5. Revised spec.
6. Implementation plan.
7. Adversarial plan review by the configured reviewer model.
8. Revised plan.
9. Implementation.
10. Automated tests.
11. Operator-as-user dry run.
12. Findings resolved through the same loop when needed.
13. Proof/handoff.

Every phase must leave an artifact. The loop is not complete until tests and dry run pass or the Candidate is quarantined with a clear reason.

### 10.1 Review model pinning

The review steps use a configured reviewer alias rather than an undefined phrase like "latest strong model".

Default reviewer for this spec generation: Claude Opus through Claude Code.

If the configured reviewer is unavailable, the Candidate does not silently skip review. It moves to `Needs Review` or `QUARANTINE_CANDIDATE` with the failure reason.

### 10.2 Operator-as-user dry run

The dry run is a concrete script or checklist where the agent acts as Leon using the built system:

- start from the project page or trigger path Leon would use;
- run the exact visible workflow step by step;
- record expected vs actual observations;
- classify findings as blocker, fix-now, backlog, or product note;
- resolve blockers before proof publication.

The dry run is evidence, not a ceremonial final checkbox.

## 11. GitHub lifecycle

### 11.1 Repo and branch model

Use GitHub as the source of truth for version control and rollback.

Default repo:

```text
leonbreukelman/rtx3070-workshop-ops
subdirectory: signal-hub/
```

This is a normal directory inside the private ops repo, not a separate git-subtree repository unless a future migration explicitly changes that.

Branch per Candidate:

```text
smactor/<issue-number>-<short-slug>
```

Use the issue number once a GitHub Issue exists. Use candidate id only for pre-Issue bootstrap or spikes.

Path scope rule:

- SmactorIO Candidate branches must normally modify only `signal-hub/**`.
- Repo-level files such as `.gitignore`, `.gitleaks.toml`, or `.github/**` may be changed only when the Candidate explicitly concerns repo safety/CI/review infrastructure.
- A pre-PR check should reject unrelated root/workshop/guardian changes.

### 11.2 Commit model

Commit and push meaningful checkpoints.

Recommended commit prefixes:

```text
spec: define candidate solution boundary
review: record spec or plan review
plan: define implementation steps
impl: implement bounded slice
test: add or update verification coverage
dryrun: record operator-as-user proof
proof: publish status, rollback, and handoff artifacts
```

Small doc-only candidates may use fewer commits, but the resulting history must still show what changed and why.

### 11.3 PR model

Preferred autonomous flow:

1. Create or update GitHub Issue.
2. Create Candidate artifact.
3. Create branch.
4. Push branch after spec/plan artifacts are written.
5. Open draft PR early.
6. Keep adding commits as the loop advances.
7. Mark PR ready only after tests and dry run pass.
8. Merge only after required review/operator gate is satisfied.

For low-risk private docs/page updates explicitly requested by Leon, direct push to `main` is acceptable only if branch protection policy allows it and the commit is verified. The safer default remains branch + PR.

### 11.4 Rollback model

Primary rollback is GitHub-native:

- revert commits or revert merge commits;
- tags on completed autonomy milestones;
- PR history and review comments;
- proof docs that state how to verify and revert.

Tag completed milestone merges as:

```text
smactor/<yyyy-mm-dd>-<short-slug>
```

The tag is written during `PUBLISH_PROOF_AND_ROLLBACK_ANCHOR` after verification and dry run pass.

Do not use tarballs as the normal rollback/versioning mechanism. Tarballs may only be emergency local host backups when touching live runtime files outside git; they are not the SmactorIO source-of-truth rollback path.

## 12. GitHub Issues/Project fields

GitHub Issues are the canonical backlog.

Recommended Project fields:

- `Status`: Inbox, Classified, Normalized, Prioritized, Selected, In Development, In Review, Verifying, Published, Quarantined, Archived.
- `Autonomy Gate`: Ready, Needs Review, Blocked Human, Blocked External, Unsafe, Verified.
- `Type`: Bug, Feature, Refactor, Research, Ops, Roadmap.
- `MoSCoW`: Must, Should, Could, Won't Now.
- `Priority Score`: numeric.
- `Score Breakdown`: text/JSON.
- `Risk`: Low, Medium, High, Security, Production.
- `Source`: Roadmap, Code, Conversation, Logs, Tests, External, User Vision.
- `Dependency`: linked issue(s).
- `Artifact Links`: spec, plan, review, proof, PR.

The project site may mirror these fields, but GitHub remains the actionable backlog.

## 13. Project page contract

SmactorIO project pages must stay simple first.

Top of page must answer:

- What is happening now?
- What is the next tiny step?
- What does done look like?
- Which Candidate is selected and why?
- What proof exists?
- What GitHub branch/issue/PR is backing it?
- How would rollback happen?

Advanced scoring details may be shown below the simple card or behind links.

### 13.1 Page markers contract

Generated SmactorIO pages must expose enough machine-checkable text or attributes for tests and future agents.

Required visible markers:

- `Priority gate`
- `GitHub-backed loop`
- `Rollback through git revert`
- `Selected candidate`
- `Priority score`
- `Development loop`
- `Operator dry run`

Recommended data attributes when a selected Candidate exists:

```text
data-candidate-id
data-priority-score
data-github-issue
data-github-branch
data-rollback-ref
```

The simple human page can stay plain-English; these markers ensure the page is also verifiable.

## 14. Autonomy gates

A Candidate can run without asking Leon only if it is:

- local/private;
- free;
- reversible through git;
- low or medium risk;
- backed by tests or a clear dry-run script;
- not a public/social mutation;
- not destructive;
- not credential/2FA blocked;
- not a product/value judgment requiring owner decision.

Human gate required for:

- public posting or social account mutation;
- spend above approved budget;
- destructive deletes;
- irreversible migrations;
- security/compliance/legal claims;
- unclear project direction or naming decisions;
- production deploy if not explicitly authorized for the current run.

## 15. Acceptance criteria for full-autonomy v1.5

SmactorIO reaches the next autonomy level when:

1. `RUN_SMACTORIO_IMPROVEMENT_LOOP` is a visible top-level FSM state.
2. GitHub repo/branch/commit/push is the normal checkpoint and rollback path.
3. GitHub Issues/Project can represent backlog, priority, status, and evidence links.
4. A roadmap item can become a Candidate with provenance.
5. Classification, normalization, prioritization, and selection are separate logged phases.
6. The selected Candidate enters the governed development loop.
7. Spec and plan review artifacts are saved.
8. Implementation runs tests.
9. Operator-as-user dry run is recorded.
10. Project pages show selected Candidate, priority reason, GitHub backing, proof, and rollback path.
11. Failed or unsafe work is quarantined, not silently skipped or forced.
12. A second consecutive run does not create duplicate Issues, Candidates, branches, PRs, or page claims for the same source signal.
13. A concurrent improvement-loop invocation is rejected with a clear status, not run.
14. Source packaging distinguishes safe committed source from private runtime data.

## 16. Non-goals for this slice

This spec does not require:

- full autonomous implementation of every phase immediately;
- broad external source discovery;
- auto-merge to protected main;
- paid API use beyond already available model/research tools;
- public publishing;
- raw transcript ingestion;
- complex graph intelligence before the simple loop is stable.

## 17. Open risks

- The local Signal Hub tree is ahead of the private GitHub baseline; packaging must avoid leaking runtime state and secrets.
- GitHub Project automation may require field setup that is not yet present.
- Generated site pages may depend on structured `data/` files currently ignored by the ops repo.
- Scoring can become false authority if evidence justifications are weak.
- Overly complex autonomy pages can overwhelm Leon; the UI must stay simple-first.

## 18. Immediate implementation direction

Immediate implementation should:

1. treat `bootstrap-github-backed-smactorio-source-001` as the current Candidate;
2. package the current safe Signal Hub/SmactorIO source into the existing private GitHub repo on a branch, not as an unreviewed main overwrite;
3. update `.gitignore`/allowlist rules so runtime state remains private while source-safe SmactorIO page data can be versioned;
4. update the SmactorIO roadmap and cockpit to show priority as a first-class gate;
5. document the GitHub-backed development loop and rollback model;
6. add tests that generated pages expose the new priority/GitHub/rollback markers;
7. run page-generation tests and secret scans;
8. push the verified docs/page update to GitHub as the first rollback-backed checkpoint;
9. then implement runtime FSM/state changes in a later Candidate branch.
