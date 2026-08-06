"""Prepare the exact Winter Observatory six-player human-play package."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from pypdf import PdfReader

from narrative_game.climb import (
    Authority, Dimension, FrozenInstrument, prepare_blind_trial,
)
from narrative_game.compiler import MaterialInput, compile_candidate, freeze_candidate
from narrative_game.contracts import canonical_json
from narrative_game.examples import (
    winter_observatory_game, winter_observatory_parent_game,
)
from narrative_game.experiment import CompletePackage, Experiment
from narrative_game.narrative import render_dossier_markdown
from narrative_game.physical import export_physical, verify_physical_export
from narrative_game.playtest import PlaytestProtocol
from narrative_game.playtest.program import PlaytestProgram


RUBRIC = (
    ("role_onboarding", "Time to understand the role and make a first move."),
    ("role_recall", "Recall of public identity, private truth, objectives, and boundaries."),
    ("post_exposure_agency", "Ability to remain active after the principal secret is exposed."),
    ("relationship_clarity", "Clarity and frequency of character-driven interaction."),
    ("social_agency", "Quality of bargaining, accusation, alliance, and belief revision."),
    (
        "cognitive_load",
        "Manageability of dossier length, evidence volume, and technical material.",
    ),
    ("reveal_guidance", "Whether reveal guidance is helpful, forced, or vague."),
    ("emotional_resolution", "Strength of the ending choice and emotional arc."),
    ("host_intervention", "Frequency, timing, and reason for host intervention."),
    ("enjoyment", "Enjoyment and desire to replay another role."),
)
RESPONSE_STAGES = ("pre_game", "in_play", "post_game", "group_debrief")
DEFECT_OWNERS = ("dossier", "evidence", "hosting", "pacing", "ui")


def winter_playtest_instrument() -> FrozenInstrument:
    return FrozenInstrument(
        "winter-observatory-six-player-human-play",
        "1.0.0",
        "one complete six-player game with one host",
        tuple(
            Dimension(identifier, description, 1, {
                "0": "prevented meaningful play",
                "50": "worked with material friction",
                "75": "worked independently for most participants",
                "100": "consistently clear, active, and emotionally effective",
            })
            for identifier, description in RUBRIC
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 75},
            {"metric": "role_onboarding", "operator": ">=", "value": 70},
            {"metric": "post_exposure_agency", "operator": ">=", "value": 70},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Complete facilitated investigation under human play",
            "panel_size": 1,
            "panel_lenses": ["first-order-human-experience"],
            "panel_aggregation": "median-per-dimension-v1",
            "selection_evidence_classes": ["fresh-human-play"],
        },
        ("package.verify", "dossier.depth", "access.separation"),
    )


def _child_package(parent_release_bytes: bytes):
    game = winter_observatory_game()
    parent_game = winter_observatory_parent_game()
    dossier_by_resource = {
        item.resource_id: item for item in game.character_program.dossiers
    }
    with ZipFile(BytesIO(parent_release_bytes)) as archive:
        manifest = json.loads(archive.read("release.json"))
        archived_parent = json.loads(archive.read("trusted/game.json"))
        from narrative_game.authoring import parse_game_definition

        if parse_game_definition(canonical_json(archived_parent)).content_hash != parent_game.content_hash:
            raise ValueError("parent Release is not the exact selected Candidate 6 game")
        materials = []
        for resource in game.kernel.resources:
            dossier = dossier_by_resource.get(resource.id)
            if dossier is not None:
                data = render_dossier_markdown(game, dossier)
                receipt = {
                    "kind": "character-program-render",
                    "program_id": game.character_program.program_id,
                    "parent_release_id": manifest["release_id"],
                }
            else:
                data = archive.read(f"materials/{resource.id}")
                receipt = json.loads(archive.read(f"receipts/{resource.id}.json"))
            materials.append(MaterialInput(resource.id, resource.media_type, data, receipt))
    frozen = freeze_candidate(
        game=game,
        materials=materials,
        seed=int(manifest["seed"]),
        component_lock=manifest["component_lock"],
        compilation_options=manifest["compilation_options"],
    )
    if frozen.candidate is None:
        raise ValueError(f"deep-Dossier child did not freeze: {frozen.findings}")
    compiled = compile_candidate(frozen.candidate)
    if compiled.release is None:
        raise ValueError(f"deep-Dossier child did not compile: {compiled.attempt.findings}")
    physical = export_physical(compiled.release)
    verify_physical_export(physical, compiled.release)
    trial = prepare_blind_trial(
        compiled.release,
        physical,
        cover_story="Anonymous complete facilitated investigation for experience review.",
    )
    page_counts = {
        dossier.seat_id: len(PdfReader(BytesIO(
            physical.file(f"print/dossiers/{dossier.seat_id}.pdf").data
        )).pages)
        for dossier in game.character_program.dossiers
    }
    return manifest, frozen.candidate, compiled.release, physical, trial, page_counts


def _forms(game, instrument: FrozenInstrument, protocol: PlaytestProtocol) -> dict[str, bytes]:
    phases = sorted(game.phases, key=lambda item: item.order)
    seats = sorted(game.kernel.seats, key=lambda item: item.id)
    roster = ["seat_id,character,participant_authority_id,participant_name"] + [
        f"{seat.id},{seat.label},," for seat in seats
    ]
    host_rows = ["elapsed_seconds,phase_id,category,instrument_item_id,quote,note,defect_owner"] + [
        f",{phase.id},host_intervention,host_intervention,,," for phase in phases
    ]
    pre = {
        "schema_version": "1.0",
        "response_stage": "pre_game",
        "required_for_each_seat": [item.id for item in seats],
        "items": [
            {"id": "role_onboarding.timer", "prompt": "Seconds from opening the Dossier to a stated first move", "response": "integer"},
            {"id": "role_recall.public_identity", "prompt": "State your public identity without looking", "response": "verbatim"},
            {"id": "role_recall.private_truth", "prompt": "State the private truth you must manage", "response": "verbatim-private"},
            {"id": "role_recall.objective", "prompt": "State your immediate objective", "response": "verbatim"},
            {"id": "role_recall.boundary", "prompt": "Name one fact, belief, or lie boundary", "response": "verbatim-private"},
        ],
    }
    post = {
        "schema_version": "1.0",
        "response_stage": "post_game",
        "required_for_each_seat": [item.id for item in seats],
        "items": [
            {"id": identifier, "prompt": description, "score": "0-100", "quote": "required", "note": "required"}
            for identifier, description in RUBRIC
        ],
    }
    consent = """# Human playtest consent v1\n\nI consent to participate in or facilitate this fictional game playtest. I permit the experiment to retain my role assignment, structured responses, timestamps, scores, and anonymized exact quotes. I may stop at any time. My responses are first-order human evidence and will not be rewritten as model judgments.\n\nDecision: [ ] consented  [ ] declined\nAuthority ID: ____________________\nName/signature: ____________________\nDate: ____________________\n"""
    debrief = """# Group debrief\n\nRecord exact quotes and speakers. Discuss, in order: the first move; secrets after exposure; relationship-driven exchanges; bargains and accusations; evidence load; reveal guidance; host interventions; each ending choice; enjoyment; and desire to replay. Classify every actionable defect as dossier, evidence, hosting, pacing, or UI. Do not convert a finding into a child Candidate until a human review approves an answer-safe requirement.\n"""
    guide = """# Facilitator run order\n\n1. Verify the package identities in `playtest-preparation.json`.\n2. Assign six distinct humans to the frozen Seats and one distinct host.\n3. Collect consent before distributing private Dossiers.\n4. Time the Quick Start and capture every player's pre-game responses.\n5. Open the live Session and record one timestamped host observation in every Phase.\n6. Preserve interventions as Session Events and in the host log.\n7. Complete individual post-game forms before the group debrief.\n8. Record exact quotes, scores, response files, and defect owners through `PlaytestProgram.record_run`.\n9. Treat the run as development evidence until an independent human review and required remeasurement support standing.\n"""
    return {
        "forms/consent-v1.md": consent.encode(),
        "forms/roster.csv": ("\n".join(roster) + "\n").encode(),
        "forms/facilitator-observations.csv": ("\n".join(host_rows) + "\n").encode(),
        "forms/pre-game.json": canonical_json(pre),
        "forms/post-game.json": canonical_json(post),
        "forms/group-debrief.md": debrief.encode(),
        "RUN.md": guide.encode(),
        "rubric.json": canonical_json({
            "instrument": instrument.to_mapping(),
            "response_stages": list(RESPONSE_STAGES),
            "defect_owner_taxonomy": list(DEFECT_OWNERS),
            "protocol": protocol.to_mapping(),
        }),
    }


def run(root: str | Path, parent_release: str | Path) -> dict[str, Any]:
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"playtest preparation root must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    parent_bytes = Path(parent_release).read_bytes()
    parent, candidate, release, physical, trial, page_counts = _child_package(parent_bytes)
    instrument = winter_playtest_instrument()
    experiment = Experiment.create(
        root / "experiment",
        experiment_id="winter-observatory-six-player-human-play-v1",
        profile_id="narrative.facilitated-investigation",
        profile_version="1.0.0",
        instrument=instrument,
        initial_data={
            "candidate_id": candidate.candidate_id,
            "release_id": release.release_id,
            "physical_export_id": physical.export_id,
            "status": "awaiting-human-play",
        },
        component_lock=candidate.component_lock,
        reviewer=Authority("playtest-owner", "human", "reviewer", "playtest-owner"),
    )
    binding = experiment.bind_package(
        CompletePackage(
            candidate.candidate_id, release.release_id, release.bundle_bytes,
            physical.export_id, physical.archive_bytes, trial,
            {"package.verify": True, "dossier.depth": all(3 <= item <= 5 for item in page_counts.values()), "access.separation": True},
        ),
        idempotency_key="bind-exact-deep-dossier-package",
    )
    protocol = PlaytestProgram(experiment).freeze_protocol(
        binding_id=binding.binding_id,
        name="Winter Observatory six-player dossier validation",
        version="1.0.0",
        consent_version="playtest-consent-v1",
        minimum_fresh_runs=2,
        minimum_participants_per_run=6,
        required_observation_categories=tuple(item[0] for item in RUBRIC),
        required_response_stages=RESPONSE_STAGES,
        individual_response_stages=("pre_game", "post_game"),
        require_facilitator_phase_observations=True,
        defect_owner_taxonomy=DEFECT_OWNERS,
    )
    packages = root / "packages"; packages.mkdir()
    (packages / "game-release.zip").write_bytes(release.bundle_bytes)
    (packages / "physical-package.zip").write_bytes(physical.archive_bytes)
    (packages / "blind-audit-package.zip").write_bytes(trial.archive_bytes)
    for path, data in _forms(winter_observatory_game(), instrument, protocol).items():
        target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    experiment.export_archive(root / "winter-observatory-playtest.ngw")
    summary = {
        "schema_version": "0.15",
        "status": "awaiting-six-distinct-human-players-and-one-host",
        "parent_candidate_id": parent["candidate_id"],
        "parent_release_id": parent["release_id"],
        "candidate_id": candidate.candidate_id,
        "release_id": release.release_id,
        "physical_export_id": physical.export_id,
        "blind_trial_id": trial.trial_id,
        "character_program_id": winter_observatory_game().character_program.program_id,
        "instrument_id": instrument.instrument_id,
        "protocol_id": protocol.protocol_id,
        "binding_id": binding.binding_id,
        "seed": candidate.seed,
        "dossier_page_counts": page_counts,
        "verification": experiment.verify(),
        "human_boundary": "Do not create a PlaytestRun until actual consent, Session history, responses, quotes, and scores exist.",
    }
    (root / "playtest-preparation.json").write_bytes(canonical_json(summary))
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--parent-release", required=True)
    args = parser.parse_args(argv)
    print(canonical_json(run(args.output, args.parent_release)).decode())


if __name__ == "__main__":
    main()
