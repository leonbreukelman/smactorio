#!/usr/bin/env python3
"""Build the consolidated SmactorIO full-autonomy HTML control plan."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from page_shell import load_pages, render_page_shell, utc_now

ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = "smactorio_full_autonomy.html"
OUTPUT = ROOT / "public" / PAGE_PATH
SPEC = ROOT / "docs" / "specs" / "2026-05-16-smactorio-github-backed-full-autonomy-spec.md"
SPEC_REVIEW = ROOT / "docs" / "verification" / "2026-05-16-smactorio-github-backed-full-autonomy-spec-opus-review.md"
PLAN = ROOT / "docs" / "plans" / "2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md"
PLAN_REVIEW = ROOT / "docs" / "verification" / "2026-05-16-smactorio-github-backed-full-autonomy-plan-opus-review.md"
ROADMAP = ROOT / "docs" / "plans" / "2026-05-15-smactorio-simple-automation-roadmap.md"
BLOCKED_MARKERS = ("<script", "javascript:", "data:")


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_row(label: str, path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    digest = sha256(path) if path.exists() else "missing"
    size = path.stat().st_size if path.exists() else 0
    return f"""
    <tr>
      <th>{esc(label)}</th>
      <td><code>{esc(rel)}</code></td>
      <td><code>{esc(digest[:16])}</code></td>
      <td>{esc(size)} bytes</td>
    </tr>
    """


def ordered(items: list[str]) -> str:
    return "<ol>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ol>"


def unordered(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def extract_section(path: Path, heading: str, *, max_chars: int = 1800) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.find(heading)
    if start < 0:
        return f"{heading}\n\nSection not found in {path.name}."
    next_heading = text.find("\n## ", start + len(heading))
    section = text[start: next_heading if next_heading > start else len(text)].strip()
    if len(section) > max_chars:
        section = section[:max_chars].rstrip() + "\n\n[…trimmed in HTML; source doc remains authoritative…]"
    return section


def build_body() -> str:
    top_level_states = [
        "SYNTHESIZE_DAILY_BRIEF",
        "RUN_SMACTORIO_IMPROVEMENT_LOOP",
        "REBUILD_PROJECT_PAGES",
        "PUBLISH_LOCAL_SITE",
        "IDLE",
    ]
    sub_states = [
        "INTAKE_WORK_SOURCES",
        "CLASSIFY_WORK_ITEMS",
        "NORMALIZE_CANDIDATES",
        "PRIORITIZE_CANDIDATES",
        "SELECT_DEVELOPMENT_CANDIDATE",
        "RUN_DEVELOPMENT_LOOP",
        "VERIFY_AND_DRY_RUN",
        "PUBLISH_PROOF_AND_ROLLBACK_ANCHOR",
        "LEARN_AND_REQUEUE",
    ]
    dev_loop = [
        "Problem/root-cause or clear goal",
        "Research and reuse-first options; do not reinvent the wheel",
        "Spec for the selected solution",
        "Independent spec review, then revised spec",
        "Plan for implementation",
        "Adversarial plan review, then revised plan",
        "Implementation in a GitHub branch",
        "Automated tests and regression checks",
        "Operator dry run as Leon, step by step",
        "Findings routed back through the loop until proof/handoff is clean",
    ]
    source_rows = "".join(
        [
            source_row("Reviewed spec", SPEC),
            source_row("Opus spec review", SPEC_REVIEW),
            source_row("Plan v2", PLAN),
            source_row("Opus adversarial plan review", PLAN_REVIEW),
            source_row("Simple roadmap", ROADMAP),
        ]
    )
    return f"""
<section id="control-plan-hero" class="autonomy-hero">
  <div class="eyebrow">SmactorIO Full Autonomy Control Plan</div>
  <h2>Consolidated from reviewed spec, plan v2, and Opus reviews</h2>
  <p class="bigline">This is the HTML surface that aligns the docs with the project cockpit: one roadmap-consuming autonomy loop, one priority gate, one selected Candidate, one GitHub-backed development cycle, and one proof path.</p>
  <div class="tags">
    <span class="tag">docs/specs</span>
    <span class="tag">docs/plans</span>
    <span class="tag">docs/verification</span>
    <span class="tag">public HTML</span>
  </div>
</section>

<section id="plain-answer">
  <div class="grid two">
    <article class="card">
      <div class="eyebrow">Plain status</div>
      <h2>HTML is now consolidated</h2>
      <p>The cockpit stays simple, the roadmap stays simple, and this page carries the deeper first-class FSM/development-loop contract so the public HTML matches the reviewed documentation.</p>
    </article>
    <article class="card">
      <div class="eyebrow">Current Candidate</div>
      <h2><code>bootstrap-github-backed-smactorio-source-001</code></h2>
      <p>Purpose: package safe SmactorIO/Signal Hub source into <code>leonbreukelman/rtx3070-workshop-ops</code> under <code>signal-hub/</code> without runtime state.</p>
    </article>
  </div>
</section>

<section id="fsm-placement">
  <article class="card">
    <div class="eyebrow">Top-level FSM placement</div>
    <h2>SmactorIO sits between daily synthesis and project-page publication</h2>
    <div class="flow" aria-label="Top-level FSM placement">
      {''.join(f'<span class="flow-node"><code>{esc(state)}</code></span>' for state in top_level_states)}
    </div>
    <p>The key missing runtime slice is to make <code>RUN_SMACTORIO_IMPROVEMENT_LOOP</code> a first-class Signal Hub FSM state, not an implicit standalone script call.</p>
  </article>
</section>

<section id="sub-fsm">
  <article class="card">
    <div class="eyebrow">Roadmap-consuming sub-FSM</div>
    <h2>Work moves through intake, classification, standalone priority, selection, development, proof, and learning</h2>
    {ordered(sub_states)}
    <p><strong>Priority gate rule:</strong> <code>PRIORITIZE_CANDIDATES</code> is separate from classification and separate from final candidate selection.</p>
  </article>
</section>

<section id="development-loop">
  <article class="card">
    <div class="eyebrow">RUN_DEVELOPMENT_LOOP</div>
    <h2>One selected Candidate goes through the reviewed development cycle</h2>
    {ordered(dev_loop)}
  </article>
</section>

<section id="priority-model">
  <div class="grid two">
    <article class="card">
      <div class="eyebrow">Priority model</div>
      <h2><code>impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface</code></h2>
      <p>Axis bounds are 0-5. Autonomous floors are <code>impact &gt;= 2</code>, <code>confidence &gt;= 2</code>, and <code>evidence_strength &gt;= 1</code>. Minimum autonomous score is <code>6</code>, with max risk no higher than medium.</p>
    </article>
    <article class="card">
      <div class="eyebrow">GitHub-backed loop</div>
      <h2>GitHub issue → branch → PR → revert</h2>
      <p>GitHub Issues become the canonical backlog. Branches and PRs carry implementation and review. Rollback is git revert/revert PR plus a proof note, not a tarball habit.</p>
    </article>
  </div>
</section>

<section id="governance">
  <div class="grid three">
    <article class="card">
      <div class="eyebrow">Candidate limit</div>
      <h3>One selected Candidate per run</h3>
      <p>Autonomy advances by finishing one bounded item, not by spraying work across many issues.</p>
    </article>
    <article class="card">
      <div class="eyebrow">Review gates</div>
      <h3>Spec review and adversarial plan review remain mandatory</h3>
      <p>Opus review artifacts stay in <code>docs/verification/</code> and future revisions get new dated/versioned files.</p>
    </article>
    <article class="card">
      <div class="eyebrow">Operator proof</div>
      <h3>Operator dry run as Leon</h3>
      <p>Before handoff, the agent acts as the user and runs the workflow step by step. Findings re-enter the development loop.</p>
    </article>
  </div>
</section>

<section id="doc-sources">
  <article class="card">
    <div class="eyebrow">Documentation sources</div>
    <h2>Source documents and hashes</h2>
    <table>
      <thead><tr><th>Artifact</th><th>Path</th><th>SHA256 prefix</th><th>Size</th></tr></thead>
      <tbody>{source_rows}</tbody>
    </table>
  </article>
</section>

<section id="source-excerpts">
  <div class="grid two">
    <article class="card source-excerpt">
      <div class="eyebrow">Spec excerpt</div>
      <h2>FSM placement</h2>
      <pre>{esc(extract_section(SPEC, '## 5. FSM placement'))}</pre>
    </article>
    <article class="card source-excerpt">
      <div class="eyebrow">Plan excerpt</div>
      <h2>Bootstrap source safely</h2>
      <pre>{esc(extract_section(PLAN, '## Phase 0 — Bootstrap source into GitHub safely'))}</pre>
    </article>
  </div>
</section>

<section id="what-next">
  <article class="card">
    <div class="eyebrow">Next executable slice</div>
    <h2>Execute the bootstrap Candidate, then wire the runtime state</h2>
    {unordered([
        'Package safe source into the private GitHub repo on branch smactor/bootstrap-github-backed-autonomy.',
        'Open a PR and keep runtime state/logs/databases/credentials out of Git.',
        'After the source is GitHub-backed, implement RUN_SMACTORIO_IMPROVEMENT_LOOP as a visible FSM state.',
        'Dry-run the full path as Leon and publish proof back to the cockpit.',
    ])}
  </article>
</section>
"""


def build_html() -> str:
    extra_head = """<style>
.autonomy-hero .bigline{font-size:clamp(1.2rem,2.4vw,1.8rem);font-weight:800;color:var(--text)}
.two{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}.three{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.flow{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:18px 0}.flow-node{display:inline-flex;align-items:center;border:1px solid rgba(105,230,255,.35);border-radius:999px;padding:9px 12px;background:rgba(105,230,255,.08)}.flow-node:not(:last-child)::after{content:"→";color:var(--amber);font-weight:900;margin-left:10px}.source-excerpt pre{white-space:pre-wrap;overflow:auto;max-height:34rem;background:rgba(0,0,0,.23);border:1px solid var(--line);border-radius:18px;padding:16px;color:#dcecff}.card code{word-break:break-word}
</style>"""
    return render_page_shell(
        title="SmactorIO Full Autonomy Control Plan",
        summary="Consolidated HTML surface for the reviewed SmactorIO full-autonomy spec, plan v2, Opus reviews, FSM placement, priority gate, GitHub-backed lifecycle, and operator dry run.",
        current_path=PAGE_PATH,
        body_html=build_body(),
        generated_at=utc_now(),
        pages=load_pages(ROOT),
        root=ROOT,
        extra_head=extra_head,
    )


def validate_html(text: str) -> None:
    required = [
        "SmactorIO Full Autonomy Control Plan",
        "Consolidated from reviewed spec, plan v2, and Opus reviews",
        "Top-level FSM placement",
        "SYNTHESIZE_DAILY_BRIEF",
        "RUN_SMACTORIO_IMPROVEMENT_LOOP",
        "RUN_DEVELOPMENT_LOOP",
        "PRIORITIZE_CANDIDATES",
        "impact + confidence + reversibility",
        "GitHub issue → branch → PR → revert",
        "bootstrap-github-backed-smactorio-source-001",
        "Operator dry run as Leon",
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
