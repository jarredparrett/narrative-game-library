"""Deterministic print planning, rendering, preflight, and packaging."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import csv
from html import escape
import json
import re
from typing import Any, Iterable, Mapping
import zipfile

import pypdf
from pypdf import PdfReader, PdfWriter
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from narrative_game.authoring import parse_game_definition
from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json

from .model import PhysicalExport, PhysicalExportProfile, PhysicalFile


PHYSICAL_EXPORTER_VERSION = "0.5.0"


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _archive(files: Iterable[PhysicalFile]) -> bytes:
    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for item in sorted(files, key=lambda value: value.path):
            info = zipfile.ZipInfo(item.path, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.extra = b""
            info.comment = b""
            info.internal_attr = 0
            info.external_attr = 0o600 << 16
            archive.writestr(info, item.data)
    return target.getvalue()


def _inline(value: str) -> str:
    """Render the small, deliberately supported inline Markdown subset."""
    value = escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', value)
    return value


class _MarkedCanvas(canvas.Canvas):
    """ReportLab Canvas with stable metadata and provenance on every page."""

    def __init__(self, *args: Any, title: str, provenance: str, **kwargs: Any):
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self._document_title = title
        self._provenance = provenance
        self.setTitle(title)
        self.setAuthor("narrative-game-library")
        self.setCreator(f"narrative-game-library physical exporter {PHYSICAL_EXPORTER_VERSION}")
        self.setSubject(provenance)

    def showPage(self) -> None:
        self.saveState()
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#444444"))
        self.drawCentredString(LETTER[0] / 2, 20, self._provenance)
        self.setFont("Helvetica", 7)
        self.drawRightString(LETTER[0] - 36, 20, f"Page {self.getPageNumber()}")
        self.restoreState()
        super().showPage()


def _text_story(data: bytes, media_type: str) -> list[Any]:
    text = data.decode("utf-8")
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "GameBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        spaceAfter=7,
    )
    h1 = ParagraphStyle(
        "GameH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        spaceAfter=12,
        textColor=colors.HexColor("#1f2933"),
    )
    h2 = ParagraphStyle(
        "GameH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        spaceBefore=7,
        spaceAfter=7,
        textColor=colors.HexColor("#334e68"),
    )
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11)
    quote = ParagraphStyle(
        "Quote",
        parent=body,
        leftIndent=18,
        borderColor=colors.HexColor("#9fb3c8"),
        borderWidth=1,
        borderPadding=8,
        backColor=colors.HexColor("#f5f7fa"),
    )
    if media_type == "text/csv":
        rows = list(csv.reader(text.splitlines()))
        table = Table([[Paragraph(_inline(cell), small) for cell in row] for row in rows], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2ec")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#829ab1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [Paragraph("Exterior camera log", h1), table]
    if media_type == "text/plain":
        return [Preformatted(text, ParagraphStyle("Plain", parent=body, fontName="Courier", fontSize=9, leading=12))]

    story: list[Any] = []
    paragraph: list[str] = []
    table_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(_inline(" ".join(paragraph)), body))
            paragraph.clear()

    def flush_table() -> None:
        if not table_lines:
            return
        rows = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            rows.append([Paragraph(_inline(cell), small) for cell in cells])
        if rows:
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2ec")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#829ab1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 8))
        table_lines.clear()

    for raw in [*text.splitlines(), ""]:
        line = raw.rstrip()
        if line.startswith("|") and line.endswith("|"):
            flush_paragraph()
            table_lines.append(line)
            continue
        flush_table()
        if not line:
            flush_paragraph()
        elif line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[2:]), h1))
        elif line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[3:]), h2))
        elif line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[2:]), quote))
        elif re.match(r"^(?:- |\d+\. )", line):
            flush_paragraph()
            item = re.sub(r"^(?:- |\d+\. )", "", line)
            story.append(Paragraph(f"&#8226;&nbsp; {_inline(item)}", body))
        elif line == "---":
            flush_paragraph()
            story.append(Spacer(1, 8))
        else:
            paragraph.append(line)
    return story


def _render_text_pdf(
    *, data: bytes, media_type: str, title: str, profile: PhysicalExportProfile
) -> bytes:
    target = BytesIO()
    document = SimpleDocTemplate(
        target,
        pagesize=LETTER,
        rightMargin=profile.margin_points,
        leftMargin=profile.margin_points,
        topMargin=profile.margin_points,
        bottomMargin=profile.margin_points,
        title=title,
        author="narrative-game-library",
    )

    def canvas_factory(*args: Any, **kwargs: Any) -> _MarkedCanvas:
        return _MarkedCanvas(
            *args,
            title=title,
            provenance=profile.provenance_label,
            **kwargs,
        )

    document.build(_text_story(data, media_type), canvasmaker=canvas_factory)
    return target.getvalue()


def _overlay(page_width: float, page_height: float, profile: PhysicalExportProfile) -> bytes:
    target = BytesIO()
    mark = canvas.Canvas(target, pagesize=(page_width, page_height), invariant=1)
    mark.setAuthor("narrative-game-library")
    mark.setCreator(f"narrative-game-library physical exporter {PHYSICAL_EXPORTER_VERSION}")
    mark.saveState()
    mark.setFillColor(colors.HexColor("#333333"))
    mark.setFont("Helvetica-Bold", 6.5)
    mark.translate(11, page_height / 2)
    mark.rotate(90)
    mark.drawCentredString(0, 0, profile.provenance_label)
    mark.restoreState()
    mark.save()
    return target.getvalue()


def _mark_existing_pdf(data: bytes, profile: PhysicalExportProfile) -> bytes:
    reader = PdfReader(BytesIO(data))
    writer = PdfWriter()
    for source_page in reader.pages:
        width = float(source_page.mediabox.width)
        height = float(source_page.mediabox.height)
        overlay_page = PdfReader(BytesIO(_overlay(width, height, profile))).pages[0]
        writer.add_page(source_page)
        writer.pages[-1].merge_page(overlay_page, over=True)
    writer.add_metadata(
        {
            "/Title": "Marked fictional-game rendition",
            "/Author": "narrative-game-library",
            "/Creator": f"narrative-game-library physical exporter {PHYSICAL_EXPORTER_VERSION}",
            "/Subject": profile.provenance_label,
            "/CreationDate": "D:19971017000000-05'00'",
            "/ModDate": "D:19971017000000-05'00'",
        }
    )
    target = BytesIO()
    writer.write(target)
    return target.getvalue()


def _material_by_resource(release: GameRelease) -> dict[str, Any]:
    return {
        item["resource_id"]: release.file(item["path"])
        for item in release.manifest["materials"]
    }


def _validate_claim_trace(release: GameRelease) -> list[dict[str, Any]]:
    game = parse_game_definition(release.file("trusted/game.json").data)
    propositions = {item.id for item in game.propositions}
    materials = _material_by_resource(release)
    receipts = {
        item["resource_id"]: json.loads(release.file(f"receipts/{item['resource_id']}.json").data)
        for item in release.manifest["materials"]
    }
    claims = release.manifest["compilation_options"].get("displayed_claims", [])
    if not claims:
        raise ValueError("Physical Export requires a displayed-claim lineage")
    verified = []
    for claim in claims:
        resource_id = claim["resource_id"]
        proposition_id = claim["proposition_id"]
        if proposition_id not in propositions:
            raise ValueError(f"displayed claim names missing Proposition: {proposition_id}")
        if resource_id not in materials:
            raise ValueError(f"displayed claim names missing Resource: {resource_id}")
        if claim["source"] == "material-text":
            quote = claim["quote"]
            try:
                text = materials[resource_id].data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"text claim names non-text Resource: {resource_id}") from exc
            if quote not in text:
                raise ValueError(f"displayed claim quote is absent from {resource_id}: {quote!r}")
            evidence = {"quote": quote, "content_hash": materials[resource_id].content_hash}
        elif claim["source"] == "artifact-request":
            pin = claim["pin"]
            receipt = receipts[resource_id]
            request = receipt.get("artifact_request", receipt)
            if proposition_id not in request.get("fact_references", []):
                raise ValueError(f"artifact claim lacks fact reference: {proposition_id}")
            if pin not in request.get("pins", {}):
                raise ValueError(f"artifact claim names missing request pin: {pin}")
            evidence = {"pin": pin, "value": request["pins"][pin], "request_hash": digest_json(request)}
        else:
            raise ValueError(f"unsupported displayed-claim source: {claim['source']}")
        verified.append({**claim, "verified_evidence": evidence})
    return verified


def _delivery_by_resource(game: Any) -> dict[tuple[str, str], str]:
    evidence_by_id = {item.id: item for item in game.evidence}
    phase_order = {item.id: item.order for item in game.phases}
    delivery: dict[tuple[str, str], list[str]] = defaultdict(list)
    for reveal in game.reveals:
        resource_id = evidence_by_id[reveal.evidence_id].resource_id
        for seat_id in reveal.audience_seat_ids:
            delivery[(resource_id, seat_id)].append(reveal.phase_id)
    return {
        key: min(phases, key=lambda phase_id: phase_order[phase_id])
        for key, phases in delivery.items()
    }


def _build_plan(
    release: GameRelease,
    profile: PhysicalExportProfile,
    rendition_files: Mapping[str, PhysicalFile],
) -> dict[str, Any]:
    game = parse_game_definition(release.file("trusted/game.json").data)
    delivery = _delivery_by_resource(game)
    resources = {item.id: item for item in game.kernel.resources}
    copies = []
    containers: dict[str, dict[str, Any]] = {}
    for policy in sorted(game.kernel.access_policies, key=lambda item: item.id):
        resource_id = policy.resource.id
        resource = resources[resource_id]
        rendition = rendition_files[resource_id]
        for grantee in sorted(policy.grantees, key=str):
            if grantee.kind == "viewer" and grantee.id == "host":
                audience = "viewer:host"
                condition = "host-setup"
                container_id = "host-binder"
                container_label = "HOST ONLY - ANSWERS AND MASTER MATERIALS"
            elif grantee.kind == "seat":
                audience = f"seat:{grantee.id}"
                condition = delivery.get((resource_id, grantee.id), "opening")
                container_id = f"{grantee.id}-{condition}"
                container_label = f"{grantee.id.upper()} - OPEN AT {condition.upper()}"
            else:
                continue
            containers.setdefault(
                container_id,
                {
                    "container_id": container_id,
                    "label": container_label,
                    "audience": audience,
                    "delivery_condition": condition,
                },
            )
            copies.append(
                {
                    "copy_id": f"copy-{resource_id}-{grantee.kind}-{grantee.id}",
                    "resource_id": resource_id,
                    "source_hash": resource.content_hash,
                    "rendition_path": rendition.path,
                    "rendition_hash": rendition.content_hash,
                    "audience": audience,
                    "delivery_condition": condition,
                    "custodian": "host",
                    "container_id": container_id,
                    "labels": [profile.provenance_label, container_label],
                    "copy_count": 1,
                    "duplicate_of": None,
                }
            )
    ordered_copies = sorted(copies, key=lambda item: item["copy_id"])
    first_copy: dict[str, str] = {}
    for copy in ordered_copies:
        prior = first_copy.get(copy["resource_id"])
        copy["duplicate_of"] = prior
        first_copy.setdefault(copy["resource_id"], copy["copy_id"])
    return {
        "schema_version": "0.5",
        "release_id": release.release_id,
        "profile": profile.to_mapping(),
        "containers": [containers[key] for key in sorted(containers)],
        "copies": ordered_copies,
        "production": {
            "page_size": profile.page_size,
            "orientation": profile.orientation,
            "color_mode": profile.color_mode,
            "sides": profile.sides,
            "bleed": "none",
            "margins_points": profile.margin_points,
            "fonts": ["Helvetica", "Helvetica-Bold", "Courier"],
            "packing_order": [
                "print all files at 100 percent scale",
                "compare every printed page count with preflight.json",
                "assemble host-binder",
                "assemble each Seat envelope by delivery condition",
                "verify copy IDs against this plan",
                "record any production substitution before play",
            ],
        },
    }


def _guide_markdown(release: GameRelease, plan: Mapping[str, Any]) -> bytes:
    lines = [
        "# Physical package assembly guide",
        "",
        f"Release: `{release.release_id}`",
        "",
        "This archive is a deterministic production projection of one immutable Game Release. It does not record an actual print run.",
        "",
        "## Assemble",
        "",
        "1. Print every PDF under `print/` at 100 percent scale, US Letter, portrait, simplex.",
        "2. Confirm each file's page count and hash against `trusted/preflight.json`.",
        "3. Create the containers below and copy each asset exactly as specified in `trusted/physical-package-plan.json`.",
        "4. Do not remove the fictional-game label from any page or container.",
        "5. Give opening containers before play. Give investigation and resolution containers only when the host advances to that phase.",
        "6. Keep the host binder private. Use `trusted/claim-trace.json` to audit displayed factual claims.",
        "",
        "## Containers",
        "",
    ]
    for container in plan["containers"]:
        count = sum(1 for copy in plan["copies"] if copy["container_id"] == container["container_id"])
        lines.append(f"- `{container['container_id']}` - {container['label']} ({count} copies)")
    lines.extend(
        [
            "",
            "## Run controls",
            "",
            "- Opening: deliver opening Seat containers and the shared opening records.",
            "- Investigation: deliver each Seat's investigation container; record physical disclosure in the Session ledger.",
            "- Resolution: deliver the marked deed and accessible rendition together; collect the joint finding form.",
            "- Debrief: use the host guide's canonical resolution and preserve the completed Session History.",
            "",
            "## Verification",
            "",
            "A production operator can verify this package offline from its embedded Release, canonical manifests, SHA-256 hashes, page counts, and fixed toolchain versions. The unmarked exact deed remains inside `source/game-release.zip`; the printable deed is a separately hashed, visibly marked rendition.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _render_labels_pdf(plan: Mapping[str, Any], profile: PhysicalExportProfile) -> bytes:
    target = BytesIO()
    document = SimpleDocTemplate(
        target,
        pagesize=LETTER,
        rightMargin=profile.margin_points,
        leftMargin=profile.margin_points,
        topMargin=profile.margin_points,
        bottomMargin=profile.margin_points,
        title="Physical package container labels",
        author="narrative-game-library",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "LabelTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.HexColor("#1f2933"),
        spaceAfter=8,
    )
    card = ParagraphStyle(
        "LabelCard",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
    )
    story: list[Any] = [
        Paragraph("Container labels", title),
        Paragraph(
            "Cut around each bordered card and keep it attached to the matching container.",
            card,
        ),
        Spacer(1, 10),
    ]
    for container in plan["containers"]:
        copies = [
            copy for copy in plan["copies"] if copy["container_id"] == container["container_id"]
        ]
        content = [
            f"<b>{escape(container['label'])}</b>",
            f"Container ID: <font name=\"Courier\">{escape(container['container_id'])}</font>",
            f"Audience: <font name=\"Courier\">{escape(container['audience'])}</font>",
            f"Delivery: <font name=\"Courier\">{escape(container['delivery_condition'])}</font>",
            "<b>Contents</b>",
            *[
                f"[ ] <font name=\"Courier\">{escape(copy['copy_id'])}</font>"
                for copy in copies
            ],
            f"<b>{escape(profile.provenance_label)}</b>",
        ]
        table = Table(
            [[Paragraph("<br/>".join(content), card)]],
            colWidths=[LETTER[0] - (2 * profile.margin_points)],
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#486581")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fa")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(KeepTogether([table, Spacer(1, 9)]))

    def canvas_factory(*args: Any, **kwargs: Any) -> _MarkedCanvas:
        return _MarkedCanvas(
            *args,
            title="Physical package container labels",
            provenance=profile.provenance_label,
            **kwargs,
        )

    document.build(story, canvasmaker=canvas_factory)
    return target.getvalue()


def _preflight(files: Iterable[PhysicalFile]) -> dict[str, Any]:
    checks = []
    for item in sorted(files, key=lambda value: value.path):
        record: dict[str, Any] = {
            "path": item.path,
            "content_hash": item.content_hash,
            "bytes": len(item.data),
            "nonempty": bool(item.data),
        }
        if item.media_type == "application/pdf":
            reader = PdfReader(BytesIO(item.data))
            boxes = [
                [float(page.mediabox.width), float(page.mediabox.height)]
                for page in reader.pages
            ]
            record.update(
                {
                    "page_count": len(reader.pages),
                    "page_boxes": boxes,
                    "letter_portrait": all(
                        abs(width - LETTER[0]) < 1 and abs(height - LETTER[1]) < 1
                        for width, height in boxes
                    ),
                }
            )
        checks.append(record)
    failures = [
        item["path"]
        for item in checks
        if not item["nonempty"]
        or ("letter_portrait" in item and not item["letter_portrait"])
    ]
    return {
        "schema_version": "0.5",
        "ok": not failures,
        "failures": failures,
        "files": checks,
    }


def export_physical(
    release: GameRelease,
    profile: PhysicalExportProfile | None = None,
) -> PhysicalExport:
    """Produce one deterministic, offline-verifiable physical package."""
    profile = profile or PhysicalExportProfile()
    claim_trace = _validate_claim_trace(release)
    game = parse_game_definition(release.file("trusted/game.json").data)
    material_files = _material_by_resource(release)
    rendition_files: dict[str, PhysicalFile] = {}
    output_files: list[PhysicalFile] = [
        PhysicalFile("source/game-release.zip", "application/zip", release.bundle_bytes, "trusted-producer")
    ]
    for resource in sorted(game.kernel.resources, key=lambda item: item.id):
        material = material_files[resource.id]
        if resource.media_type == "application/pdf":
            rendered = _mark_existing_pdf(material.data, profile)
        elif resource.media_type.startswith("text/"):
            rendered = _render_text_pdf(
                data=material.data,
                media_type=resource.media_type,
                title=resource.label,
                profile=profile,
            )
        else:
            raise ValueError(f"Physical Export cannot render {resource.media_type}")
        physical_file = PhysicalFile(
            path=f"print/resources/{resource.id}.pdf",
            media_type="application/pdf",
            data=rendered,
            audience="as-planned",
        )
        rendition_files[resource.id] = physical_file
        output_files.append(physical_file)

    plan = _build_plan(release, profile, rendition_files)
    guide_md = _guide_markdown(release, plan)
    guide_pdf = _render_text_pdf(
        data=guide_md,
        media_type="text/markdown",
        title="Physical package assembly guide",
        profile=profile,
    )
    labels_pdf = _render_labels_pdf(plan, profile)
    output_files.extend(
        [
            PhysicalFile("guides/assembly-guide.md", "text/markdown", guide_md, "trusted-producer"),
            PhysicalFile("guides/assembly-guide.pdf", "application/pdf", guide_pdf, "trusted-producer"),
            PhysicalFile("print/container-labels.pdf", "application/pdf", labels_pdf, "trusted-producer"),
            PhysicalFile(
                "trusted/physical-package-plan.json",
                "application/json",
                canonical_json(plan),
                "trusted-producer",
            ),
            PhysicalFile(
                "trusted/claim-trace.json",
                "application/json",
                canonical_json({"schema_version": "0.5", "claims": claim_trace}),
                "trusted-producer",
            ),
        ]
    )
    preflight = _preflight(output_files)
    if not preflight["ok"]:
        raise ValueError(f"Physical preflight failed: {preflight['failures']}")
    preflight_file = PhysicalFile(
        "trusted/preflight.json",
        "application/json",
        canonical_json(preflight),
        "trusted-producer",
    )
    output_files.append(preflight_file)
    core_files = tuple(sorted(output_files, key=lambda item: item.path))
    export_core = {
        "schema_version": "0.5",
        "release_id": release.release_id,
        "release_bundle_hash": release.bundle_hash,
        "exporter": {"id": "narrative-game-library.physical", "version": PHYSICAL_EXPORTER_VERSION},
        "toolchain": {
            "pypdf": pypdf.__version__,
            "reportlab": reportlab.Version,
        },
        "profile": profile.to_mapping(),
        "plan_hash": digest_json(plan),
        "preflight_hash": digest_json(preflight),
        "files": [item.descriptor() for item in core_files],
        "physical_readiness": "production-ready-layout",
        "artifact_measurement": "development-only",
        "printing_receipt": None,
    }
    export_id = digest_json(export_core)
    manifest = {"export_id": export_id, **export_core}
    manifest_file = PhysicalFile(
        "physical-export.json",
        "application/json",
        canonical_json(manifest),
        "public-metadata",
    )
    files = tuple(sorted((*core_files, manifest_file), key=lambda item: item.path))
    archive_bytes = _archive(files)
    result = PhysicalExport(
        export_id=export_id,
        release_id=release.release_id,
        profile=profile,
        plan=_copy(plan),
        preflight=_copy(preflight),
        files=files,
        archive_bytes=archive_bytes,
        archive_hash=digest_bytes(archive_bytes),
    )
    verify_physical_export(result, release)
    return result


def verify_physical_export(value: PhysicalExport, release: GameRelease) -> None:
    """Verify identity, embedded Release, hashes, preflight, and package plan."""
    if value.release_id != release.release_id:
        raise ValueError("Physical Export names another Release")
    if value.file("source/game-release.zip").data != release.bundle_bytes:
        raise ValueError("Physical Export does not preserve the exact Game Release")
    manifest = json.loads(value.file("physical-export.json").data)
    if manifest["export_id"] != value.export_id:
        raise ValueError("Physical Export manifest identity differs")
    described = {item["path"]: item for item in manifest["files"]}
    actual = {item.path: item for item in value.files if item.path != "physical-export.json"}
    if set(described) != set(actual):
        raise ValueError("Physical Export file graph differs from its manifest")
    for path, item in actual.items():
        if described[path] != item.descriptor():
            raise ValueError(f"Physical Export file descriptor differs: {path}")
    if digest_json(value.plan) != manifest["plan_hash"]:
        raise ValueError("Physical Package Plan hash differs")
    if digest_json(value.preflight) != manifest["preflight_hash"] or not value.preflight["ok"]:
        raise ValueError("Physical preflight differs or failed")
    if digest_bytes(value.archive_bytes) != value.archive_hash:
        raise ValueError("Physical archive hash differs")
    if _archive(value.files) != value.archive_bytes:
        raise ValueError("Physical archive is not canonical")
