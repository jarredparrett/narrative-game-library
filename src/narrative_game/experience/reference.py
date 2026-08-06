"""Deterministic, dependency-free reference rendering for experience projections."""

from __future__ import annotations

from html import escape
import json
from typing import Any

from narrative_game.contracts import canonical_json

from .model import ExperienceProjection


_CSS = """
:root{--carbon:#17212b;--blue:#174a7e;--signal:#f3b43f;--archive:#d8d8f2;--paper:#f6f7fb;--evidence:#f16445;--line:#b9c3ce;--display:Baskerville,'Iowan Old Style',Georgia,serif;--body:'Avenir Next',Avenir,'Segoe UI',sans-serif;--mono:'SFMono-Regular',Consolas,monospace}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--carbon);font-family:var(--body)}button{font:inherit;cursor:pointer}button:focus-visible,summary:focus-visible{outline:3px solid var(--signal);outline-offset:3px}.shell{min-height:100vh;display:grid;grid-template-columns:250px 1fr}.identity{padding:44px 28px;background:var(--blue);color:#fff}.identity.host{background:var(--carbon)}.identity.player,.identity.print{background:var(--archive);color:var(--carbon)}.identity h1{font:400 34px/1 var(--display);margin:18px 0}.eyebrow{font:700 10px/1.3 var(--mono);letter-spacing:.12em;text-transform:uppercase}.hash{font:10px/1.5 var(--mono);overflow-wrap:anywhere;opacity:.8}.main{padding:48px clamp(24px,6vw,86px) 100px;max-width:1280px}.main>header{border-bottom:1px solid var(--line);padding-bottom:24px}.main h2{font:400 clamp(38px,5vw,64px)/.98 var(--display);max-width:800px;margin:8px 0 10px}.subtitle{max-width:760px;color:#526171}.custody{display:flex;gap:8px;margin:28px 0}.custody span{flex:1;padding:12px;border-top:3px solid var(--line);font-size:12px}.custody span.active{border-color:var(--evidence);font-weight:700}.sections{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(260px,.7fr);gap:24px}.section{background:#fff;padding:20px;border-left:3px solid var(--archive);margin-bottom:16px;overflow:hidden}.section h3{font-size:13px;margin:0 0 14px}.tutorial-step{border-top:1px solid var(--line);padding:10px 0}.tutorial-step summary{font:400 20px/1.2 var(--display);cursor:pointer}.tutorial-step p{color:#526171}.tutorial-step dl{display:grid;grid-template-columns:90px 1fr;font-size:12px}.tutorial-step dt{font-weight:700}.tutorial-step dd{margin:0 0 8px}.material,.record,.phase{padding:12px 0;border-top:1px solid var(--line)}.material strong,.record strong,.phase strong{display:block;font:400 19px var(--display)}.record span,.phase span{color:#526171;font-size:11px}.material pre,.json{white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.5 var(--mono);color:#526171}.character-lead{font:400 27px/1.25 var(--display);margin:8px 0 20px}.brief-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.brief-card{padding:14px;background:var(--paper)}.brief-card strong{display:block;margin-bottom:6px}.actions{position:sticky;top:20px}.actions button{display:block;width:100%;padding:12px;margin:0 0 8px;border:0;text-align:left;background:var(--blue);color:#fff;font-weight:650}.actions button[data-boundary=session]{background:var(--carbon)}.intent-status{min-height:32px;color:#526171;font-size:12px}.host-layout{background:var(--carbon);color:#f8fafc}.host-layout .main{max-width:none}.host-layout .section{background:#1d2934;color:#fff;border-color:#43505d}.host-layout .section pre,.host-layout .subtitle,.host-layout .json,.host-layout .record span,.host-layout .phase span{color:#aab8c4}.host-layout .main>header{border-color:#43505d}.player-layout{background:#dce4e7}.player-layout .section{box-shadow:0 16px 36px rgba(23,33,43,.12)}.player-layout .section:nth-child(2){border-color:var(--evidence)}.badge{display:inline-block;padding:5px 7px;border:1px solid currentColor;font:700 9px var(--mono);text-transform:uppercase}.lineage{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}.lineage div{background:var(--paper);padding:12px}.lineage b{display:block;font:400 24px var(--display)}@media(max-width:800px){.shell,.sections{grid-template-columns:1fr}.identity{padding:28px}.main{padding:28px 18px 100px}.custody,.brief-grid{display:grid;grid-template-columns:1fr}.actions{position:static}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
"""

_STRUCTURED_CSS = """
.section h4{margin:22px 0 8px;font:700 10px/1.3 var(--mono);letter-spacing:.1em;text-transform:uppercase}.summary-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:18px}.summary-strip div{padding:12px;background:var(--paper)}.summary-strip b{display:block;font:400 24px/1.1 var(--display)}.summary-strip span{font-size:11px;color:#526171}.packing{margin:0;padding-left:24px}.packing li{padding:5px 0}.manifest{margin-top:18px;border-top:1px solid var(--line);padding-top:12px}.manifest summary{cursor:pointer;font-weight:700}.check{display:grid;grid-template-columns:14px 1fr;gap:8px;padding:9px 0;border-top:1px solid var(--line)}.check-mark{color:#167454;font-weight:900}.check span{font-size:12px;color:#526171}.host-layout .summary-strip div{background:#17212b}.host-layout .summary-strip span,.host-layout .check span{color:#aab8c4}.status-ready{display:inline-block;margin-bottom:14px;padding:6px 9px;background:#167454;color:#fff;font:700 10px var(--mono);letter-spacing:.08em;text-transform:uppercase}
"""


def _json(value: Any) -> str:
    return escape(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False))


def _tutorial(data: dict[str, Any]) -> str:
    result = []
    for index, step in enumerate(data["steps"]):
        result.append(
            f'<details class="tutorial-step" {"open" if index == 0 else ""}>'
            f'<summary>{index + 1}. {escape(step["title"])}</summary>'
            f'<p>{escape(step["summary"])}</p>'
            f'<dl><dt>Owns</dt><dd>{escape(", ".join(step["owns"]))}</dd>'
            f'<dt>Produces</dt><dd>{escape(", ".join(step["produces"]))}</dd>'
            f'<dt>In this game</dt><dd><code>{escape(", ".join(step["example_refs"]))}</code></dd></dl>'
            '</details>'
        )
    return "".join(result)


def _physical_plan(data: dict[str, Any]) -> str:
    containers = data["containers"]
    copies = data["copies"]
    profile = data["profile"]
    production = data["production"]
    body = (
        '<div class="summary-strip">'
        f'<div><b>{len(containers)}</b><span>containers</span></div>'
        f'<div><b>{len(copies)}</b><span>controlled copies</span></div>'
        f'<div><b>{escape(profile["page_size"])}</b><span>{escape(profile["sides"])} · {escape(profile["color_mode"])}</span></div>'
        "</div>"
        f'<p class="hash">production profile {escape(profile["profile_id"])} · {escape(profile["version"])}</p>'
        "<h4>Containers and custody</h4>"
    )
    body += "".join(
        f'<div class="record"><strong>{escape(item["label"])}</strong>'
        f'<span>{escape(item["audience"])} · {escape(item["delivery_condition"])}</span></div>'
        for item in containers
    )
    body += '<h4>Packing order</h4><ol class="packing">' + "".join(
        f"<li>{escape(item)}</li>" for item in production["packing_order"]
    ) + "</ol>"
    body += f'<details class="manifest"><summary>Copy manifest · {len(copies)} controlled copies</summary>'
    body += "".join(
        f'<div class="record"><strong>{escape(item["resource_id"])}</strong>'
        f'<span>{escape(item["container_id"])} · {escape(item["audience"])} · {escape(item["rendition_path"])}</span></div>'
        for item in copies
    )
    return body + "</details>"


def _preflight(data: dict[str, Any]) -> str:
    status = "Preflight ready" if data["ok"] else "Preflight failed"
    body = f'<span class="status-ready">{escape(status)}</span>'
    body += (
        '<div class="summary-strip">'
        f'<div><b>{len(data["files"])}</b><span>verified files</span></div>'
        f'<div><b>{len(data["executed_checks"])}</b><span>executed checks</span></div>'
        f'<div><b>{len(data["failures"])}</b><span>failures</span></div>'
        "</div><h4>Executed checks</h4>"
    )
    body += "".join(
        f'<div class="check"><b class="check-mark">✓</b><div><strong>{escape(key.replace("_", " "))}</strong><br><span>{escape(description)}</span></div></div>'
        for key, description in sorted(data["executed_checks"].items())
    )
    if data["unexecuted_checks"]:
        body += '<h4>Requires physical evidence</h4>' + "".join(
            f'<div class="check"><b>—</b><div><strong>{escape(key.replace("_", " "))}</strong><br><span>{escape(description)}</span></div></div>'
            for key, description in sorted(data["unexecuted_checks"].items())
        )
    return body


def _file_index(data: list[dict[str, Any]]) -> str:
    return "".join(
        f'<div class="record"><strong>{escape(item["path"])}</strong>'
        f'<span>{escape(item["media_type"])} · {item["bytes"]} bytes · {escape(item["audience"])}</span>'
        f'<span class="hash">{escape(item["content_hash"])}</span></div>'
        for item in data
    )


def _section(value: dict[str, Any]) -> str:
    kind = value["kind"]
    data = value["data"]
    if kind == "tutorial":
        body = _tutorial(data)
    elif kind == "character":
        character = data["character"]
        body = f'<p class="character-lead">{escape(data["resolution_prompt"])}</p><div class="brief-grid">'
        body += "".join(
            f'<div class="brief-card"><strong>Objective</strong>{escape(item["description"])}</div>'
            for item in character["objectives"]
        )
        body += "".join(
            f'<div class="brief-card"><strong>Belief · {escape(item["stance"])}</strong>{escape(item["expression"])}</div>'
            for item in character["beliefs"]
        ) + '</div>'
    elif kind == "authorized-materials":
        body = "".join(
            f'<article class="material"><strong>{escape(item["resource_id"])}</strong>'
            f'<div class="hash">{escape(item["content_hash"])}</div>'
            f'<pre>{escape(item.get("content") or "Binary material")}</pre></article>'
            for item in data
        )
    elif kind == "phase-rail":
        phases = data["phases"] if isinstance(data, dict) else data
        current = data.get("current") if isinstance(data, dict) else phases[0].get("phase_id")
        body = "".join(
            f'<div class="phase"><strong>{escape(item.get("label") or item.get("phase_id") or item["id"])}</strong><span>{"Now" if (item.get("id") or item.get("phase_id")) == current else escape(item.get("dramatic_question", "Later"))}</span></div>'
            for item in phases
        )
    elif kind == "event-stream":
        body = "".join(
            f'<div class="record"><strong>{item["sequence"]:02d} · {escape(item["event_type"].replace("-", " "))}</strong><span>{escape(item["represented_phase_id"])}</span></div>'
            for item in data
        )
    elif kind == "queue":
        queued = [
            ("Hint", item.get("request", "")) for item in data.get("hints", [])
        ] + [("Evidence", item.get("resource_id", "")) for item in data.get("evidence", [])]
        body = "".join(f'<div class="record"><strong>{escape(label)}</strong><span>{escape(text)}</span></div>' for label, text in queued) or '<p>No open requests.</p>'
    elif kind == "material-index":
        body = "".join(
            f'<div class="record"><strong>{escape(item["resource_id"])}</strong><span>{escape(item["media_type"])} · {escape(item["content_hash"])}</span></div>'
            for item in data
        )
    elif kind == "component-summary":
        body = '<div class="lineage">' + "".join(
            f'<div><b>{len(data[key])}</b><span>{escape(key.replace("_", " "))}</span></div>'
            for key in ("seats", "characters", "evidence", "proof_paths", "materials")
        ) + '</div>'
    elif kind == "identity":
        body = "".join(f'<div class="record"><strong>{escape(key.replace("_", " "))}</strong><span class="hash">{escape(str(item))}</span></div>' for key, item in data.items())
    elif kind == "lineage" and isinstance(data, dict):
        body = '<div class="lineage">' + "".join(
            f'<div><b>{escape(str(item))}</b><span>{escape(str(key).replace("_", " "))}</span></div>'
            for key, item in sorted(data.items())
        ) + '</div>'
    elif kind == "physical-plan":
        body = _physical_plan(data)
    elif kind == "preflight":
        body = _preflight(data)
    elif kind == "file-index":
        body = _file_index(data)
    else:
        body = f'<pre class="json">{_json(data)}</pre>'
    return f'<section class="section" data-section="{escape(value["section_id"])}"><h3>{escape(value["label"])}</h3>{body}</section>'


def render_reference_html(projection: ExperienceProjection) -> bytes:
    """Render one standalone role-scoped page with no external dependencies."""
    mapping = projection.to_mapping()
    body_class = {
        "host": "host-layout",
        "player": "player-layout",
        "print": "player-layout",
    }.get(projection.surface, "")
    primary = "".join(_section(item.to_mapping()) for item in projection.sections)
    actions = "".join(
        f'<button data-action="{escape(item.action_id)}" data-command="{escape(item.command)}" data-boundary="{escape(item.boundary)}" {"" if item.enabled else "disabled"}>{escape(item.label)}</button>'
        for item in projection.actions
    )
    embedded = canonical_json(mapping).decode("utf-8").replace("<", "\\u003c")
    session_line = projection.session_id or "No live Session"
    revision_line = f"revision {projection.revision}" if projection.revision is not None else "immutable"
    active_stage = {"maker": "Author", "host": "Play", "player": "Play", "print": "Deliver"}.get(projection.surface, "Release")
    custody = "".join(f'<span class="{"active" if item == active_stage else ""}">{item}</span>' for item in ("Author", "Release", "Deliver", "Play", "Measure"))
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(projection.title)} — {escape(projection.surface)}</title><style>{_CSS}{_STRUCTURED_CSS}</style></head>
<body class="{body_class}"><div class="shell"><aside class="identity {escape(projection.surface)}"><div class="eyebrow">{escape(projection.surface)} experience</div><h1>{escape(projection.title)}</h1><span class="badge">{escape(projection.authority_scope)}</span><p class="hash">release {escape(projection.release_id)}<br>{escape(session_line)}<br>{escape(revision_line)}</p></aside>
<main class="main"><header><div class="eyebrow">Authorized projection · schema 0.11</div><h2>{escape(projection.subtitle)}</h2><p class="subtitle">This surface renders exact library state. Controls emit typed intents; only the Experiment or Session authority may accept them.</p></header><div class="custody">{custody}</div><div class="sections"><div>{primary}</div><aside class="actions"><div class="eyebrow">Available actions</div>{actions or '<p>No actions in this state.</p>'}<p class="intent-status" aria-live="polite"></p><p class="hash">projection {escape(projection.projection_id)}</p></aside></div></main></div>
<script id="experience-projection" type="application/json">{embedded}</script><script>document.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>{{const detail={{action_id:button.dataset.action,command:button.dataset.command,boundary:button.dataset.boundary,projection_id:{json.dumps(projection.projection_id)}}};window.dispatchEvent(new CustomEvent('narrative-game-intent',{{detail}}));document.querySelector('.intent-status').textContent=`Intent emitted: ${{detail.action_id}}. The ${{detail.boundary}} authority must decide it.`;}}));</script></body></html>"""
    return html.encode("utf-8")
