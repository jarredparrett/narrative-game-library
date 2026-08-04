"""Executable Stage 0 proof using only exported Verismill interfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verismill import AgentRun, Experiment, ModelConfig

from narrative_game.adapters import VerismillArtifactForge
from narrative_game.contracts import ArtifactRequest, canonical_json, digest_bytes, digest_json


UPSTREAM_COMMIT = "fca101e99e2bc3f5dd9e5376d51c97ef9606e3f3"


def _agent_run() -> AgentRun:
    parsed = {"decision": "propose", "summary": "emit the sourced deed fixture"}
    return AgentRun(
        run_id="stage0-builder-run",
        agent_id="stage0-builder",
        context_id="stage0-context",
        role="builder",
        model=ModelConfig(
            provider="fixture",
            model="recorded-human-direction",
            resolved_model="recorded-human-direction-v1",
        ),
        prompt_hash=digest_bytes(b"stage0 public artifact forge fixture"),
        input_hashes={"request": digest_bytes(b"1997 Madison deed")},
        raw_response=json.dumps(parsed, sort_keys=True),
        parsed_output=parsed,
    )


def run(root: str | Path) -> dict:
    root = Path(root)
    experiment = Experiment.create(
        root,
        request="Emit a deterministic 1997 Madison, New Jersey deed fixture",
        experiment_id="stage0_public_forge",
        clock=lambda: 1_700_000_000,
    )
    experiment.freeze_preparation(
        research={
            "sources": [
                {
                    "id": "verismill-public-facade",
                    "kind": "source_code",
                    "provenance": {
                        "repository": "jarredparrett/verismill-lean",
                        "commit": UPSTREAM_COMMIT,
                    },
                }
            ],
            "coverage": {
                "emission": "Experiment.emit_candidate",
                "materialization": "Experiment.artifact_result",
            },
        },
        rubric={
            "version": "stage0.1",
            "scorer": "absolute-v0.2",
            "dimensions": [
                {
                    "id": "public_boundary",
                    "description": "The artifact crosses only public versioned interfaces",
                    "anchors": {"0": "private dependency", "100": "public verified result"},
                }
            ],
            "acceptance": {
                "rules": [{"metric": "overall_min", "operator": ">=", "value": 0}]
            },
        },
        requirements=[
            {
                "id": "artifact.public-boundary",
                "property": "exact bytes and attestation cross the public facade",
                "failure": "downstream code needs a private Verismill or Mattermill import",
            }
        ],
    )
    builder_run = experiment.record_agent_run(_agent_run())
    request = ArtifactRequest(
        artifact_id="madison-deed-1997",
        document_class="deed_nj_1997",
        seed=1997,
        pins={
            "execution_date": "1997-10-17",
            "consideration": 425000,
            "grantor_married": True,
            "new_construction": False,
            "partial_exemption": "none",
        },
        narrative_function="Stage 0 proof of exact public artifact materialization",
        permitted_disclosures=("fixture",),
    )
    result = VerismillArtifactForge().forge(
        experiment,
        request,
        builder_run=builder_run,
        explanation={
            "observation": "the downstream boundary had no materialized fixture",
            "requirement": "artifact.public-boundary",
            "change": "emit and copy the exact artifact through the public facade",
            "evidence": f"verismill commit {UPSTREAM_COMMIT}",
        },
    )
    attestation = dict(result.attestation)
    summary = {
        "artifact_id": result.artifact_id,
        "artifact_hash": result.content_hash,
        "manifest_hash": digest_json(dict(result.manifest)),
        "request_hash": digest_json(dict(result.request)),
        "attestation_hash": digest_json(attestation),
        "bytes": len(result.document),
        "experiment_verified": attestation["verification"]["ok"],
        "measurement_status": attestation["measurement"]["status"],
        "upstream_commit": UPSTREAM_COMMIT,
    }
    (root / "stage0-result.json").write_bytes(canonical_json(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="new directory for the deterministic experiment")
    args = parser.parse_args()
    print(json.dumps(run(args.root), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
