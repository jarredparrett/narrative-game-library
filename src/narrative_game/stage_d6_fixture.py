"""Write the deterministic Operator Evidence Monitor worked example."""

from __future__ import annotations

import argparse
from pathlib import Path

from narrative_game.contracts.canonical import canonical_json
from narrative_game.difficulty import reference_operator_projection, render_operator_html


def run(output_root: str | Path) -> dict[str, object]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    projections = {}
    for state in ("current", "incomplete", "stale", "corrupt"):
        projection = reference_operator_projection(state)
        (output / f"operator-{state}.json").write_bytes(projection.to_bytes())
        (output / f"operator-{state}.html").write_bytes(render_operator_html(projection))
        projections[state] = projection.projection_ref
    (output / "index.html").write_bytes(render_operator_html(reference_operator_projection("current")))
    manifest = {
        "schema_version": "operator-monitor-example.1",
        "entry_point": "index.html",
        "projections": projections,
    }
    (output / "manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".narrative-game/operator-monitor")
    arguments = parser.parse_args()
    result = run(arguments.output)
    print(canonical_json(result).decode("utf-8"))


if __name__ == "__main__":
    main()
