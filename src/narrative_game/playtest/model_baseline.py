"""Run a configured blind model panel for later human-evidence comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrative_game.climb import JsonCommandDriver
from narrative_game.contracts import canonical_json
from narrative_game.experiment import Experiment, ModelPanelMember
from narrative_game.workspace.io import atomic_write


def measure_model_baseline(
    experiment_root: str | Path,
    panel_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute and persist one frozen blind panel from an operator manifest."""
    panel_file = Path(panel_path).resolve()
    raw = json.loads(panel_file.read_bytes())
    if raw.get("schema_version") != "1.0":
        raise ValueError("Model panel manifest requires schema_version 1.0")
    member_data = raw.get("members")
    if not isinstance(member_data, list) or not member_data:
        raise ValueError("Model panel manifest requires at least one member")
    members = []
    for item in member_data:
        command = item.get("command") if isinstance(item, dict) else None
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise ValueError("every model panel member requires a command argv array")
        members.append(
            ModelPanelMember(
                str(item["authority_id"]),
                str(item["principal"]),
                str(item["requested_model"]),
                str(item["assigned_lens"]),
                JsonCommandDriver(
                    tuple(command),
                    str(item["provider"]),
                    "live-model",
                    int(item.get("timeout_seconds", 600)),
                ),
            )
        )
    experiment = Experiment.open(experiment_root)
    measured = experiment.measure_model_panel(
        binding_id=str(raw["binding_id"]),
        task_key=str(raw["task_key"]),
        members=tuple(members),
        seed=int(raw["seed"]) if raw.get("seed") is not None else None,
    )
    verification = experiment.verify()
    if not verification["ok"]:
        raise RuntimeError(
            f"Experiment failed verification after model panel: {verification}"
        )
    evaluation = measured.evaluation
    result = {
        "schema_version": "1.0",
        "experiment_id": experiment.plan.experiment_id,
        "binding_id": str(raw["binding_id"]),
        "task_id": evaluation.task_id,
        "evaluation_id": evaluation.evaluation_id,
        "instrument_id": evaluation.instrument_id,
        "judge_authority_ids": list(evaluation.judge_authority_ids),
        "model_receipt_ids": list(evaluation.model_receipt_ids),
        "scores": dict(evaluation.scores),
        "finding_ids": list(evaluation.finding_ids),
        "outcome": evaluation.outcome,
        "verification": verification,
    }
    target = (
        Path(output_path)
        if output_path is not None
        else panel_file.parent / "model-panel-record.json"
    )
    atomic_write(target, canonical_json(result))
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("panel")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    print(
        canonical_json(
            measure_model_baseline(
                args.experiment, args.panel, output_path=args.output
            )
        ).decode()
    )


if __name__ == "__main__":
    main()
