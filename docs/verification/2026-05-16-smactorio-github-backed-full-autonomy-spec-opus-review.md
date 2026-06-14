# Opus Review: SmactorIO GitHub-backed Full Autonomy Spec

Source reviewed: `docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
Reviewer: Claude Opus via Claude Code
Date: 2026-05-16

# Spec Review: SmactorIO GitHub-backed Full Autonomy

## 1. Verdict

**Approve with changes.** The four-phase separation is correct and the GitHub-backed lifecycle model is coherent. Two concrete blockers must be closed before this can drive autonomous execution: (a) the bootstrap path from local-ahead-of-remote, and (b) idempotency mechanics. Several non-blocking gaps will bite later if left vague.

## 2. Strongest parts

- **Section 1 framing.** The "classification is local, selection is global, prioritization is the bridge" sentence is the right load-bearing claim and the rest of the spec respects it.
- **Section 5–6 FSM with explicit `QUARANTINE_CANDIDATE`.** Naming quarantine as a first-class destination (not silent skip) is what keeps the loop auditable.
- **Section 8.1 additive score chosen over RICE/WSJF.** Right call for v1.5: explainable, debuggable, fits a single page card.
- **Section 8.2 keeping tie-breakers out of the score.** Prevents score laundering by selection logic.
- **Section 9 rule 1 (refuse on unknown dirty work) and rule 7 (write blocked status rather than force a change).** These two rules are what prevent chaotic autonomy.
- **Section 11.4 rejecting tarballs as the rollback path.** Correct; keeps a single source of truth.
- **Section 14 explicit human-gate list.** Concrete and defensible.

## 3. Blocking issues

### B1. Bootstrap path is undefined and the highest-risk single step.
Section 3 says local is ahead of remote and not itself a checkout; section 18.1 says "package the current safe source... without committing runtime state." There is no spec for:
- what "safe" is (allowlist? denylist? secret scan? `.gitignore` policy?);
- how the local tree becomes a working checkout without overwriting the existing `signal-hub/` subtree on the remote;
- how a divergence-vs-fast-forward is detected and resolved before the first push.
This step is itself a Candidate that needs its own spec/plan/review pass — but the spec uses it as a precondition. Risk of a destructive first push.

### B2. Idempotency mechanism is asserted but not specified.
Acceptance criterion 15.12 requires idempotency across runs, but nothing in §7 or §11 explains *how*. There is no:
- dedup key for Candidates from re-ingested signals (hash of `source_ref`? title+source_type?);
- search-before-create rule for GitHub Issues;
- branch-exists handling (reuse vs. new suffix);
- guard against double-creating PRs for the same Candidate ID across re-runs.
Without this, the second run silently breaks acceptance.

### B3. Subtree semantics are ambiguous.
§11.1 names `subtree: signal-hub/` but does not say whether this is a directory inside the ops repo or a git-subtree with separate history. Branch naming `smactor/<id>` says nothing about path scope. PRs touching files outside `signal-hub/` would be allowed by the spec as written. Needs an explicit "all SmactorIO Candidate branches must be path-scoped to `signal-hub/**`" rule, plus an `.github/CODEOWNERS` or PR check that enforces it.

### B4. No autonomy threshold on `priority_score`.
§8 produces a score in roughly [-9, +15] but §9 only says "prefer high score." Without a numeric floor below which autonomous selection refuses to run, a slow day will let weak Candidates through. Set an explicit `min_autonomous_score` and require operator pin below it.

### B5. Risk-band feeds the autonomy gate, but classification owns risk-band.
§14 gates on "low or medium risk" but risk is assigned in §6 `CLASSIFY_WORK_ITEMS`. A single misclassification therefore lets unsafe work into autonomous execution with no second check. Need either a re-validation in `SELECT_DEVELOPMENT_CANDIDATE` or a review-required default for any item whose risk classification has confidence below a threshold.

## 4. Non-blocking improvements

- **MoSCoW leak into classification (§6).** MoSCoW is a prioritization band, not a type label. Putting it in classification gives classification authority over what runs. Either move `moscow_band` into prioritization, or rename it `moscow_hint` to make the advisory nature explicit.
- **"Latest strong model" (§10 steps 4 and 7).** Undefined. Pin a model alias or a config key, with a fallback policy if it fails.
- **"Operator-as-user dry run" (§10 step 11).** Referenced as if defined elsewhere. Either link the existing definition or include a one-paragraph contract here.
- **Concurrency (§9).** Nothing about a second improvement loop starting while the first is mid-PR. Add a single-writer lock or a "no select if open SmactorIO branch is non-stale."
- **`LEARN_AND_REQUEUE` loop guard (§5/§6).** Findings can re-spawn the same Candidate. Need a max-requeue count per source signal and a "promotion to human review" rule when it trips.
- **Project page contract (§13) has no schema or test contract.** §18.4 mentions tests but does not say what markers the generator must emit. Spell them out as a small machine-checkable contract (e.g., `data-candidate-id`, `data-priority-score`, `data-rollback-ref` attributes).
- **Tag naming and timing (§11.4).** "Tags on completed autonomy milestones" is vague. Specify `smactor/v<n>` or `smactor/<date>-<slug>` and which state writes them.
- **Branch slug ambiguity (§11.1).** `<issue-number-or-candidate-id>` — define which one and when. Recommend: always issue-number once an Issue exists; candidate-id only for pre-Issue spikes.
- **Selection rule 4 on "spend" (§9).** No budget tracking specified. Either drop the word or reference a budget source.
- **Page generator may depend on ignored `data/` (§17).** This is flagged as a risk but no mitigation. Add a §18 step: define which `data/` files are public-safe vs. runtime-private.
- **Acceptance criterion 15.12 word choice.** "Route evidence" is unclear — likely "rotate" or a typo. Either way, restate.

## 5. Concrete patch recommendations

1. **Add §3.1 "Bootstrap Candidate."** Make "package local into existing remote without clobbering `signal-hub/`" an explicit named Candidate with its own spec/review/plan. Specify: a denylist of paths, a `git fetch && diff` step before any push, branch-only first push (no direct main), and a secret-scan gate.

2. **Add §7.1 "Idempotency keys."** Define `candidate_dedup_key = sha256(source_type + ":" + source_ref)`. Specify: `INTAKE` skips signals whose dedup key already maps to an open Candidate; `NORMALIZE` searches GitHub Issues by a hidden marker line (`<!-- smactor:dedup=<key> -->`) before creating; `SELECT` reuses an existing branch if `branch_name` exists.

3. **Tighten §11.1 to:** "All SmactorIO Candidate branches MUST modify only `signal-hub/**` plus `docs/smactorio/**`. A pre-PR check rejects branches that touch other paths." Add `CODEOWNERS` requirement to the §17 risks.

4. **Add §8.4 "Autonomous selection floor."** Define `min_autonomous_score` (suggest +6) and require operator pin below it. Also define a `max_risk_for_autonomy` symbol and bind §14 to it.

5. **Move `moscow_band` from §6 to §8** (or rename to `moscow_hint`). Update Candidate schema in §7 to reflect the move.

6. **Add §9 rule 9:** "Selection re-validates risk band; if classification confidence < threshold, treat as `Needs Review`." Removes the single point of failure in §14.

7. **Add §13.1 "Page markers contract."** Enumerate the required HTML data attributes or JSON keys the generator must emit, so §18.4 tests have something concrete to assert against.

8. **Add §10.1 "Model pinning."** Name the spec/plan reviewer model alias and the failure fallback (e.g., quarantine, not silently skip).

9. **Add §15.13:** "A concurrent improvement-loop invocation is rejected with a clear status, not run." Couple to the §9 lock.

10. **Reword §15.12** to remove "route evidence" ambiguity. Suggested: "A second consecutive run does not create duplicate Issues, Candidates, branches, PRs, or page claims for the same source signal."

## 6. Specific answer on prioritization placement

**Yes — prioritization is placed correctly** as a standalone, governed step between `NORMALIZE_CANDIDATES` and `SELECT_DEVELOPMENT_CANDIDATE`. The reasoning in §1 is sound: classification is per-item, selection is queue-global, prioritization bridges the two with a deterministic, auditable score. Keeping tie-breakers in §8.2 out of the score and in selection is the right call and prevents the most common failure mode (selection silently rewriting priority).

The one placement leak that should be fixed is §6's `moscow_band` sitting inside classification — MoSCoW is a prioritization concept and putting it upstream of `PRIORITIZE_CANDIDATES` lets a labeler implicitly outrank the score. Either relabel it as a hint or move it to §8. With that single fix and the autonomous-floor in §8.4, the prioritization phase is correctly positioned and load-bearing in the right place.
