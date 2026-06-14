#!/usr/bin/env python3
"""Manifest-backed HTML shell helpers for Signal Hub generated pages.

This module is intentionally small and boring: generator scripts own trusted page
body HTML, while this helper owns page registration, global navigation, manifest
metadata, and shared CSS used to prevent orphan generated pages.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import posixpath
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "pages.json"
SHELL_VERSION = "v1"
SHELL_GLOBAL_MARKER = "global"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_pages(root: Path | str = ROOT, manifest_name: str = MANIFEST_NAME) -> list[dict[str, Any]]:
    """Load and normalize the canonical page manifest.

    The canonical shape is {"pages": [...]}. Older tests/fixtures may provide a
    bare list; accept that shape to keep the helper easy to exercise in temp dirs.
    """
    root_path = Path(root)
    manifest_path = root_path / manifest_name
    if not manifest_path.exists():
        return [
            {
                "path": "index.html",
                "title": "Leon Signal Hub",
                "summary": "LAN-only Signal Hub dashboard.",
                "type": "dashboard",
                "status": "current",
                "nav_visible": True,
                "source_script": "scripts/build_dashboard.py",
                "parent": "",
                "tags": ["signal-hub", "dashboard"],
                "generated_from": ["pages.json"],
                "owner": "Signal Hub",
            },
            {
                "path": "ai_tech_signal_brief.html",
                "title": "AI + Tech Signal Daily Brief",
                "summary": "FSM-derived daily signal deltas, queued actions, parked review items, and evidence boundaries.",
                "type": "brief",
                "status": "current",
                "nav_visible": True,
                "source_script": "scripts/synthesize_daily_brief.py",
                "parent": "index.html",
                "tags": ["signal-hub", "daily-brief", "fsm"],
                "generated_from": ["state/source_state.json", "state/signal_loop.db", "goals.json", "pages.json"],
                "owner": "Signal Hub",
            },
        ]
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        pages = raw.get("pages") or []
    elif isinstance(raw, list):
        pages = raw
    else:
        raise ValueError(f"{manifest_path} must contain a page list or a {{'pages': [...]}} object")
    if not isinstance(pages, list):
        raise ValueError(f"{manifest_path} pages field must be a list")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("each page manifest entry must be an object")
        if not page.get("path") or not page.get("title"):
            raise ValueError("each page manifest entry needs path and title")
        entry = {
            "summary": "",
            "type": "page",
            "status": "current",
            "nav_visible": True,
            "source_script": "unknown",
            "parent": "index.html",
            "tags": [],
            "generated_from": [],
            "owner": "Signal Hub",
            **page,
        }
        href = _page_href(entry["path"])
        if href in seen:
            raise ValueError(f"duplicate page manifest path: {href}")
        seen.add(href)
        entry["path"] = href
        normalized.append(entry)
    return normalized


def _page_href(path: Any) -> str:
    value = str(path or "index.html").strip()
    pathish = value.replace("\\", "/")
    lowered = pathish.lower()
    first_segment = pathish.split("/", 1)[0]
    if (
        "://" in pathish
        or pathish.startswith("//")
        or pathish.startswith("/")
        or ":" in first_segment
        or lowered.startswith("javascript:")
        or lowered.startswith("data:")
    ):
        raise ValueError(f"manifest page path must be a relative internal path: {value!r}")
    normalized = posixpath.normpath(pathish)
    if normalized == ".":
        return "index.html"
    if normalized.startswith("../") or normalized == ".." or normalized.startswith("/"):
        raise ValueError(f"manifest page path must stay within public/: {value!r}")
    return normalized


def _relative_href(target_path: Any, current_path: Any) -> str:
    target = _page_href(target_path)
    current = _page_href(current_path)
    current_dir = posixpath.dirname(current) or "."
    rel = posixpath.relpath(target, start=current_dir).replace("\\", "/")
    if rel == ".":
        rel = posixpath.basename(target)
    return rel


def find_page(current_path: str, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    current = current_path.lstrip("/") or "index.html"
    for page in pages:
        if str(page.get("path", "")).lstrip("/") == current:
            return page
    return None


def _status_rank(page: dict[str, Any]) -> tuple[int, str]:
    order = {"current": 0, "experimental": 1, "legacy": 2, "archived": 3, "live-only": 4}
    return (order.get(str(page.get("status", "current")), 9), str(page.get("title", "")))


def _iter_nav_pages(pages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    visible = [page for page in pages if page.get("nav_visible", True)]
    return sorted(visible, key=_status_rank)


def render_global_nav(
    current_path: str,
    pages: list[dict[str, Any]],
    section_links: list[tuple[str, str]] | None = None,
) -> str:
    """Render manifest-backed global nav plus optional page-local anchors."""
    links: list[str] = []
    current = current_path.lstrip("/") or "index.html"
    for page in _iter_nav_pages(pages):
        status = str(page.get("status", "current"))
        if status in {"archived", "live-only"}:
            continue
        target = _page_href(page.get("path"))
        href = _relative_href(target, current)
        label = page.get("title") or target
        current_attrs = ' aria-current="page" class="current"' if target == current else ""
        links.append(f'<a href="{esc(href)}"{current_attrs}>{esc(label)}</a>')
    for fragment, label in section_links or []:
        clean_fragment = str(fragment).strip().lstrip("#")
        if not clean_fragment:
            continue
        links.append(f'<a href="#{esc(clean_fragment)}">{esc(label)}</a>')
    if not links:
        return ""
    return (
        '<nav class="shell-nav" data-signal-hub-shell="global" aria-label="Signal Hub pages">'
        + "".join(links)
        + "</nav>"
    )


def render_page_meta(
    current_path: str,
    pages: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
    source_note: str = "",
) -> str:
    page = find_page(current_path, pages) or {}
    timestamp = generated_at or utc_now()
    tags = " ".join(f'<span class="tag">{esc(tag)}</span>' for tag in (page.get("tags") or []))
    generated_from = page.get("generated_from") or []
    generated_list = "".join(f"<li>{esc(item)}</li>" for item in generated_from) or "<li>not specified</li>"
    source_script = page.get("source_script") or "unknown"
    return f"""
<aside class="card page-meta" data-page-meta="manifest" aria-label="Page manifest metadata">
  <div class="eyebrow">LAN-only/private Signal Hub surface · {esc(page.get('type', 'page'))} · {esc(page.get('status', 'current'))}</div>
  <h2>{esc(page.get('title') or current_path)}</h2>
  <p>{esc(page.get('summary') or '')}</p>
  <div class="shell-meta">
    <span class="badge">Generated {esc(timestamp)}</span>
    <span class="badge">Source {esc(source_script)}</span>
    <span class="badge">Owner {esc(page.get('owner', 'Signal Hub'))}</span>
  </div>
  <p class="muted">{esc(source_note)}</p>
  <details><summary>Generated from</summary><ul>{generated_list}</ul></details>
  <div class="tags">{tags}</div>
</aside>
""".strip()


def render_page_index(pages: list[dict[str, Any]], *, current_path: str = "index.html") -> str:
    cards: list[str] = []
    for page in _iter_nav_pages(pages):
        target = _page_href(page.get("path"))
        href = _relative_href(target, current_path)
        tags = " ".join(f'<span class="tag">{esc(tag)}</span>' for tag in (page.get("tags") or []))
        cards.append(
            f"""
            <article class="card page-card">
              <div class="eyebrow">{esc(page.get('type', 'page'))} · {esc(page.get('status', 'current'))}</div>
              <h3><a href="{esc(href)}">{esc(page.get('title'))}</a></h3>
              <p>{esc(page.get('summary'))}</p>
              <p class="muted">Source: <code>{esc(page.get('source_script', 'unknown'))}</code></p>
              <div class="tags">{tags}</div>
            </article>
            """
        )
    if not cards:
        cards.append('<article class="card"><p class="muted">No manifest-visible pages are registered.</p></article>')
    return (
        '<section id="pages" data-page-index="manifest">'
        '<div class="eyebrow">Manifest index</div><h2>Pages / control surfaces</h2>'
        '<p class="muted">This index is generated from <code>pages.json</code>; add future generated pages there before publishing them.</p>'
        '<div class="grid two page-index">'
        + "".join(cards)
        + "</div></section>"
    )


def render_shared_styles() -> str:
    return """
.shell-nav{position:sticky;top:0;z-index:20;margin:0 auto 28px;padding:12px;border-radius:999px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;background:rgba(2,6,23,.88);border:1px solid var(--line,rgba(148,163,184,.24));backdrop-filter:blur(14px)}
.shell-nav a{padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.07);color:var(--text,#e5f4ff);text-decoration:none}
.shell-nav a.current{outline:1px solid var(--cyan,#69e6ff);color:var(--cyan,#69e6ff)}
.page-meta{margin:0 auto 28px;padding:22px}
.page-card code,.page-meta code{white-space:normal}
.shell-meta{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.badge,.tag,.pill{display:inline-flex;align-items:center;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);border-radius:999px;padding:5px 9px;color:#dcecff;font-size:.84rem}
.meta-row,.metrics,.source-health{display:flex;gap:10px;flex-wrap:wrap;align-items:stretch;margin:12px 0}
.metric{display:inline-flex;flex-direction:column;gap:2px;min-width:92px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.07);border-radius:18px;padding:9px 12px;color:var(--muted,#a8bbcf)}
.metric-value{font-weight:900;font-size:1.05rem;color:var(--text,#eef7ff);line-height:1.1}
.metric-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted,#a8bbcf)}
.confidence{display:inline-flex;align-items:center;border:1px solid rgba(255,208,113,.28);background:rgba(255,208,113,.09);border-radius:999px;padding:5px 9px;color:var(--amber,#ffd071);font-size:.84rem}
.signal-summary{color:var(--text,#eef7ff)}
.daily-brief-hero{margin-bottom:16px}
.signal-card,.signal-contract{position:relative}
.rank{position:absolute;right:18px;top:14px;color:var(--amber,#ffd071);font-weight:900}
.tags{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
.lan-warning{margin-top:18px;padding:16px;border-radius:18px;border:1px solid rgba(105,230,255,.32);background:rgba(105,230,255,.08);color:var(--text,#e5f4ff)}
.back-link{display:inline-flex;margin-bottom:14px;font-weight:800}
.page-index{align-items:stretch}
.footer{padding:36px 0 64px;color:var(--muted,#9fb2c7);font-size:.92rem}
@media(max-width:900px){.shell-nav{position:static;border-radius:22px;justify-content:flex-start}}
""".strip()


def render_page_shell(
    *,
    title: str,
    summary: str,
    current_path: str,
    body_html: str,
    generated_at: str | None = None,
    pages: list[dict[str, Any]] | None = None,
    root: Path | str = ROOT,
    extra_head: str = "",
) -> str:
    """Wrap trusted local-generator body HTML in the Signal Hub page shell.

    `body_html` may contain HTML because it is produced by trusted local renderer
    code, not directly by untrusted source items or agent text.
    """
    loaded_pages = pages if pages is not None else load_pages(root)
    current = find_page(current_path, loaded_pages) or {}
    display_title = str(current.get("title") or title or "Signal Hub Page")
    display_summary = str(current.get("summary") or summary or "")
    timestamp = generated_at or utc_now()
    back_link = ""
    if current_path.lstrip("/") != "index.html":
        parent = _page_href(current.get("parent") or "index.html")
        back_link = f'<a class="back-link" href="{esc(_relative_href(parent, current_path))}">← Back to Signal Hub dashboard</a>'
    nav = render_global_nav(current_path, loaded_pages)
    meta = render_page_meta(
        current_path,
        loaded_pages,
        generated_at=timestamp,
        source_note=f"Rendered by scripts/page_shell.py for {current_path} from the canonical manifest.",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(display_title)}</title>
<style>
:root {{ color-scheme: dark; --bg:#071017; --panel:rgba(255,255,255,.075); --panel2:rgba(255,255,255,.11); --line:rgba(255,255,255,.16); --text:#eef7ff; --muted:#a8bbcf; --cyan:#69e6ff; --green:#8ef0c1; --amber:#ffd071; --rose:#ff9ab1; --violet:#c7a6ff; }}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:radial-gradient(circle at 12% -10%,rgba(105,230,255,.23),transparent 34rem),radial-gradient(circle at 88% 4%,rgba(199,166,255,.20),transparent 34rem),linear-gradient(160deg,#061019,#101827 58%,#0c121b);color:var(--text);line-height:1.55}} a{{color:var(--cyan);text-decoration:none}} a:hover{{text-decoration:underline}} main{{width:min(1180px,calc(100vw - 32px));margin:0 auto}} .shell-hero{{padding:52px 0 22px}} .panel,.card{{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:26px;box-shadow:0 24px 70px rgba(0,0,0,.35);backdrop-filter:blur(18px)}} .hero-panel,.card{{padding:24px}} .kicker,.eyebrow{{text-transform:uppercase;letter-spacing:.15em;font-weight:800;font-size:.76rem;color:var(--green)}} h1{{font-size:clamp(2.4rem,7vw,5.2rem);line-height:.94;margin:12px 0;letter-spacing:-.055em}} h2{{font-size:clamp(1.9rem,3.4vw,2.7rem);line-height:1.05;margin:10px 0 14px;letter-spacing:-.035em}} h3{{margin:0 0 10px;font-size:1.22rem}} p,.muted,td,li{{color:var(--muted)}} section{{padding:34px 0}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}} table{{width:100%;border-collapse:collapse}} th,td{{padding:10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} code{{color:var(--amber)}}
{render_shared_styles()}
</style>
{extra_head}
</head>
<body data-signal-hub-shell="{SHELL_VERSION}">
<main>
<header class="shell-hero" id="top">
  <div class="panel hero-panel">
    {back_link}
    <div class="kicker">LAN-only Signal Hub</div>
    <h1>{esc(display_title)}</h1>
    <p class="muted">{esc(display_summary)}</p>
    <div class="shell-meta"><span class="badge">Generated {esc(timestamp)}</span><span class="badge">Shared shell</span><span class="badge">No raw agent HTML</span></div>
    <div class="lan-warning"><strong>Private boundary:</strong> this LAN-only/private Signal Hub surface must stay off the public internet unless separately reviewed.</div>
  </div>
</header>
{nav}
{meta}
{body_html}
<footer class="footer">Rendered by <code>scripts/page_shell.py</code> from <code>pages.json</code>.</footer>
</main>
</body>
</html>
"""
