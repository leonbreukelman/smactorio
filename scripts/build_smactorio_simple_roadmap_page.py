#!/usr/bin/env python3
"""Build a simple SmactorIO automation-first roadmap page."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from page_shell import load_pages, render_page_shell, utc_now

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "plans" / "2026-05-15-smactorio-simple-automation-roadmap.md"
OUTPUT = ROOT / "public" / "smactorio_simple_roadmap.html"
PAGE_PATH = "smactorio_simple_roadmap.html"
BLOCKED_MARKERS = ("<script", "javascript:", "data:")


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def simple_flow_svg() -> str:
    steps = [
        ("1", "GOAL", "What do we want?"),
        ("2", "PRIORITY", "Which safe Candidate?"),
        ("3", "STATE", "Where are we?"),
        ("4", "DO", "One safe action"),
        ("5", "CHECK", "Did it work?"),
        ("6", "SHOW", "Plain result + rollback"),
    ]
    cards = []
    arrows = []
    for index, (number, title, note) in enumerate(steps):
        x = 28 + index * 166
        cards.append(
            f'''
            <g>
              <rect x="{x}" y="42" width="130" height="112" rx="20" fill="#10233a" stroke="#69e6ff" stroke-width="2"/>
              <circle cx="{x + 28}" cy="72" r="18" fill="#8ef0c1"/>
              <text x="{x + 28}" y="78" text-anchor="middle" font-size="18" font-weight="900" fill="#061019">{esc(number)}</text>
              <text x="{x + 65}" y="104" text-anchor="middle" font-size="18" font-weight="900" fill="#eef7ff">{esc(title)}</text>
              <text x="{x + 65}" y="131" text-anchor="middle" font-size="12" fill="#a8bbcf">{esc(note)}</text>
            </g>
            '''
        )
        if index < len(steps) - 1:
            ax = x + 136
            arrows.append(
                f'<path d="M {ax} 98 L {ax + 22} 98" stroke="#ffd071" stroke-width="5" stroke-linecap="round" marker-end="url(#arrow)"/>'
            )
    return f'''
    <svg class="simpleflow" viewBox="0 0 1040 205" role="img" aria-label="Simple SmactorIO automation flow">
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L9,3 z" fill="#ffd071"/>
        </marker>
      </defs>
      <rect x="1" y="1" width="1038" height="203" rx="26" fill="rgba(255,255,255,.04)" stroke="rgba(255,255,255,.16)"/>
      {''.join(cards)}
      {''.join(arrows)}
      <text x="520" y="184" text-anchor="middle" font-size="15" fill="#ffd071">Repeat only after the check and rollback path are clear.</text>
    </svg>
    '''


def build_body() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    return f'''
<section id="simple-first" class="simple-hero">
  <div class="eyebrow">SmactorIO reset</div>
  <h2>First: make the GitHub-backed automation work.</h2>
  <p class="big">One goal. One priority gate. One state card. One safe action. One check. One plain result.</p>
  {simple_flow_svg()}
</section>

<section id="now-next-done">
  <div class="grid three">
    <article class="card focuscard now"><div class="eyebrow">Now</div><h3>Bootstrap GitHub backing</h3><p>SmactorIO packages safe Signal Hub source into the private GitHub repo.</p></article>
    <article class="card focuscard next"><div class="eyebrow">Next tiny step</div><h3>Use the Priority gate</h3><p>Classification labels work; prioritization scores it; selection picks one safe Candidate.</p></article>
    <article class="card focuscard done"><div class="eyebrow">Done looks like</div><h3>Rollback is obvious</h3><p>The page shows the branch/PR/proof and says how to rollback through git revert.</p></article>
  </div>
</section>

<section id="github-backed-loop">
  <div class="grid three">
    <article class="card focuscard"><div class="eyebrow">Priority gate</div><h3>Standalone step</h3><p>Priority is not hidden inside classification. It sits between normalization and candidate selection.</p></article>
    <article class="card focuscard"><div class="eyebrow">GitHub-backed loop</div><h3>Issue → branch → PR</h3><p>GitHub becomes the audit trail for roadmap items, decisions, commits, reviews, and proof.</p></article>
    <article class="card focuscard"><div class="eyebrow">Rollback through git revert</div><h3>No tarball versioning</h3><p>Normal rollback is a revert branch/PR plus a proof note and reopened Candidate issue.</p></article>
  </div>
</section>

<section id="consolidated-plan-link">
  <article class="card focuscard">
    <div class="eyebrow">Consolidated HTML</div>
    <h2><a href="smactorio_full_autonomy.html">Full autonomy control plan</a></h2>
    <p>The reviewed spec, plan v2, Opus reviews, FSM placement, priority model, GitHub lifecycle, and operator dry-run contract are consolidated on one HTML page so this roadmap can stay simple.</p>
  </article>
</section>

<section id="development-loop">
  <article class="card">
    <div class="eyebrow">Development loop</div>
    <h2>One selected Candidate goes through the governed loop</h2>
    <ol>
      <li>Problem or root cause.</li>
      <li>Research and reuse-first options.</li>
      <li>Spec and independent review.</li>
      <li>Plan and adversarial review.</li>
      <li>Implement and run automated tests.</li>
      <li>Operator dry run as Leon.</li>
      <li>Proof, rollback anchor, and learning/requeue.</li>
    </ol>
  </article>
</section>

<section id="one-card-rule">
  <article class="card">
    <div class="eyebrow">One-card rule</div>
    <h2>Every FSM step must fit here</h2>
    <div class="stepgrid">
      <div><strong>State</strong><span>Where are we?</span></div>
      <div><strong>Input</strong><span>What came in?</span></div>
      <div><strong>Action</strong><span>What will be done?</span></div>
      <div><strong>Output</strong><span>What changed?</span></div>
      <div><strong>Check</strong><span>How do we know?</span></div>
      <div><strong>Next</strong><span>Where now?</span></div>
    </div>
  </article>
</section>

<section id="parking-lot">
  <article class="card parking">
    <div class="eyebrow">Roadmap parking lot</div>
    <h2>Important, but later</h2>
    <p>These ideas are not cancelled. They are parked until the simple automation loop works.</p>
    <ul>
      <li>self-improvement flywheel</li>
      <li>RICE/WSJF views after the additive Priority gate works</li>
      <li>many source discovery mechanisms</li>
      <li>long project intelligence graphs</li>
      <li>old conversation extraction</li>
      <li>full improvement scoreboard</li>
      <li>auto-merge after branch protection and human policy are defined</li>
    </ul>
  </article>
</section>

<section id="source-note">
  <article class="card source-note">
    <div class="eyebrow">Source note</div>
    <h2>The written roadmap is intentionally short</h2>
    <pre>{esc(source)}</pre>
  </article>
</section>
'''


def build_html() -> str:
    extra_head = """<style>
.simple-hero{padding-top:18px}.big{font-size:clamp(1.3rem,2.5vw,2rem);color:var(--text);font-weight:800}.simpleflow{width:100%;height:auto;margin-top:16px}.three{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}.focuscard{min-height:190px}.focuscard h3{font-size:1.55rem}.focuscard p{font-size:1.08rem;color:var(--text)}.now{border-color:rgba(142,240,193,.45)}.next{border-color:rgba(255,208,113,.45)}.done{border-color:rgba(105,230,255,.45)}.stepgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}.stepgrid div{border:1px solid rgba(255,255,255,.16);border-radius:20px;padding:16px;background:rgba(255,255,255,.07)}.stepgrid strong{display:block;font-size:1.35rem;color:#eef7ff}.stepgrid span{display:block;color:#a8bbcf;margin-top:6px}.parking li{font-size:1.08rem;margin:8px 0}.source-note pre{white-space:pre-wrap;overflow:auto;max-height:26rem;background:rgba(0,0,0,.23);border:1px solid var(--line);border-radius:18px;padding:16px;color:#dcecff}
</style>"""
    return render_page_shell(
        title="SmactorIO Simple Automation Roadmap",
        summary="A simplified GitHub-backed roadmap: one goal, one priority gate, one FSM step card, one safe action, one check, one plain result.",
        current_path=PAGE_PATH,
        body_html=build_body(),
        generated_at=utc_now(),
        pages=load_pages(ROOT),
        root=ROOT,
        extra_head=extra_head,
    )


def validate_html(text: str) -> None:
    required = [
        "SmactorIO Simple Automation Roadmap",
        "First: make the GitHub-backed automation work.",
        "One goal. One priority gate. One state card. One safe action. One check. One plain result.",
        "Priority gate",
        "GitHub-backed loop",
        "Rollback through git revert",
        "Development loop",
        "Operator dry run as Leon",
        "Roadmap parking lot",
        "LAN-only",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError(f"generated page missing markers: {missing}")
    lowered = text.lower()
    for marker in BLOCKED_MARKERS:
        if marker in lowered:
            raise ValueError(f"generated page contains blocked marker: {marker}")


def main() -> int:
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
