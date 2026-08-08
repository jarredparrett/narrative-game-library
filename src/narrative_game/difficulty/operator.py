"""Read-only, checkpoint-rooted operator projections and release capsules."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json
from narrative_game.workspace.evidence import (
    deterministic_zip,
    capsule_members,
    verify_claim_capsule_bytes,
)


PROJECTION_STATES = ("current-complete", "current-incomplete", "stale", "invalid")
REPRODUCIBILITY_STATES = (
    "complete",
    "degraded",
    "externally-dependent",
    "unsupported",
    "corrupt",
)
SEALED_HANDLE_FIELDS = (
    "handle_id",
    "declared_cost_microunits",
    "reserved_budget_category",
    "eligibility_state",
    "consumption_state",
    "promotion_gate",
    "aggregate_decision_receipt_ref",
)
FORBIDDEN_OPERATOR_COMMANDS = (
    "approve",
    "reject",
    "run",
    "retry",
    "rebuild",
    "resume",
    "cancel",
    "promote",
    "select",
    "transition",
    "reallocate",
    "edit",
    "delete",
)


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _is_ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _find_forbidden_keys(value: Any, *, path: str = "") -> tuple[str, ...]:
    findings = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).casefold() in FORBIDDEN_OPERATOR_COMMANDS:
                findings.append(child_path)
            findings.extend(_find_forbidden_keys(child, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden_keys(child, path=f"{path}[{index}]"))
    return tuple(findings)


@dataclass(frozen=True)
class OperatorProjectionSource:
    """Verified inputs from which one disposable monitor snapshot is derived."""

    workspace_id: str
    checkpoint_ref: str
    current_checkpoint_ref: str
    derivation_contract_ref: str
    authorized_journal_heads: Mapping[str, Mapping[str, Any]]
    verification_receipt_ref: str
    claim_manifest_refs: tuple[str, ...]
    scheduling_receipt_ref: str
    reproducibility_status: str
    conclusions: Mapping[str, Mapping[str, Any]]
    overview: Mapping[str, Any]
    coverage: tuple[Mapping[str, Any], ...]
    incidents: tuple[Mapping[str, Any], ...]
    sealed_handles: tuple[Mapping[str, Any], ...]
    completeness_debt: tuple[str, ...] = ()
    verification_failures: tuple[str, ...] = ()
    last_verifiable_checkpoint_ref: str | None = None
    schema_version: str = "operator-projection-source.1"

    def __post_init__(self) -> None:
        if not self.workspace_id.strip():
            raise ValueError("operator projection requires a Workspace identity")
        for label, value in (
            ("checkpoint", self.checkpoint_ref),
            ("current checkpoint", self.current_checkpoint_ref),
            ("derivation contract", self.derivation_contract_ref),
            ("verification receipt", self.verification_receipt_ref),
            ("Scheduling Receipt", self.scheduling_receipt_ref),
        ):
            if not _is_ref(value):
                raise ValueError(f"operator projection {label} must be content-addressed")
        if not self.claim_manifest_refs or any(
            not _is_ref(value) for value in self.claim_manifest_refs
        ):
            raise ValueError("operator projection requires content-addressed Claim Manifests")
        if tuple(sorted(set(self.claim_manifest_refs))) != self.claim_manifest_refs:
            raise ValueError("Claim Manifest references must be canonical")
        if self.reproducibility_status not in REPRODUCIBILITY_STATES:
            raise ValueError("unsupported operator reproducibility status")
        if self.last_verifiable_checkpoint_ref is not None and not _is_ref(
            self.last_verifiable_checkpoint_ref
        ):
            raise ValueError("last verifiable Checkpoint must be content-addressed")
        object.__setattr__(self, "authorized_journal_heads", _copy(self.authorized_journal_heads))
        object.__setattr__(self, "conclusions", _copy(self.conclusions))
        object.__setattr__(self, "overview", _copy(self.overview))
        object.__setattr__(self, "coverage", tuple(_copy(item) for item in self.coverage))
        object.__setattr__(self, "incidents", tuple(_copy(item) for item in self.incidents))
        object.__setattr__(self, "sealed_handles", tuple(_copy(item) for item in self.sealed_handles))


@dataclass(frozen=True)
class OperatorEvidenceProjection:
    """Canonical monitor data; inspection is its only authority."""

    material: Mapping[str, Any]
    schema_version: str = "operator-evidence-projection.1"

    def __post_init__(self) -> None:
        copied = _copy(self.material)
        state = copied.get("trust", {}).get("state")
        if state not in PROJECTION_STATES:
            raise ValueError("operator projection has an unsupported trust state")
        forbidden = _find_forbidden_keys(copied)
        if forbidden:
            raise ValueError(f"operator projection contains mutation authority: {forbidden[0]}")
        object.__setattr__(self, "material", copied)

    @property
    def projection_ref(self) -> str:
        return digest_json({"schema_version": self.schema_version, "material": self.material})

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "projection_ref": self.projection_ref,
            "material": _copy(self.material),
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_mapping())


def build_operator_projection(source: OperatorProjectionSource) -> OperatorEvidenceProjection:
    """Validate authority links and derive a fail-closed read-only snapshot."""
    allowed_authorities = {*source.claim_manifest_refs, source.scheduling_receipt_ref}
    conclusions = []
    for conclusion_id, value in sorted(source.conclusions.items()):
        authority_ref = value.get("authority_ref")
        if authority_ref not in allowed_authorities:
            raise ValueError(
                f"operator conclusion {conclusion_id} does not resolve to a Claim Manifest or Scheduling Receipt"
            )
        conclusions.append(
            {
                "conclusion_id": conclusion_id,
                "statement": str(value.get("statement", "")),
                "status": str(value.get("status", "")),
                "authority_ref": authority_ref,
            }
        )

    handles = []
    for handle in source.sealed_handles:
        extra = set(handle) - set(SEALED_HANDLE_FIELDS)
        if extra:
            raise ValueError(f"sealed handle exposes forbidden field: {sorted(extra)[0]}")
        handles.append({key: handle.get(key) for key in SEALED_HANDLE_FIELDS})

    invalid = bool(source.verification_failures) or source.reproducibility_status == "corrupt"
    stale = source.checkpoint_ref != source.current_checkpoint_ref
    incomplete = bool(source.completeness_debt)
    if invalid:
        state = "invalid"
    elif stale:
        state = "stale"
    elif incomplete:
        state = "current-incomplete"
    else:
        state = "current-complete"

    overview = _copy(source.overview)
    if incomplete:
        overview["standing_status"] = "indeterminate"
        overview["selection_status"] = "indeterminate"

    suppressed = []
    views: dict[str, Any]
    visible_conclusions = conclusions
    if invalid:
        suppressed = [item["conclusion_id"] for item in conclusions]
        visible_conclusions = []
        views = {"overview": {}, "coverage": [], "incidents": []}
    else:
        views = {
            "overview": overview,
            "coverage": list(source.coverage),
            "incidents": list(source.incidents),
        }

    material = {
        "identity": {
            "workspace_id": source.workspace_id,
            "checkpoint_ref": source.checkpoint_ref,
            "current_checkpoint_ref": source.current_checkpoint_ref,
            "derivation_contract_ref": source.derivation_contract_ref,
            "authorized_journal_heads": source.authorized_journal_heads,
            "verification_receipt_ref": source.verification_receipt_ref,
            "claim_manifest_refs": list(source.claim_manifest_refs),
            "scheduling_receipt_ref": source.scheduling_receipt_ref,
        },
        "trust": {
            "state": state,
            "freshness": "invalid" if invalid else ("stale" if stale else "current"),
            "reproducibility_status": source.reproducibility_status,
            "read_only": True,
            "authority": "inspection-only",
            "completeness_debt": list(source.completeness_debt),
            "verification_failures": list(source.verification_failures),
            "last_verifiable_checkpoint_ref": source.last_verifiable_checkpoint_ref,
        },
        "conclusions": visible_conclusions,
        "suppressed_conclusion_ids": suppressed,
        "views": views,
        "sealed_handles": handles,
        "affordances": ("navigate", "filter-projected", "inspect", "expand-trace", "copy-reference"),
    }
    return OperatorEvidenceProjection(material)


def reference_operator_projection(state: str = "current") -> OperatorEvidenceProjection:
    """Build the portable worked monitor fixture used by docs and qualification."""
    if state not in {"current", "incomplete", "stale", "corrupt"}:
        raise ValueError("unknown reference operator state")

    def ref(character: str) -> str:
        return "sha256:" + character * 64

    checkpoint = ref("1")
    current = ref("2") if state == "stale" else checkpoint
    manifest = ref("3")
    scheduling = ref("4")
    source = OperatorProjectionSource(
        workspace_id="difficulty:facilitated-investigation",
        checkpoint_ref=checkpoint,
        current_checkpoint_ref=current,
        derivation_contract_ref=ref("5"),
        authorized_journal_heads={
            name: {"sequence": index, "head": ref(hex(index)[2:])}
            for index, name in enumerate(
                ("access", "analysis", "climb", "lineage", "operational", "qualification"),
                10,
            )
        },
        verification_receipt_ref=ref("6"),
        claim_manifest_refs=(manifest,),
        scheduling_receipt_ref=scheduling,
        reproducibility_status="corrupt" if state == "corrupt" else "complete",
        conclusions={
            "current-work": {
                "statement": "Counterfactual handoff probe is the current complete work package.",
                "status": "scheduled",
                "authority_ref": scheduling,
            },
            "coverage-debt": {
                "statement": "One invalid restricted-cell Episode requires its frozen replacement.",
                "status": "open" if state == "incomplete" else "resolved",
                "authority_ref": manifest,
            },
            "target-band": {
                "statement": "Coordination quality remains below the frozen target interval.",
                "status": "indeterminate" if state == "incomplete" else "supported",
                "authority_ref": manifest,
            },
        },
        overview={
            "standing_status": "supported",
            "selection_status": "diagnostic-only",
            "diagnostic_stop_state": "scheduled",
            "evidence_spine": [
                {
                    "phase": "01 · Episodes",
                    "title": "Matched standing panel",
                    "status": "verified",
                    "completion": "23/24 valid; 1 replaced",
                    "receipt_ref": manifest,
                },
                {
                    "phase": "02 · Incident",
                    "title": "Uncompleted handoff",
                    "status": "corroborated",
                    "completion": "5/5 truth-blind sweeps",
                    "receipt_ref": manifest,
                },
                {
                    "phase": "03 · Probe",
                    "title": "Counterfactual transfer condition",
                    "status": "current",
                    "completion": "2/3 contrasts verified",
                    "receipt_ref": scheduling,
                },
            ],
            "budgets": {
                "standing": {"reserved": 2400, "spent": 2400, "remaining": 0},
                "counterfactuals": {"reserved": 900, "spent": 600, "remaining": 300},
                "sealed": {"reserved": 1200, "spent": 0, "remaining": 1200},
            },
        },
        coverage=(
            {
                "cell": "ordinary / seed-11",
                "required": 6,
                "valid": 6,
                "invalid": 0,
                "missing": 0,
                "replacement": 0,
                "uncertainty": "Wilson 95% · [0.41, 0.93]",
            },
            {
                "cell": "handoff-pressure / seed-17",
                "required": 6,
                "valid": 5,
                "invalid": 1,
                "missing": 0,
                "replacement": 1,
                "uncertainty": "insufficient until replacement",
            },
        ),
        incidents=(
            {
                "title": "Complementary proof was never transferred",
                "status": "counterfactual-active",
                "disagreement": "Attribution A favors role obligation; B favors tool visibility.",
                "next_probe": "change transfer affordance while freezing truth and oracle",
                "lineage_ref": manifest,
            },
        ),
        sealed_handles=(
            {
                "handle_id": "sealed:promoted-regression:v1",
                "declared_cost_microunits": 1200,
                "reserved_budget_category": "sealed",
                "eligibility_state": "eligible",
                "consumption_state": "unused",
                "promotion_gate": "no-regression",
                "aggregate_decision_receipt_ref": None,
            },
        ),
        completeness_debt=("restricted / seed-17 replacement is not verified",)
        if state == "incomplete"
        else (),
        verification_failures=("analysis Journal head hash is invalid",)
        if state == "corrupt"
        else (),
        last_verifiable_checkpoint_ref=ref("0") if state == "corrupt" else checkpoint,
    )
    return build_operator_projection(source)


def _authority_link(value: str) -> str:
    return f'<a class="ref" href="#ref-{escape(value[7:19])}">{escape(value[:19])}…</a>'


def render_operator_html(projection: OperatorEvidenceProjection) -> bytes:
    """Render accessible static HTML with no mutation or transition controls."""
    value = projection.to_mapping()
    material = value["material"]
    trust = material["trust"]
    identity = material["identity"]
    state = trust["state"]
    overview = material["views"]["overview"]
    coverage = material["views"]["coverage"]
    incidents = material["views"]["incidents"]
    conclusions = material["conclusions"]

    conclusion_html = "".join(
        f'<li><span>{escape(item["statement"])}</span><strong>{escape(item["status"])}</strong>'
        f'{_authority_link(item["authority_ref"])}</li>'
        for item in conclusions
    ) or '<li class="empty">Derived conclusions are suppressed in this trust state.</li>'
    debt = "".join(f"<li>{escape(item)}</li>" for item in trust["completeness_debt"])
    failures = "".join(f"<li>{escape(item)}</li>" for item in trust["verification_failures"])
    packages = "".join(
        f'<li class="spine-node"><span class="phase">{escape(str(item.get("phase", "evidence")))}</span>'
        f'<h3>{escape(str(item.get("title", "Evidence package")))}</h3>'
        f'<p>{escape(str(item.get("status", "unknown")))} · {escape(str(item.get("completion", "")))}</p>'
        f'<code>{escape(str(item.get("receipt_ref", "unreceipted")))}</code></li>'
        for item in overview.get("evidence_spine", [])
    )
    coverage_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(cell.get(key, '—')))}</td>"
            for key in ("cell", "required", "valid", "invalid", "missing", "replacement", "uncertainty")
        )
        + "</tr>"
        for cell in coverage
    )
    incident_html = "".join(
        f'<article class="incident"><p class="kicker">{escape(str(item.get("status", "active")))}</p>'
        f'<h3>{escape(str(item.get("title", "Incident")))}</h3>'
        f'<p>{escape(str(item.get("disagreement", "No recorded disagreement")))}</p>'
        f'<dl><dt>Next probe</dt><dd>{escape(str(item.get("next_probe", "none")))}</dd>'
        f'<dt>Lineage</dt><dd><code>{escape(str(item.get("lineage_ref", "unavailable")))}</code></dd></dl></article>'
        for item in incidents
    )
    sealed_html = "".join(
        f'<li><code>{escape(str(item["handle_id"]))}</code><span>{escape(str(item["eligibility_state"]))} / '
        f'{escape(str(item["consumption_state"]))}</span></li>'
        for item in material["sealed_handles"]
    )
    embedded = canonical_json(value).decode("utf-8").replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence monitor · {escape(state)}</title>
<style>
:root{{--ink:#171a1f;--slate:#52606d;--line:#cbd5df;--paper:#f7f9fb;--panel:#fff;--blue:#225ea8;--amber:#9a6700;--red:#9b2c2c;--focus:#005fcc;--mono:ui-monospace,SFMono-Regular,Menlo,monospace;--sans:Aptos,"Segoe UI",system-ui,sans-serif;--display:"Arial Narrow","Aptos Narrow",sans-serif}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 var(--sans)}}a{{color:var(--blue)}}a:focus-visible{{outline:3px solid var(--focus);outline-offset:4px}}code,.ref{{font:12px/1.4 var(--mono);overflow-wrap:anywhere}}.trust{{position:sticky;z-index:5;top:0;display:grid;grid-template-columns:minmax(14rem,1fr) auto;gap:1rem;padding:.8rem clamp(1rem,4vw,4rem);background:var(--ink);color:#fff;border-bottom:4px solid var(--blue)}}.trust[data-state="stale"]{{border-color:var(--amber)}}.trust[data-state="invalid"]{{border-color:var(--red)}}.trust strong{{font-family:var(--display);font-size:1.35rem;text-transform:uppercase;letter-spacing:.04em}}.trust p{{margin:0;color:#d8e0e8}}.shell{{max-width:1280px;margin:auto;padding:clamp(1rem,4vw,4rem)}}header{{display:grid;grid-template-columns:1.4fr 1fr;gap:2rem;align-items:end;border-bottom:1px solid var(--line);padding-bottom:2rem}}.eyebrow,.kicker,.phase{{font:700 .72rem/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--blue)}}h1,h2,h3,p{{margin-top:0}}h1{{max-width:12ch;margin:.2rem 0;font:700 clamp(3rem,8vw,7rem)/.82 var(--display);letter-spacing:-.045em;text-transform:uppercase}}h2{{font:700 clamp(1.5rem,3vw,2.5rem)/1 var(--display);text-transform:uppercase}}nav{{display:flex;flex-wrap:wrap;gap:.5rem;margin:2rem 0}}nav a{{padding:.55rem .8rem;background:var(--panel);border:1px solid var(--line);text-decoration:none}}section{{scroll-margin-top:6rem;margin:3rem 0}}.grid{{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(16rem,.7fr);gap:2rem}}.card,.incident{{background:var(--panel);border:1px solid var(--line);padding:1.25rem}}.spine{{position:relative;list-style:none;margin:0;padding:0 0 0 2.2rem}}.spine:before{{content:"";position:absolute;left:.55rem;top:.5rem;bottom:.5rem;width:2px;background:var(--blue)}}.spine-node{{position:relative;padding:0 0 2rem 1rem}}.spine-node:before{{content:"";position:absolute;left:-2rem;top:.2rem;width:.7rem;height:.7rem;background:var(--paper);border:3px solid var(--blue);border-radius:50%}}.spine-node h3{{margin:.35rem 0}}.spine-node p{{color:var(--slate)}}.claim-list,.sealed-list{{list-style:none;padding:0;margin:0}}.claim-list li,.sealed-list li{{display:grid;grid-template-columns:1fr auto auto;gap:1rem;padding:.8rem 0;border-bottom:1px solid var(--line)}}.empty{{color:var(--red)}}table{{width:100%;border-collapse:collapse;background:var(--panel)}}th,td{{padding:.7rem;text-align:left;border-bottom:1px solid var(--line)}}th{{font:700 .72rem/1 var(--mono);text-transform:uppercase;background:#e9f0f7}}.incident-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr));gap:1rem}}dt{{font:700 .7rem/1.4 var(--mono);text-transform:uppercase;color:var(--slate)}}dd{{margin:0 0 1rem}}.warning{{padding:1rem;border-left:4px solid var(--amber);background:#fff8e6}}.failure{{border-color:var(--red);background:#fff5f5}}footer{{border-top:1px solid var(--line);padding-top:1rem;color:var(--slate)}}
@media(max-width:760px){{.trust,header,.grid{{grid-template-columns:1fr}}h1{{font-size:3.5rem}}.claim-list li{{grid-template-columns:1fr}}.table-wrap{{overflow-x:auto}}}}
@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important;animation:none!important}}}}
</style></head><body>
<div class="trust" data-state="{escape(state)}" role="status" aria-live="polite"><div><strong>{escape(state.replace('-', ' '))}</strong><p>{escape(trust['reproducibility_status'])} reproducibility · read only — no transition authority</p></div><code>{escape(identity['checkpoint_ref'])}</code></div>
<main class="shell"><header><div><p class="eyebrow">Operator evidence monitor · schema 1</p><h1>Evidence, not instinct.</h1></div><p>One checkpointed view of what the system can support, what remains undecided, and which exact receipts carry each conclusion.</p></header>
<nav aria-label="Monitor views"><a href="#overview">Overview</a><a href="#coverage">Coverage</a><a href="#incidents">Incidents</a><a href="#lineage">Lineage</a></nav>
{f'<section class="warning failure"><h2>Verification failed</h2><ul>{failures}</ul><p>Derived decision content is suppressed. Inspect the authoritative Workspace verifier.</p></section>' if failures else ''}
{f'<section class="warning"><h2>Evidence debt</h2><ul>{debt}</ul><p>Standing and selection remain indeterminate.</p></section>' if debt else ''}
<section id="overview"><div class="grid"><div><p class="eyebrow">Overview</p><h2>Evidence spine</h2><ol class="spine">{packages or '<li class="empty">No derived spine is visible.</li>'}</ol></div><aside class="card"><p class="eyebrow">Reportable conclusions</p><ul class="claim-list">{conclusion_html}</ul></aside></div></section>
<section id="coverage"><p class="eyebrow">Coverage</p><h2>Assignments stay visible</h2><div class="table-wrap"><table><thead><tr><th>Cell</th><th>Required</th><th>Valid</th><th>Invalid</th><th>Missing</th><th>Replacement</th><th>Uncertainty</th></tr></thead><tbody>{coverage_rows or '<tr><td colspan="7">Coverage suppressed or unavailable.</td></tr>'}</tbody></table></div></section>
<section id="incidents"><p class="eyebrow">Incident workbench</p><h2>Disagreement is evidence</h2><div class="incident-grid">{incident_html or '<p class="empty">Incident conclusions are suppressed or unavailable.</p>'}</div></section>
<section id="lineage" class="grid"><div class="card"><p class="eyebrow">Lineage</p><h2>Bound authority</h2><p>Workspace <code>{escape(identity['workspace_id'])}</code></p><p>Current head <code>{escape(identity['current_checkpoint_ref'])}</code></p><p>Scheduling receipt {_authority_link(identity['scheduling_receipt_ref'])}</p></div><aside class="card"><p class="eyebrow">Sealed boundary</p><ul class="sealed-list">{sealed_html or '<li>No sealed handle projected.</li>'}</ul></aside></section>
<footer><p>Projection <code>{escape(projection.projection_ref)}</code>. Deleting this file deletes no evidence; rebuild from its named Checkpoint.</p></footer></main>
<script id="operator-evidence-projection" type="application/json">{embedded}</script></body></html>"""
    return html.encode("utf-8")


_STANDALONE_VERIFIER = r'''#!/usr/bin/env python3
import hashlib, json, sys, zipfile

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()

def ref(value):
    return "sha256:" + hashlib.sha256(value).hexdigest()

def verify(path):
    failures = []
    try:
        with zipfile.ZipFile(path) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        descriptor = json.loads(members["release-capsule.json"])
    except Exception as exc:
        return {"ok": False, "failures": ["release capsule unreadable: " + str(exc)]}
    if descriptor.get("schema_version") != "release-claim-capsule.1":
        failures.append("unsupported release capsule schema")
    declared_members = set(descriptor.get("member_refs", {}))
    expected_members = {"claim.ngc", "component-lock.json", "operator-projection.json", "schemas.json", "verify.py"}
    if declared_members != expected_members or set(members) != expected_members | {"release-capsule.json"}:
        failures.append("release capsule membership differs from the exact bundle")
    for name, expected in descriptor.get("member_refs", {}).items():
        if name not in members or ref(members[name]) != expected:
            failures.append("missing or corrupt release member: " + name)
    try:
        projection = json.loads(members["operator-projection.json"])
        inner_path = path + ".claim.tmp"
        open(inner_path, "wb").write(members["claim.ngc"])
        with zipfile.ZipFile(inner_path) as archive:
            inner = {name: archive.read(name) for name in archive.namelist()}
        import os; os.unlink(inner_path)
        claim = json.loads(inner["capsule.json"])
        for object_ref in claim.get("object_refs", []):
            name = "objects/sha256/" + object_ref[7:9] + "/" + object_ref[9:]
            if name not in inner or ref(inner[name]) != object_ref:
                failures.append("missing or corrupt claim object: " + object_ref)
        projected_ref = ref(canonical({"schema_version": projection["schema_version"], "material": projection["material"]}))
        if projection.get("projection_ref") != projected_ref or projected_ref != descriptor.get("operator_projection_ref"):
            failures.append("operator Projection identity mismatch")
        if projection["material"]["identity"]["checkpoint_ref"] != claim.get("checkpoint_ref"):
            failures.append("projection and claim Checkpoints differ")
        if projection["material"]["identity"]["claim_manifest_refs"] != [claim.get("claim_manifest_ref")]:
            failures.append("projection and reportable Claim Manifests differ")
    except Exception as exc:
        failures.append("worked claim cannot be rechecked: " + str(exc))
    return {"ok": not failures, "failures": failures, "claim_manifest_ref": descriptor.get("claim_manifest_ref"), "projection_ref": descriptor.get("operator_projection_ref")}

result = verify(sys.argv[1])
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
'''.encode("utf-8")


def build_release_claim_capsule(
    *,
    claim_capsule: bytes,
    projection: OperatorEvidenceProjection,
    schema_bundle: Mapping[str, Any],
    component_lock: Mapping[str, str],
) -> bytes:
    """Package exact offline verifier, schemas, locks, and one worked claim."""
    inner = verify_claim_capsule_bytes(claim_capsule)
    if not inner["ok"]:
        raise ValueError(f"Claim Capsule does not verify: {inner['failures']}")
    projection_mapping = projection.to_mapping()
    identity = projection_mapping["material"]["identity"]
    if identity["checkpoint_ref"] != inner["checkpoint_ref"]:
        raise ValueError("operator Projection and Claim Capsule name different Checkpoints")
    if identity["claim_manifest_refs"] != [inner["claim_manifest_ref"]]:
        raise ValueError("release Capsule requires exact reportable Claim Manifest closure")
    required_schemas = {
        "operator-evidence-projection.1",
        "claim-capsule.1",
        "release-claim-capsule.1",
    }
    declared = set(schema_bundle.get("schemas", ()))
    if not required_schemas <= declared:
        raise ValueError("release Capsule schema bundle is incomplete")
    if not component_lock or any(not str(key).strip() or not str(value).strip() for key, value in component_lock.items()):
        raise ValueError("release Capsule requires exact component locks")
    members = {
        "claim.ngc": claim_capsule,
        "component-lock.json": canonical_json(dict(sorted(component_lock.items()))),
        "operator-projection.json": projection.to_bytes(),
        "schemas.json": canonical_json(schema_bundle),
        "verify.py": _STANDALONE_VERIFIER,
    }
    descriptor = {
        "schema_version": "release-claim-capsule.1",
        "claim_manifest_ref": inner["claim_manifest_ref"],
        "checkpoint_ref": inner["checkpoint_ref"],
        "operator_projection_ref": projection.projection_ref,
        "claim_capsule_ref": digest_bytes(claim_capsule),
        "schema_bundle_ref": digest_bytes(members["schemas.json"]),
        "component_lock_ref": digest_bytes(members["component-lock.json"]),
        "verifier_ref": digest_bytes(_STANDALONE_VERIFIER),
        "member_refs": {name: digest_bytes(value) for name, value in sorted(members.items())},
    }
    return deterministic_zip({"release-capsule.json": canonical_json(descriptor), **members})


def verify_release_claim_capsule_bytes(value: bytes) -> dict[str, Any]:
    """Recheck the outer bundle, exact worked projection, and inner claim closure."""
    failures = []
    try:
        members = capsule_members(value)
        descriptor = json.loads(members["release-capsule.json"])
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "failures": [f"release capsule unreadable: {exc}"]}
    if descriptor.get("schema_version") != "release-claim-capsule.1":
        failures.append("unsupported release Capsule schema")
    expected_members = {
        "claim.ngc",
        "component-lock.json",
        "operator-projection.json",
        "schemas.json",
        "verify.py",
    }
    if set(descriptor.get("member_refs", {})) != expected_members or set(members) != expected_members | {"release-capsule.json"}:
        failures.append("release Capsule membership differs from the exact bundle")
    for name, expected in descriptor.get("member_refs", {}).items():
        data = members.get(name)
        if data is None or digest_bytes(data) != expected:
            failures.append(f"missing or corrupt release member: {name}")
    if members.get("verify.py") != _STANDALONE_VERIFIER:
        failures.append("release Capsule verifier differs from the qualified verifier")
    inner = verify_claim_capsule_bytes(members.get("claim.ngc", b""))
    failures.extend(f"inner claim: {item}" for item in inner["failures"])
    try:
        projection = json.loads(members["operator-projection.json"])
        projected_ref = digest_json(
            {"schema_version": projection["schema_version"], "material": projection["material"]}
        )
        if projection.get("projection_ref") != projected_ref or projected_ref != descriptor.get("operator_projection_ref"):
            failures.append("operator Projection identity mismatch")
        identity = projection["material"]["identity"]
        if identity["checkpoint_ref"] != inner.get("checkpoint_ref"):
            failures.append("operator Projection and claim Checkpoints differ")
        if identity["claim_manifest_refs"] != [inner.get("claim_manifest_ref")]:
            failures.append("operator Projection omits or adds a reportable claim")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        failures.append(f"worked operator Projection unreadable: {exc}")
    return {
        "ok": not failures,
        "failures": failures,
        "claim_manifest_ref": descriptor.get("claim_manifest_ref"),
        "checkpoint_ref": descriptor.get("checkpoint_ref"),
        "operator_projection_ref": descriptor.get("operator_projection_ref"),
        "component_lock_ref": descriptor.get("component_lock_ref"),
        "schema_bundle_ref": descriptor.get("schema_bundle_ref"),
        "verifier_ref": descriptor.get("verifier_ref"),
    }
