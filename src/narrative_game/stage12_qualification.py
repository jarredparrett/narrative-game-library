"""Evaluate the frozen public-release policy against one portable Experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrative_game.contracts import canonical_json
from narrative_game.experiment import Experiment
from narrative_game.release import ReleaseEvidence, qualify_public_release


def run(
    experiment_root: str | Path,
    evidence_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    evidence_file = Path(evidence_path)
    raw = json.loads(evidence_file.read_bytes())
    evidence = ReleaseEvidence.from_mapping(raw)
    objects = {
        str(ref): (evidence_file.parent / str(path)).resolve().read_bytes()
        for ref, path in raw.get("object_paths", {}).items()
    }
    report = qualify_public_release(
        Experiment.open(experiment_root), evidence, evidence_objects=objects
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json(report.to_mapping()))
    return report.to_mapping()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("evidence")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--allow-not-qualified", action="store_true",
        help="write a diagnostic report without failing the command",
    )
    args = parser.parse_args(argv)
    report = run(args.experiment, args.evidence, args.output)
    print(canonical_json(report).decode())
    if report["status"] != "qualified" and not args.allow_not_qualified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
