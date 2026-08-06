"""Finalize model-human comparison and accepted Standing after independent review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrative_game.climb import Authority
from narrative_game.contracts import canonical_json
from narrative_game.experiment import Experiment
from narrative_game.workspace.io import atomic_write

from .program import PlaytestProgram


def finalize_review(
    experiment_root: str | Path,
    review_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist one approved independent review over exact model and Run evidence."""
    review_file = Path(review_path).resolve()
    raw = json.loads(review_file.read_bytes())
    if raw.get("schema_version") != "1.0":
        raise ValueError("Standing review requires schema_version 1.0")
    if raw.get("decision") != "approved":
        raise ValueError(
            "Accepted Standing requires an explicit approved decision; retain a "
            "non-approved review as feedback and revise before retrying"
        )
    reviewer_data = raw.get("reviewer")
    if not isinstance(reviewer_data, dict) or set(reviewer_data) != {
        "authority_id",
        "principal",
    }:
        raise ValueError("Standing review requires an exact reviewer Authority")
    run_ids = raw.get("playtest_run_ids")
    if not isinstance(run_ids, list) or not run_ids:
        raise ValueError("Standing review requires exact Playtest Run IDs")
    reviewer = Authority(
        str(reviewer_data["authority_id"]),
        "human",
        "reviewer",
        str(reviewer_data["principal"]),
    )
    experiment = Experiment.open(experiment_root)
    comparison, standing = PlaytestProgram(experiment).finalize_accepted_standing(
        protocol_id=str(raw["protocol_id"]),
        model_evaluation_id=str(raw["model_evaluation_id"]),
        playtest_run_ids=tuple(str(item) for item in run_ids),
        reviewer=reviewer,
        statement=str(raw["statement"]),
    )
    verification = experiment.verify()
    if not verification["ok"]:
        raise RuntimeError(
            f"Experiment failed verification after Standing review: {verification}"
        )
    result = {
        "schema_version": "1.0",
        "experiment_id": experiment.plan.experiment_id,
        "protocol_id": comparison.protocol_id,
        "comparison_id": comparison.comparison_id,
        "comparison_conclusion": comparison.conclusion,
        "playtest_run_ids": list(comparison.playtest_run_ids),
        "reviewer_authority_id": reviewer.authority_id,
        "standing_attestation_id": standing.attestation_id,
        "standing_level": standing.level,
        "verification": verification,
    }
    target = (
        Path(output_path)
        if output_path is not None
        else review_file.parent / "standing-review-record.json"
    )
    atomic_write(target, canonical_json(result))
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("review")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    print(
        canonical_json(
            finalize_review(args.experiment, args.review, output_path=args.output)
        ).decode()
    )


if __name__ == "__main__":
    main()
