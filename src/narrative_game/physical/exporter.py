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
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from narrative_game.authoring import parse_game_definition
from narrative_game.narrative import CharacterDossier, render_dossier_markdown
from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json

from .model import PhysicalExport, PhysicalExportProfile, PhysicalFile


PHYSICAL_EXPORTER_VERSION = "0.7.3"


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


def _table_column_widths(rows: list[list[str]], available_width: float) -> list[float]:
    """Allocate stable table width toward columns that carry longer evidence."""
    column_count = max((len(row) for row in rows), default=0)
    if column_count == 0:
        return []
    minimum = min(48.0, available_width / column_count)
    remaining = max(0.0, available_width - minimum * column_count)
    weights = [
        max(1, min(48, max((len(row[index]) for row in rows if index < len(row)), default=1)))
        for index in range(column_count)
    ]
    total_weight = sum(weights)
    return [minimum + remaining * weight / total_weight for weight in weights]


def _text_story(
    data: bytes, media_type: str, *, available_width: float = LETTER[0] - 108
) -> list[Any]:
    text = data.decode("utf-8")
    compact_form = "joint finding sheet" in text.casefold()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "GameBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=11 if compact_form else 12,
        spaceAfter=1 if compact_form else 3.5,
    )
    h1 = ParagraphStyle(
        "GameH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        spaceAfter=6 if compact_form else 10,
        textColor=colors.HexColor("#1f2933"),
    )
    h2 = ParagraphStyle(
        "GameH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=14 if compact_form else 15,
        spaceBefore=3 if compact_form else 6,
        spaceAfter=2 if compact_form else 5,
        textColor=colors.HexColor("#334e68"),
    )
    h3 = ParagraphStyle(
        "GameH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        spaceBefore=5,
        spaceAfter=4,
        textColor=colors.HexColor("#334e68"),
        keepWithNext=True,
    )
    h4 = ParagraphStyle(
        "GameH4",
        parent=h3,
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#243b53"),
    )
    small = ParagraphStyle("Small", parent=body, fontSize=9, leading=11.5)
    csv_cell = ParagraphStyle(
        "CsvCell",
        parent=body,
        fontSize=8.5,
        leading=10,
        splitLongWords=False,
    )
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
        blocks: list[list[list[str]]] = []
        current: list[list[str]] = []
        for row in csv.reader(text.splitlines()):
            if not row:
                if current:
                    blocks.append(current)
                    current = []
                continue
            current.append(row)
        if current:
            blocks.append(current)

        story: list[Any] = []
        has_document_title = False

        def append_table(rows: list[list[str]]) -> None:
            column_widths = _table_column_widths(rows, available_width)
            if rows and "source_system" in rows[0] and "observed_value" in rows[0]:
                source_index = rows[0].index("source_system")
                observation_index = rows[0].index("observed_value")
                source_floor = 110.0
                transfer = min(
                    max(0.0, source_floor - column_widths[source_index]),
                    max(0.0, column_widths[observation_index] - 100.0),
                )
                column_widths[source_index] += transfer
                column_widths[observation_index] -= transfer
            table = Table(
                [[Paragraph(_inline(cell), csv_cell) for cell in row] for row in rows],
                colWidths=column_widths,
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2ec")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#829ab1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.extend((table, Spacer(1, 5)))

        for block in blocks:
            rows = list(block)
            if rows and len(rows[0]) == 1:
                heading = rows.pop(0)[0]
                story.append(Paragraph(_inline(heading), h1 if not has_document_title else h2))
                has_document_title = True
            elif not has_document_title:
                story.append(Paragraph("Exterior camera log", h1))
                has_document_title = True
            if not rows:
                continue
            if all(len(row) == 1 for row in rows):
                story.extend(Paragraph(_inline(row[0]), body) for row in rows)
                continue
            column_count = max(len(row) for row in rows)
            padded = [row + [""] * (column_count - len(row)) for row in rows]
            append_table(padded)
        return story
    if media_type == "text/plain":
        plain = ParagraphStyle(
            "Plain",
            parent=body,
            fontName="Courier",
            fontSize=10,
            leading=12.5,
        )
        return [Paragraph(escape(text).replace("\n", "<br/>"), plain)]

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
        elif line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[4:]), h3))
        elif line.startswith("#### "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[5:]), h4))
        elif line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(_inline(line[2:]), quote))
        elif re.match(r"^(?:- |\d+\. )", line):
            flush_paragraph()
            item = re.sub(r"^(?:- |\d+\. )", "", line)
            story.append(Paragraph(f"&#45;&nbsp; {_inline(item)}", body))
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

    document.build(
        _text_story(
            data,
            media_type,
            available_width=LETTER[0] - 2 * profile.margin_points,
        ),
        canvasmaker=canvas_factory,
    )
    return target.getvalue()


def render_dossier_pdf(
    game: Any,
    dossier: CharacterDossier,
    profile: PhysicalExportProfile | None = None,
) -> bytes:
    """Render one deterministic seat-private Dossier and enforce its page contract."""
    profile = profile or PhysicalExportProfile()
    rendered = _render_text_pdf(
        data=render_dossier_markdown(game, dossier),
        media_type="text/markdown",
        title=f"Character dossier — {dossier.seat_id}",
        profile=profile,
    )
    page_count = len(PdfReader(BytesIO(rendered)).pages)
    if not 3 <= page_count <= 5:
        raise ValueError(
            f"Dossier {dossier.dossier_id} rendered to {page_count} pages; expected 3–5"
        )
    return rendered


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
    dossier_renditions: Mapping[str, PhysicalFile] | None = None,
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
    for seat_id, rendition in sorted((dossier_renditions or {}).items()):
        container_id = f"{seat_id}-opening"
        container_label = f"{seat_id.upper()} - OPENING DOSSIER"
        containers.setdefault(
            container_id,
            {
                "container_id": container_id,
                "label": container_label,
                "audience": f"seat:{seat_id}",
                "delivery_condition": "opening",
            },
        )
        source = release.file(f"dossiers/{seat_id}.md")
        copies.append(
            {
                "copy_id": f"copy-dossier-{seat_id}",
                "resource_id": f"dossier:{seat_id}",
                "source_hash": source.content_hash,
                "rendition_path": rendition.path,
                "rendition_hash": rendition.content_hash,
                "audience": f"seat:{seat_id}",
                "delivery_condition": "opening",
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


def _marker_text(value: str) -> str:
    """Normalize authored and extracted text for a deterministic order check."""
    value = re.sub(r"[^\w$]+", " ", value, flags=re.UNICODE)
    return " ".join(value.casefold().split())


def _reading_markers(data: bytes, media_type: str) -> tuple[str, ...]:
    """Extract line-sized markers whose order must survive text rendering."""
    text = data.decode("utf-8")
    if media_type == "text/csv":
        raw_markers = [" ".join(cell for cell in row if cell.strip()) for row in csv.reader(text.splitlines())]
    else:
        raw_markers = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or re.fullmatch(r"\|?(?:\s*:?-+:?\s*\|)+\s*", stripped):
                continue
            stripped = re.sub(r"^(?:#{1,3}\s+|>\s+|-\s+|\d+\.\s+)", "", stripped)
            if stripped.startswith("|") and stripped.endswith("|"):
                stripped = " ".join(cell.strip() for cell in stripped.strip("|").split("|"))
            raw_markers.append(stripped)
    return tuple(marker for value in raw_markers if (marker := _marker_text(value)))


def _pdf_reading_markers(data: bytes) -> tuple[str, ...]:
    """Sample stable OCR markers from every imported page before overlaying it."""
    reader = PdfReader(BytesIO(data))
    markers: list[str] = []
    for page in reader.pages:
        candidates = [
            marker
            for line in (page.extract_text() or "").splitlines()
            if len(marker := _marker_text(line)) >= 8
        ]
        if not candidates:
            continue
        indexes = sorted({0, len(candidates) // 2, len(candidates) - 1})
        markers.extend(candidates[index] for index in indexes)
    return tuple(markers)


def _label_reading_markers(plan: Mapping[str, Any]) -> tuple[str, ...]:
    """Derive label markers from the package plan that authors the label sheet."""
    values = ["Container labels"]
    for container in plan["containers"]:
        values.extend(
            (
                container["label"],
                f"Container ID: {container['container_id']}",
                f"Audience: {container['audience']}",
                f"Delivery: {container['delivery_condition']}",
                "Contents",
            )
        )
        values.extend(
            copy["copy_id"]
            for copy in plan["copies"]
            if copy["container_id"] == container["container_id"]
        )
    return tuple(_marker_text(value) for value in values)


def _markers_appear_in_order(
    extracted: str,
    markers: Iterable[str],
    ignored_text: Iterable[str] = (),
) -> bool:
    for value in ignored_text:
        extracted = extracted.replace(value, " ")
    extracted = re.sub(r"(?im)^\s*Page\s+\d+\s*$", " ", extracted)
    haystack = _marker_text(extracted)
    cursor = 0
    for marker in markers:
        position = haystack.find(marker, cursor)
        if position < 0:
            return False
        cursor = position + len(marker)
    return True


def _pdf_font_measurements(reader: PdfReader) -> list[tuple[str, float]]:
    measurements: list[tuple[str, float]] = []
    for page in reader.pages:
        def visitor(text: str, _cm: Any, _tm: Any, _font: Any, font_size: float) -> None:
            if text.strip() and float(font_size) > 0:
                measurements.append((text.strip(), float(font_size)))

        page.extract_text(visitor_text=visitor)
    return measurements


def _pdf_font_sizes(reader: PdfReader) -> list[float]:
    return [size for _text, size in _pdf_font_measurements(reader)]


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(value: str) -> float:
        channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def _preflight(
    files: Iterable[PhysicalFile],
    rendition_expectations: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    expectations = rendition_expectations or {}
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
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            font_measurements = _pdf_font_measurements(reader)
            font_sizes = [size for _text, size in font_measurements]
            expectation = expectations.get(item.path, {})
            markers = tuple(expectation.get("reading_markers", ()))
            ignored_text = tuple(expectation.get("ignored_text", ()))
            minimum_font_size = min(font_sizes) if font_sizes else None
            reportlab_rendition = expectation.get("renderer") == "reportlab-platypus"
            artifact_overlay = expectation.get("renderer") == "artifact-overlay"
            authored_content_sizes = [
                size
                for text, size in font_measurements
                if not re.fullmatch(r"Page\s+\d+", text)
                and text not in ignored_text
            ]
            expected_boxes = expectation.get("source_page_boxes")
            overlay_layout_passed = (
                boxes == expected_boxes if artifact_overlay and expected_boxes is not None else None
            )
            palette_ratios = (
                _contrast_ratio("#000000", "#ffffff"),
                _contrast_ratio("#334e68", "#ffffff"),
                _contrast_ratio("#1f2933", "#ffffff"),
                _contrast_ratio("#444444", "#ffffff"),
                _contrast_ratio("#000000", "#d9e2ec"),
                _contrast_ratio("#000000", "#f5f7fa"),
            )
            record.update(
                {
                    "page_count": len(reader.pages),
                    "page_boxes": boxes,
                    "letter_portrait": all(
                        abs(width - LETTER[0]) < 1 and abs(height - LETTER[1]) < 1
                        for width, height in boxes
                    ),
                    "pdf_checks": {
                        "parseable_page_tree": bool(reader.pages),
                        "extractable_text": bool(extracted.strip()),
                        "minimum_font_size": {
                            "measured_points": minimum_font_size,
                            "threshold_points": 6.0,
                            "passed": minimum_font_size is not None and minimum_font_size >= 6.0,
                            "scope": "nonvisual OCR text layer" if artifact_overlay else "rendered text",
                        },
                        "authored_content_font_size": {
                            "executed": reportlab_rendition,
                            "measured_points": min(authored_content_sizes) if reportlab_rendition and authored_content_sizes else None,
                            "threshold_points": 8.5,
                            "scope": "authored content excluding page numbers and provenance marks",
                            "passed": (
                                min(authored_content_sizes) >= 8.5
                                if reportlab_rendition and authored_content_sizes else None
                            ),
                        },
                        "authored_reading_order": {
                            "executed": bool(markers),
                            "marker_count": len(markers),
                            "passed": _markers_appear_in_order(extracted, markers, ignored_text) if markers else None,
                        },
                        "layout_engine_completed": {
                            "executed": reportlab_rendition or artifact_overlay,
                            "method": (
                                "source page count and media boxes preserved by artifact overlay"
                                if artifact_overlay
                                else "ReportLab Platypus completed without LayoutError"
                            ),
                            "passed": overlay_layout_passed if artifact_overlay else True,
                        },
                        "renderer_palette_contrast": {
                            "executed": reportlab_rendition or artifact_overlay,
                            "scope": "added provenance mark" if artifact_overlay else "library-rendered palette",
                            "minimum_ratio": round(min(palette_ratios), 3),
                            "threshold_ratio": 4.5,
                            "passed": min(palette_ratios) >= 4.5,
                        },
                    },
                }
            )
        checks.append(record)
    failures = []
    for item in checks:
        if not item["nonempty"] or ("letter_portrait" in item and not item["letter_portrait"]):
            failures.append(item["path"])
            continue
        pdf_checks = item.get("pdf_checks")
        if pdf_checks is None:
            continue
        mandatory = (
            pdf_checks["parseable_page_tree"],
            pdf_checks["extractable_text"],
            pdf_checks["minimum_font_size"]["passed"],
        )
        reading_order = pdf_checks["authored_reading_order"]
        authored_size = pdf_checks["authored_content_font_size"]
        if (
            not all(mandatory)
            or reading_order["executed"] and not reading_order["passed"]
            or authored_size["executed"] and not authored_size["passed"]
        ):
            failures.append(item["path"])
    return {
        "schema_version": "0.7",
        "ok": not failures,
        "failures": failures,
        "executed_checks": {
            "file_integrity": "non-empty bytes and stable content hash for every shipped file",
            "pdf_geometry": "parseable, non-empty US-Letter portrait page tree for every printable PDF",
            "text_usability": "extractable text, OCR-layer size, and separate authored-content font size for every printable PDF",
            "authored_reading_order": "source-line or source-OCR markers remain in order in every printable rendition",
            "layout_completion": "authored layouts complete and imported overlays preserve source page geometry",
            "renderer_palette_contrast": "WCAG contrast calculation for library-rendered palettes and imported-artifact provenance marks",
        },
        "unexecuted_checks": {
            "physical_printer_test": "requires a specific printer, paper, scale, and human inspection; no print-run receipt exists",
            "imported_artifact_palette_contrast": "owned by the Artifact Forge attestation; this exporter only measures its added provenance mark",
        },
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
    dossier_by_resource = {
        item.resource_id: item
        for item in (
            game.character_program.dossiers if game.character_program else ()
        )
    }
    rendition_expectations: dict[str, dict[str, Any]] = {}
    output_files: list[PhysicalFile] = [
        PhysicalFile("source/game-release.zip", "application/zip", release.bundle_bytes, "trusted-producer")
    ]
    for resource in sorted(game.kernel.resources, key=lambda item: item.id):
        material = material_files[resource.id]
        dossier = dossier_by_resource.get(resource.id)
        if dossier is not None:
            if material.data != render_dossier_markdown(game, dossier):
                raise ValueError(f"Dossier Resource differs from Character Program: {resource.id}")
            rendered = render_dossier_pdf(game, dossier, profile)
        elif resource.media_type == "application/pdf":
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
            path=(
                f"print/dossiers/{dossier.seat_id}.pdf"
                if dossier is not None
                else f"print/resources/{resource.id}.pdf"
            ),
            media_type="application/pdf",
            data=rendered,
            audience="as-planned",
        )
        rendition_files[resource.id] = physical_file
        source_reader = PdfReader(BytesIO(material.data)) if resource.media_type == "application/pdf" else None
        rendition_expectations[physical_file.path] = {
            "renderer": "artifact-overlay" if resource.media_type == "application/pdf" else "reportlab-platypus",
            "reading_markers": _pdf_reading_markers(material.data) if resource.media_type == "application/pdf" else _reading_markers(material.data, resource.media_type),
            "ignored_text": (profile.provenance_label,),
            "source_page_boxes": (
                [
                    [float(page.mediabox.width), float(page.mediabox.height)]
                    for page in source_reader.pages
                ]
                if source_reader is not None else None
            ),
        }
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
    rendition_expectations["guides/assembly-guide.pdf"] = {
        "renderer": "reportlab-platypus",
        "reading_markers": _reading_markers(guide_md, "text/markdown"),
        "ignored_text": (profile.provenance_label,),
    }
    rendition_expectations["print/container-labels.pdf"] = {
        "renderer": "reportlab-platypus",
        "reading_markers": _label_reading_markers(plan),
        "ignored_text": (profile.provenance_label,),
    }
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
    preflight = _preflight(output_files, rendition_expectations)
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
