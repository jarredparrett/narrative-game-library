"""Offline ingestion of one completed first-order human Playtest Run bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from narrative_game.climb import Authority
from narrative_game.contracts import canonical_json
from narrative_game.experiment import Experiment
from narrative_game.runtime import SessionHistory
from narrative_game.workspace.io import atomic_write

from .program import PlaytestProgram


def _local_path(root: Path, value: Any) -> Path:
    target = (root / str(value)).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Playtest bundle path leaves its directory: {value}")
    if not target.is_file():
        raise ValueError(f"Playtest bundle file is unavailable: {value}")
    return target


def _json_file(root: Path, value: Any) -> Any:
    return json.loads(_local_path(root, value).read_bytes())


def _authority(value: Mapping[str, Any], role: str) -> Authority:
    required = {"authority_id", "principal"}
    if not isinstance(value, Mapping) or required - set(value):
        raise ValueError(f"{role} Authority requires authority_id and principal")
    return Authority(
        str(value["authority_id"]), "human", role, str(value["principal"])
    )


def record_playtest_bundle(
    experiment_root: str | Path,
    bundle_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and atomically preflight one completed operator-owned bundle."""
    bundle_file = Path(bundle_path).resolve()
    raw = json.loads(bundle_file.read_bytes())
    if raw.get("schema_version") != "1.0":
        raise ValueError("Playtest Run bundle requires schema_version 1.0")
    root = bundle_file.parent
    participants = tuple(
        _authority(item, "participant") for item in raw.get("participants", ())
    )
    facilitator = _authority(raw.get("facilitator", {}), "facilitator")
    observers = tuple(
        _authority(item, "observer") for item in raw.get("observers", ())
    )
    consent_paths = raw.get("consent_paths", {})
    if not isinstance(consent_paths, Mapping):
        raise ValueError("consent_paths must map Authority IDs to response files")
    consents = {
        str(authority_id): _json_file(root, path)
        for authority_id, path in consent_paths.items()
    }
    observations = _json_file(root, raw["observations_path"])
    if not isinstance(observations, list) or not all(
        isinstance(item, Mapping) for item in observations
    ):
        raise ValueError("observations_path must contain a JSON array of responses")
    production = _json_file(root, raw["production_receipt_path"])
    if not isinstance(production, Mapping):
        raise ValueError("production receipt must be a JSON object")
    session = SessionHistory.from_bytes(
        _local_path(root, raw["session_history_path"]).read_bytes()
    )
    scores = raw.get("scores")
    if not isinstance(scores, Mapping):
        raise ValueError("Playtest Run bundle requires Instrument scores")
    experiment = Experiment.open(experiment_root)
    run = PlaytestProgram(experiment).record_run(
        protocol_id=str(raw["protocol_id"]),
        run_key=str(raw["run_key"]),
        session_history=session,
        production_receipt=production,
        participants=participants,
        facilitator=facilitator,
        observers=observers,
        consent_responses=consents,
        observations=tuple(dict(item) for item in observations),
        scores={str(key): int(value) for key, value in scores.items()},
        idempotency_key=str(raw["idempotency_key"]),
    )
    verification = experiment.verify()
    if not verification["ok"]:
        raise RuntimeError(f"Experiment failed verification after Run ingestion: {verification}")
    result = {
        "schema_version": "1.0",
        "experiment_id": experiment.plan.experiment_id,
        "protocol_id": run.protocol_id,
        "run_id": run.run_id,
        "run_key": run.run_key,
        "release_id": run.release_id,
        "physical_export_id": run.physical_export_id,
        "evidence_class": run.evidence_class,
        "outcome": run.outcome,
        "participant_authority_ids": list(run.participant_authority_ids),
        "verification": verification,
    }
    target = Path(output_path) if output_path is not None else root / "playtest-run-record.json"
    atomic_write(target, canonical_json(result))
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment")
    parser.add_argument("bundle")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    print(canonical_json(record_playtest_bundle(
        args.experiment, args.bundle, output_path=args.output
    )).decode())


if __name__ == "__main__":
    main()
