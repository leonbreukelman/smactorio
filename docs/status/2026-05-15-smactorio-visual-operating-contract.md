# SmactorIO visual operating contract surface

Created: 2026-05-15T02:00:00Z
Status: current visual/manual-walkthrough surface
Project surface: Signal Hub / SmactorIO project-intelligence loop

## Purpose

Leon asked that dense text handoffs become a human-friendly URL with visuals, process flows, state machines, and graph-like summaries. The text remains useful as machine-ingested SmactorIO FSM material, but the human control surface should be visual first.

## Decision

Create a LAN-only Signal Hub page named `smactorio_operating_contract.html` that draws the current SmactorIO operating model:

- SmactorIO is the autonomous project operating system.
- Signal Hub is the private LAN status and intelligence surface inside it.
- Each FSM step should receive and emit a typed envelope.
- Pydantic is the right Python boundary for validating those envelopes; exported JSON Schema can serve non-Python consumers.
- Prompts should be state-specific contracts: role, input schema, output schema, action rules, stop conditions, and evidence requirements.
- Blockers become testable risk claims, not automatic stops.
- Human escalation should be a measured residual-risk output, not the default behavior.

## Current visual output

Source generator: `scripts/build_smactorio_operating_contract_page.py`

Generated page: `public/smactorio_operating_contract.html`

LAN URL after publication: `http://192.168.30.10:8765/smactorio_operating_contract.html`

## FSM-consumable summary

Input:
- Leon requested a visual, URL-based explanation of the SmactorIO operating contract and asked whether Pydantic should define the handoff schemas between FSM steps.

Processing:
- Translate the previous text contract into a visual state-machine page.
- Register the page in `pages.json` so it appears in the Signal Hub dashboard.
- Keep the page LAN-only and generated from trusted local source.
- Preserve machine-ingestible capsule evidence for the next SmactorIO cycle.

Output:
- A governed static HTML page with diagrams, schema cards, and current manual FSM position.

Next state:
- Use the page as the human review surface while the FSM consumes the capsule and contract artifacts as structured evidence.
