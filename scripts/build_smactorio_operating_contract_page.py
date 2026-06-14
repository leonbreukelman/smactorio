#!/usr/bin/env python3
"""Build the SmactorIO visual operating contract page."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from page_shell import load_pages, render_page_shell, utc_now

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "smactorio_operating_contract.html"
PAGE_PATH = "smactorio_operating_contract.html"
SOURCE_DOC = ROOT / "docs" / "status" / "2026-05-15-smactorio-visual-operating-contract.md"
BLOCKED_MARKERS = ("<script", "javascript:", "data:", "/tmp/")


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def code_block(text: str) -> str:
    return f'<pre class="schema-code"><code>{esc(text.strip())}</code></pre>'


PYDANTIC_EXAMPLE = """
from pydantic import BaseModel, Field
from typing import Literal

class StepEnvelope(BaseModel):
    project_id: str
    state_id: str
    goal: str
    input_artifacts: list[str]
    risk_claims: list["RiskClaim"] = []
    evidence_refs: list[str] = []

class RiskClaim(BaseModel):
    claim: str
    action_under_consideration: str
    asset_at_risk: str
    risk_mechanism: str
    blast_radius: str
    max_loss: str
    reversibility: Literal["reversible", "backup_restore", "partial", "irreversible"]
    probes: list[str]
    residual_risk: Literal["low", "medium", "high", "unknown"]
    autonomy_decision: Literal["proceed", "guarded", "park", "ask_leon", "blocked"]
""".strip()

PROMPT_CONTRACT = """
State prompt =
  role: operator or reviewer
  input_schema: StepEnvelope
  output_schema: NextStepEnvelope
  action_rules: what can be done without asking
  stop_rules: measured conditions that require Leon
  evidence_rules: files, URLs, DB rows, hashes, tests
""".strip()


def build_architecture_svg() -> str:
    return """
<svg class="flow-svg" viewBox="0 0 1180 520" role="img" aria-labelledby="arch-title arch-desc">
  <title id="arch-title">SmactorIO goal to verified motion architecture</title>
  <desc id="arch-desc">A goal moves through project contract, typed state envelope, risk claim probe, safe action, evidence store, and visual URL.</desc>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#69e6ff"/>
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#8ef0c1"/>
    </marker>
    <linearGradient id="box-blue" x1="0" x2="1"><stop offset="0" stop-color="rgba(105,230,255,.22)"/><stop offset="1" stop-color="rgba(105,230,255,.08)"/></linearGradient>
    <linearGradient id="box-green" x1="0" x2="1"><stop offset="0" stop-color="rgba(142,240,193,.22)"/><stop offset="1" stop-color="rgba(142,240,193,.08)"/></linearGradient>
    <linearGradient id="box-violet" x1="0" x2="1"><stop offset="0" stop-color="rgba(199,166,255,.22)"/><stop offset="1" stop-color="rgba(199,166,255,.08)"/></linearGradient>
    <linearGradient id="box-amber" x1="0" x2="1"><stop offset="0" stop-color="rgba(255,208,113,.24)"/><stop offset="1" stop-color="rgba(255,208,113,.09)"/></linearGradient>
  </defs>
  <rect x="1" y="1" width="1178" height="518" rx="24" fill="rgba(2,6,23,.55)" stroke="rgba(255,255,255,.14)"/>
  <path d="M210 108 H333" class="arrow"/>
  <path d="M496 108 H620" class="arrow"/>
  <path d="M783 108 H906" class="arrow"/>
  <path d="M670 170 C650 250 560 275 472 304" class="arrow green"/>
  <path d="M760 170 C825 230 842 287 805 352" class="arrow"/>
  <path d="M454 352 H704" class="arrow green"/>
  <path d="M865 352 H987" class="arrow"/>
  <path d="M610 414 C522 475 322 461 212 170" class="return"/>

  <g class="node"><rect x="48" y="56" width="162" height="104" rx="18" fill="url(#box-blue)" stroke="#69e6ff"/><text x="69" y="91" class="node-title">Leon goal</text><text x="69" y="118" class="node-sub">plain language</text><text x="69" y="140" class="node-sub">desired outcome</text></g>
  <g class="node"><rect x="334" y="56" width="162" height="104" rx="18" fill="url(#box-green)" stroke="#8ef0c1"/><text x="356" y="91" class="node-title">Project contract</text><text x="356" y="118" class="node-sub">north star</text><text x="356" y="140" class="node-sub">authority envelope</text></g>
  <g class="node"><rect x="620" y="56" width="164" height="104" rx="18" fill="url(#box-violet)" stroke="#c7a6ff"/><text x="642" y="91" class="node-title">Typed envelope</text><text x="642" y="118" class="node-sub">Pydantic model</text><text x="642" y="140" class="node-sub">schema checked</text></g>
  <g class="node"><rect x="906" y="56" width="182" height="104" rx="18" fill="url(#box-amber)" stroke="#ffd071"/><text x="928" y="91" class="node-title">FSM step</text><text x="928" y="118" class="node-sub">prompt contract</text><text x="928" y="140" class="node-sub">operator action</text></g>

  <g class="node"><rect x="250" y="286" width="204" height="132" rx="18" fill="rgba(255,154,177,.11)" stroke="#ff9ab1"/><text x="276" y="323" class="node-title">Risk claim</text><text x="276" y="351" class="node-sub">asset + mechanism</text><text x="276" y="374" class="node-sub">probe plan + evidence</text><text x="276" y="397" class="node-sub">residual risk</text></g>
  <g class="node"><rect x="704" y="286" width="162" height="132" rx="18" fill="url(#box-green)" stroke="#8ef0c1"/><text x="728" y="323" class="node-title">Decision</text><text x="728" y="351" class="node-sub">proceed</text><text x="728" y="374" class="node-sub">guarded</text><text x="728" y="397" class="node-sub">ask Leon</text></g>
  <g class="node"><rect x="988" y="286" width="142" height="132" rx="18" fill="url(#box-blue)" stroke="#69e6ff"/><text x="1013" y="323" class="node-title">URL</text><text x="1013" y="351" class="node-sub">visual page</text><text x="1013" y="374" class="node-sub">proof</text><text x="1013" y="397" class="node-sub">next input</text></g>

  <g class="state-store"><rect x="496" y="214" width="228" height="70" rx="18" fill="rgba(255,255,255,.08)" stroke="rgba(255,255,255,.22)"/><text x="525" y="246" class="node-title">State store</text><text x="525" y="269" class="node-sub">SQLite + capsules + docs + hashes</text></g>
  <text x="42" y="486" class="caption">The output is both human-visible and machine-consumable: the page is for Leon; the capsule/schema/evidence feed the next FSM cycle.</text>
</svg>
""".strip()


def build_state_svg() -> str:
    states = [
        ("001", "Project contract", "name, north star, authority"),
        ("002", "Typed capsule", "structured input for next loop"),
        ("003", "Source discovery", "what signals matter now"),
        ("004", "Risk scoring", "convert blocker into claim"),
        ("005", "Safe action", "act inside envelope"),
        ("006", "Evidence URL", "show proof visually"),
        ("007", "Next cycle", "state becomes new input"),
    ]
    circles = []
    arrows = []
    x0 = 92
    y = 120
    gap = 158
    for index, (num, title, sub) in enumerate(states):
        x = x0 + index * gap
        words = sub.split()
        sub_lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word])
            if current and len(candidate) > 16:
                sub_lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            sub_lines.append(" ".join(current))
        sub_text = "\n".join(
            f'    <text x="{x}" y="{y+78+(line_index*13)}" text-anchor="middle" class="state-sub">{esc(line)}</text>'
            for line_index, line in enumerate(sub_lines[:2])
        )
        circles.append(f'''
  <g class="fsm-node">
    <circle cx="{x}" cy="{y}" r="48" fill="rgba(105,230,255,.10)" stroke="#69e6ff"/>
    <text x="{x}" y="{y-8}" text-anchor="middle" class="state-num">{num}</text>
    <text x="{x}" y="{y+14}" text-anchor="middle" class="state-title">{esc(title)}</text>
{sub_text}
  </g>''')
        if index < len(states) - 1:
            arrows.append(f'<path d="M{x+50} {y} H{x+gap-52}" class="arrow"/>')
    return f'''
<svg class="state-svg" viewBox="0 0 1180 285" role="img" aria-labelledby="fsm-title fsm-desc">
  <title id="fsm-title">Manual SmactorIO FSM track</title>
  <desc id="fsm-desc">The current manual state machine starts with project contract and cycles through typed capsule, source discovery, risk scoring, safe action, evidence URL, and next cycle.</desc>
  <defs>
    <marker id="fsm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#69e6ff"/></marker>
  </defs>
  <rect x="1" y="1" width="1178" height="283" rx="24" fill="rgba(2,6,23,.42)" stroke="rgba(255,255,255,.14)"/>
  {''.join(arrows)}
  {''.join(circles)}
  <path d="M1040 218 C840 263 340 263 92 218" class="return"/>
  <text x="590" y="266" text-anchor="middle" class="caption">Every state emits a checked output envelope; that output becomes the next state's input.</text>
</svg>
'''.strip()


def build_body() -> str:
    architecture = build_architecture_svg()
    state_machine = build_state_svg()
    schema = code_block(PYDANTIC_EXAMPLE)
    prompt_contract = code_block(PROMPT_CONTRACT)
    return f"""
<section id="picture" class="visual-section">
  <div class="eyebrow">Drawn picture</div>
  <h2>SmactorIO turns goals into verified motion</h2>
  <p class="lead">The short version: Leon gives a goal. SmactorIO keeps the project contract, checks every handoff with typed schemas, probes risk instead of guessing, acts when measured risk is inside bounds, then publishes evidence back to a URL.</p>
  <div class="svg-card">{architecture}</div>
</section>

<section id="fsm" class="visual-section">
  <div class="eyebrow">Manual FSM track</div>
  <h2>The current one-project walkthrough</h2>
  <div class="svg-card">{state_machine}</div>
  <div class="grid three">
    <article class="card mini"><h3>Current input</h3><p>SmactorIO contract + Leon request for a visual URL, process flow, state machine, graph, and schema explanation.</p></article>
    <article class="card mini"><h3>Processing now</h3><p>Generate a governed LAN-only page, register it in the manifest, and create an FSM-consumable capsule.</p></article>
    <article class="card mini"><h3>Output now</h3><p>A Signal Hub URL that shows the operating model visually and can become the next cycle's evidence.</p></article>
  </div>
</section>

<section id="schemas" class="visual-section">
  <div class="eyebrow">Typed contracts</div>
  <h2>Yes: Pydantic is the right boundary for step-to-step communication</h2>
  <div class="grid two">
    <article class="card"><h3>What Pydantic buys us</h3><ul>
      <li>Each FSM step receives a known shape, not vague prose.</li>
      <li>Each step emits a validated next-state envelope.</li>
      <li>Bad or incomplete outputs fail closed before they mutate state.</li>
      <li>JSON Schema can be exported for pages, prompts, tests, and non-Python tools.</li>
    </ul></article>
    <article class="card"><h3>Where prompts fit</h3><p>Prompts should not be free-form essays. They should be state contracts: role, input schema, output schema, allowed actions, stop rules, and evidence rules.</p>{prompt_contract}</article>
  </div>
  <article class="card schema-card"><h3>Starter shape, not final implementation</h3>{schema}</article>
</section>

<section id="risk" class="visual-section">
  <div class="eyebrow">Autonomy rule</div>
  <h2>A blocker becomes a testable risk claim</h2>
  <div class="risklane">
    <div class="riskpill danger">Sounds risky</div>
    <div class="riskarrow">→</div>
    <div class="riskpill">Asset</div>
    <div class="riskpill">Mechanism</div>
    <div class="riskpill">Max loss</div>
    <div class="riskpill">Probe</div>
    <div class="riskpill">Evidence</div>
    <div class="riskpill good">Residual decision</div>
  </div>
  <div class="grid two">
    <article class="card"><h3>Proceed autonomously when</h3><p>Local/private/LAN-only, reversible or backed up, no public mutation, no real spend, no raw transcript exposure, and residual risk is low or bounded-medium.</p></article>
    <article class="card"><h3>Ask Leon when</h3><p>Measured residual risk is high or unknown, the action spends money, mutates public/social/external accounts, deletes or rewrites hard-to-restore state, or is mostly a value judgment.</p></article>
  </div>
</section>

<section id="view" class="visual-section">
  <div class="eyebrow">Human control surface</div>
  <h2>What changes from here</h2>
  <div class="grid three">
    <article class="card"><h3>Less wall of text</h3><p>Long replies become source material. The review surface becomes pages with diagrams, state cards, proof links, and next-action buttons or questions.</p></article>
    <article class="card"><h3>Clearer questions</h3><p>When Leon is needed, the page should show the actual residual decision: what was tested, what remains unknown, and why his judgment matters.</p></article>
    <article class="card"><h3>Faster goals</h3><p>The loop does not restart from chat memory. It consumes typed state, runs probes, acts inside bounds, and keeps only high-value decisions for Leon.</p></article>
  </div>
</section>
""".strip()


def build_html() -> str:
    generated_at = utc_now()
    extra_head = """
<style>
.lead{font-size:1.12rem;color:var(--text);max-width:76rem}.visual-section{padding-top:30px}.svg-card{overflow:auto;border:1px solid var(--line);border-radius:26px;background:rgba(0,0,0,.20);box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}.flow-svg,.state-svg{display:block;min-width:980px;width:100%;height:auto}.arrow{fill:none;stroke:#69e6ff;stroke-width:3;marker-end:url(#arrow)}.state-svg .arrow{marker-end:url(#fsm-arrow)}.green{stroke:#8ef0c1;marker-end:url(#arrow-green)}.return{fill:none;stroke:#ffd071;stroke-width:2.5;stroke-dasharray:8 8}.node-title{font-size:18px;font-weight:900;fill:#eef7ff}.node-sub{font-size:14px;fill:#a8bbcf}.caption{font-size:14px;fill:#a8bbcf}.state-num{font-size:18px;font-weight:900;fill:#ffd071}.state-title{font-size:11px;font-weight:900;fill:#eef7ff}.state-sub{font-size:12px;fill:#a8bbcf}.grid.three{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.mini p{color:var(--text)}.schema-code{white-space:pre-wrap;overflow:auto;background:rgba(0,0,0,.28);border:1px solid rgba(255,255,255,.16);border-radius:18px;padding:16px;color:#dcecff}.schema-code code{color:#dcecff}.schema-card{margin-top:16px}.risklane{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:16px 0 18px}.riskpill{padding:12px 14px;border-radius:999px;border:1px solid rgba(105,230,255,.28);background:rgba(105,230,255,.10);color:#eef7ff;font-weight:800}.riskpill.danger{border-color:rgba(255,154,177,.5);background:rgba(255,154,177,.12)}.riskpill.good{border-color:rgba(142,240,193,.5);background:rgba(142,240,193,.13)}.riskarrow{color:#69e6ff;font-size:1.4rem;font-weight:900}@media(max-width:900px){.flow-svg,.state-svg{min-width:900px}}
</style>
""".strip()
    return render_page_shell(
        title="SmactorIO Operating Contract Visual",
        summary="Visual control surface for the SmactorIO autonomous project operating system: goal loop, FSM states, typed envelopes, prompt contracts, and risk scoring.",
        current_path=PAGE_PATH,
        body_html=build_body(),
        generated_at=generated_at,
        pages=load_pages(ROOT),
        root=ROOT,
        extra_head=extra_head,
    )


def validate_html(text: str) -> None:
    required = [
        "SmactorIO Operating Contract Visual",
        "SmactorIO turns goals into verified motion",
        "Manual FSM track",
        "Pydantic is the right boundary",
        "A blocker becomes a testable risk claim",
        "Private boundary",
        "data-signal-hub-shell=\"global\"",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"generated page missing markers: {missing}")
    lowered = text.lower()
    for marker in BLOCKED_MARKERS:
        if marker in lowered:
            raise ValueError(f"generated page contains blocked marker: {marker}")


def main() -> int:
    if not SOURCE_DOC.exists():
        raise FileNotFoundError(SOURCE_DOC)
    html_text = build_html()
    validate_html(html_text)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_name(f".{OUTPUT.name}.tmp")
    tmp.write_text("\n".join(line.rstrip() for line in html_text.splitlines()) + "\n", encoding="utf-8")
    tmp.replace(OUTPUT)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(json.dumps({"status": "ok", "path": str(OUTPUT), "sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
