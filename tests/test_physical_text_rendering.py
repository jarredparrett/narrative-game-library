"""Capability tests for legible narrative text in physical packages."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from reportlab.platypus import Paragraph, Table

from narrative_game.physical import PhysicalExportProfile
from narrative_game.physical.exporter import _render_text_pdf, _text_story
from narrative_game.stage5_fixture import DEFAULT_SOURCE


def test_plain_text_renditions_wrap_inside_the_printable_frame():
    """stage7.plain-text-wrap: accessible prose wraps instead of clipping off-page."""
    story = _text_story(
        (
            "ACCESSIBLE RENDITION\n\n"
            + "A deliberately long game-relevant sentence " * 20
        ).encode(),
        "text/plain",
    )
    assert len(story) == 1
    assert isinstance(story[0], Paragraph)
    width, height = story[0].wrap(468, 1000)
    assert width == 468
    assert height > 22


def test_third_level_markdown_headings_render_without_source_markers():
    """stage7.markdown-h3: host-guide section headings render semantically."""
    rendered = _render_text_pdf(
        data=b"# Guide\n\n### Setup\n\nPut the interview in the investigation folder.\n",
        media_type="text/markdown",
        title="Guide",
        profile=PhysicalExportProfile(),
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(rendered)).pages)
    assert "Setup" in text
    assert "###" not in text


def test_representative_host_guide_has_no_orphan_tail_page():
    """stage7.host-guide-pagination: the worked guide remains one coherent print unit."""
    rendered = _render_text_pdf(
        data=(DEFAULT_SOURCE / "content" / "host-guide.md").read_bytes(),
        media_type="text/markdown",
        title="The Ashwood Ledger host guide",
        profile=PhysicalExportProfile(),
    )
    reader = PdfReader(BytesIO(rendered))
    assert len(reader.pages) == 1
    assert "Safety and provenance" in (reader.pages[0].extract_text() or "")


def test_markdown_list_markers_extract_as_plain_hyphens():
    """stage7.archive-fidelity: player-handout lists have no control glyphs."""
    rendered = _render_text_pdf(
        data=b"# Objectives\n\n1. Establish the timeline.\n2. Compare the records.\n",
        media_type="text/markdown",
        title="Objectives",
        profile=PhysicalExportProfile(),
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(rendered)).pages)
    assert "\x7f" not in text
    assert "-  Establish the timeline." in text


def test_csv_print_layout_allocates_width_to_long_evidence_columns():
    """stage7.csv-table-layout: forensic rows retain readable column structure."""
    story = _text_story(
        (
            "timestamp,zone,event,status\n"
            "1997-10-21 21:12,staff-entrance,badge read NV-04; key tag R-2 visible,admitted\n"
        ).encode(),
        "text/csv",
        available_width=504,
    )
    table = next(item for item in story if isinstance(item, Table))
    table.wrap(504, 700)
    assert sum(table._colWidths) == 504
    assert table._colWidths[2] == max(table._colWidths)
    assert table._colWidths[2] >= 190


def test_sectioned_compiled_export_preserves_source_rows_in_reading_order():
    """stage7.compiled-export-layout: multi-system records keep provenance and row order."""
    source = (
        "VALE HOUSE ARCHIVE — ENTRANCE AND PERIMETER COMPILED EXPORT\n"
        "compiled_at,1998-05-15 09:40\n"
        "compiled_by,Facilities Records Office\n\n"
        "source_system,source_record_id,timestamp,zone,observed_value,result\n"
        "STAFF-DOOR-CONTROLLER,SD-88412,1998-05-14 21:12,staff-entrance,badge NV-04 read; controller released door,admitted\n"
        "ENTRANCE-VIDEO-REVIEW,EV-19980514-2112,1998-05-14 21:12,staff-entrance,key tag R-2 visible on admitted person,logged\n\n"
        "DIRECTORY SOURCE: PERSONNEL-BADGE-DIRECTORY\n"
        "badge_id,person_name,role,directory_status\n"
        "NV-04,Noel Voss,records clerk,active\n"
    )
    rendered = _render_text_pdf(
        data=source.encode(),
        media_type="text/csv",
        title="Compiled movement export",
        profile=PhysicalExportProfile(),
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(rendered)).pages)
    normalized = " ".join(text.split())
    assert "ENTRANCE AND PERIMETER COMPILED EXPORT" in normalized
    assert normalized.index("STAFF-DOOR-CONTROLLER") < normalized.index("ENTRANCE-VIDEO-REVIEW")
    assert "DIRECTORY SOURCE: PERSONNEL-BADGE-DIRECTORY" in normalized
    assert "NV-04 Noel Voss records clerk active" in normalized


def test_joint_finding_form_keeps_signature_block_with_the_form():
    """stage7.form-pagination: a complete two-seat finding form has no orphan tail page."""
    source = """# Vale House Archive — Joint finding sheet

Complete together during Resolution, after opening the instrument envelope.

## Phase record

Opening checkpoint: We identified two named people whose recorded access could account for movement of the ledger and wrote what the Opening records leave unresolved. [ ]

Investigation checkpoint: Each investigator privately selected one fact, exchanged only the selected facts, and compared them with the shared interview. [ ]

Resolution checkpoint: We compared the recorded instrument with the earlier Quillstone records. [ ]

## Opening alternatives

Named person 1: _________________________________________________

Opening fact supporting that possibility: _________________________

Named person 2: _________________________________________________

Opening fact supporting that possibility: _________________________

Question the Opening records cannot answer: ______________________

## Joint finding

Who removed the property ledger?

________________________________________________________________

What payment was proposed?

________________________________________________________________

What packet action and timing were attached to it?

________________________________________________________________

## Required cross-seat comparison

Avery's privately selected positive fact:

________________________________________________________________

Blake's privately selected positive fact:

________________________________________________________________

Shared or third record compared with them:

________________________________________________________________

How do the records identify the person and account for access?

________________________________________________________________

How do the records connect the payment, developer, entry, and option?

________________________________________________________________

## Recorded transaction

Property address: _______________________________________________

Execution date: _________________________________________________

Stated consideration: ___________________________________________

Earlier record compared with the instrument: _____________________

Avery Shaw: ____________________    Blake Mercer: ____________________
"""
    rendered = _render_text_pdf(
        data=source.encode(),
        media_type="text/markdown",
        title="Joint finding sheet",
        profile=PhysicalExportProfile(),
    )
    reader = PdfReader(BytesIO(rendered))
    assert len(reader.pages) == 1
    assert "Blake Mercer" in (reader.pages[0].extract_text() or "")
