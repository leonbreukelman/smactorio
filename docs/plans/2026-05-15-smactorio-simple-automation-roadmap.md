# SmactorIO Simple Automation Roadmap

Status: active reset, updated for GitHub-backed autonomy on 2026-05-16

## Plain promise

Keep SmactorIO simple.

It should help Leon move one project forward, one small verified step at a time.

No big theory first. No developer wall of text first. The simple view stays on top; deeper autonomy details live behind the cockpit.

## What we do first

First we make the automation loop work.

The first useful loop is:

1. Goal: what do we want?
2. State card: where are we?
3. Priority gate: which one safe Candidate should run next?
4. Action: do one safe thing.
5. Check: did it work?
6. Show: explain the result and rollback path in plain English.

That is it.

## The simple FSM card

Every step should fit on one card:

- State: where are we?
- Input: what came in?
- Action: what will be done?
- Output: what changed?
- Check: how do we know it worked?
- Next: where do we go now?

## Current priority

Build the first GitHub-backed automation path that can run without a long explanation.

Current Candidate:

- `bootstrap-github-backed-smactorio-source-001`
- Purpose: put safe SmactorIO/Signal Hub source into the private GitHub repo without runtime state.
- Backing repo: `leonbreukelman/rtx3070-workshop-ops`, under `signal-hub/`.
- Rollback: branch + PR + git revert, not tarballs.
- Consolidated HTML: `smactorio_full_autonomy.html` holds the reviewed spec/plan/FSM details so this roadmap can stay simple.

## The development loop

Once a Candidate is selected, the work loop is:

1. Problem or root cause.
2. Research and reuse-first options.
3. Spec.
4. Independent spec review.
5. Plan.
6. Adversarial plan review.
7. Implement.
8. Automated tests.
9. Operator dry run as Leon.
10. Proof and handoff.

If the dry run finds a blocker, it goes back through the loop instead of being hidden.

## What moves to later

These are still valuable, but they are not first:

- RICE/WSJF views after the simple additive score works
- broad external source discovery
- many source discovery mechanisms
- long project intelligence graphs
- complex extraction from old conversations
- full improvement scoreboard
- auto-merge after branch protection and human policy are defined

They go on the roadmap parking lot until the basic GitHub-backed loop works.

## Rule for future pages

Show the simple view first.

Advanced details can exist, but they must sit behind the simple view.

The top of every SmactorIO page should answer:

- What are we doing now?
- What is the next tiny step?
- Why was this Candidate chosen?
- What does done look like?
- What GitHub branch/issue/PR backs it?
- How would rollback happen?
