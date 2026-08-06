"""Write the complete Winter Observatory Character Program for human review."""

from __future__ import annotations

import argparse
from pathlib import Path

from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.examples import winter_observatory_game
from narrative_game.narrative import render_dossier_markdown, validate_character_program
from narrative_game.physical import render_dossier_pdf


def run(root: str | Path) -> dict:
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Character example output root must be empty: {root}")
    dossiers = root / "dossiers"
    dossiers.mkdir(parents=True, exist_ok=True)
    game = winter_observatory_game()
    findings = validate_character_program(game, game.character_program)
    if findings:
        raise ValueError(f"Character Program is invalid: {findings}")
    outputs = []
    for dossier in game.character_program.dossiers:
        markdown = render_dossier_markdown(game, dossier)
        pdf = render_dossier_pdf(game, dossier)
        md_path = dossiers / f"{dossier.seat_id}.md"
        pdf_path = dossiers / f"{dossier.seat_id}.pdf"
        md_path.write_bytes(markdown)
        pdf_path.write_bytes(pdf)
        outputs.append({
            "seat_id": dossier.seat_id,
            "dossier_id": dossier.dossier_id,
            "markdown_hash": digest_bytes(markdown),
            "pdf_hash": digest_bytes(pdf),
        })
    (root / "game-with-character-program.json").write_bytes(canonical_json(game.to_mapping()))
    summary = {
        "schema_version": "0.14",
        "game_id": game.kernel.game_id,
        "character_program_id": game.character_program.program_id,
        "dossiers": outputs,
        "validation_findings": [],
    }
    (root / "character-example.json").write_bytes(canonical_json(summary))
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="winter-character-example")
    args = parser.parse_args(argv)
    summary = run(args.output)
    print(canonical_json(summary).decode("utf-8"))


if __name__ == "__main__":
    main()
