"""Stage 10 acceptance for first-order human-play evidence and standing."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from narrative_game.climb import (
    Authority,
    Dimension,
    DriverOutput,
    Evaluation,
    Exposure,
    FrozenInstrument,
    Requirement,
    Task,
    TrialBinding,
)
from narrative_game.climb.ledger import ClimbRejected
from narrative_game.compiler import compile_candidate
from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.experiment import Experiment, ProposedRevision
from narrative_game.examples import vanished_ledger_blueprint
from narrative_game.playtest.program import PlaytestProgram
from narrative_game.playtest.ingestion import record_playtest_bundle
from narrative_game.profiles import FacilitatedInvestigationAuthoringAdapter
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    SessionCommand,
    ViewerGrant,
    apply_command,
    create_session,
)
from narrative_game.stage3_fixture import build_micro_candidate
from narrative_game.workspace import Workspace


GAME_JSON = Path("fixtures/micro-game/game.json").read_bytes()


def instrument() -> FrozenInstrument:
    return FrozenInstrument(
        "human-play-quality",
        "1.0.0",
        "complete facilitated play",
        (
            Dimension("world_realism", "The represented world holds under play.", 1, {"0": "breaks", "100": "holds"}),
            Dimension("playability", "Players can act, infer, recover, and resolve.", 1, {"0": "blocked", "100": "resilient"}),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 75},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Anonymous facilitated investigation",
            "panel_size": 1,
            "panel_lenses": ["complete-experience"],
            "panel_aggregation": "median-per-dimension-v1",
            "selection_evidence_classes": ["live-model"],
        },
        ("package.verify",),
    )


def complete_session(release, *, prefix: str):
    bindings = (
        ActorBinding(f"{prefix}-binding-a", Actor(f"{prefix}-actor-a", "human", "Player A"), "avery", 1),
        ActorBinding(f"{prefix}-binding-b", Actor(f"{prefix}-actor-b", "human", "Player B"), "blake", 1),
    )
    history = create_session(
        release=release,
        session_id=f"{prefix}-session",
        mode="live",
        bindings=bindings,
        viewers=(ViewerGrant(f"{prefix}-host", "host"),),
    )
    host = AuthorizationContext("viewer", f"{prefix}-host")
    avery = AuthorizationContext("actor", f"{prefix}-actor-a", f"{prefix}-binding-a")

    def accept(command_id: str, action: str, payload: dict, authority):
        nonlocal history
        result = apply_command(
            release,
            history,
            SessionCommand(
                f"{prefix}-{command_id}",
                history.session_id,
                release.release_id,
                history.sequence,
                action,
                payload,
            ),
            authority,
        )
        assert result.receipt.accepted, result.receipt.trusted_reason
        history = result.history
        return result

    accept("open", "open-session", {}, host)
    accept("phase", "advance-phase", {"phase_id": "resolution"}, host)
    accept(
        "receipt",
        "disclose-resource",
        {
            "resource_id": "cash-receipt",
            "audience_seat_ids": ["avery"],
            "evidence_grade": "host-witnessed",
        },
        host,
    )
    submission = accept(
        "submit",
        "submit-resolution",
        {"hypothesis_id": "inside-job", "proof_path_id": "key-and-payment"},
        avery,
    )
    accept(
        "resolve",
        "record-resolution",
        {"submission_sequence": submission.events[0].sequence},
        host,
    )
    return history


def prepared_experiment(tmp_path: Path):
    candidate = build_micro_candidate(GAME_JSON)
    compilation = compile_candidate(candidate)
    assert compilation.release is not None
    release = compilation.release
    experiment = Experiment.create(
        tmp_path / "experiment",
        experiment_id="stage10-playtest",
        profile_id="fixture.facilitated-investigation",
        profile_version="1.0.0",
        instrument=instrument(),
        initial_data={"title": "Human play evidence fixture"},
        component_lock={"components": []},
        reviewer=Authority("owner", "human", "reviewer", "game-owner"),
    )
    release_ref = experiment.workspace.store.put_bytes(release.bundle_bytes)
    physical_ref = experiment.workspace.store.put_bytes(b"exact physical package")
    blind_ref = experiment.workspace.store.put_bytes(b"exact blind trial")
    binding = TrialBinding(
        candidate.candidate_id,
        release.release_id,
        release_ref,
        digest_bytes(b"physical-export-id"),
        physical_ref,
        digest_bytes(b"blind-trial-id"),
        blind_ref,
        {"package.verify": True},
    )
    experiment.ledger.register(binding, actor="system:fixture", idempotency_key="binding")
    judge = Authority("model-judge", "agent", "judge", "independent-model")
    experiment.ledger.register(judge, actor="human:operator", idempotency_key="model-judge")
    task = Task(
        "model-baseline",
        "blind-measure",
        candidate.candidate_id,
        instrument().instrument_id,
        judge.authority_id,
        (),
        {"blind_trial": blind_ref},
        "Judge the anonymous complete package.",
    )
    experiment.ledger.register(task, actor="human:operator", idempotency_key="model-task")
    experiment.ledger.register(
        Exposure(judge.authority_id, blind_ref, "blind-trial", "blind measurement", task.task_id),
        actor="system:exposure-recorder",
        idempotency_key="model-exposure",
    )
    receipt = experiment.ledger.record_model_invocation(
        authority_id=judge.authority_id,
        provider="fixture",
        requested_model="judge-v1",
        resolved_model="judge-v1-pinned",
        role="judge",
        prompt_hash=digest_bytes(b"prompt"),
        context_hash=digest_bytes(b"context"),
        tool_contract_hash=digest_bytes(b"contract"),
        input_hashes={"blind_trial": blind_ref},
        tool_receipt_hashes=(),
        raw_output=canonical_json({"scores": {"world_realism": 60, "playability": 60}}),
        parsed_output={"scores": {"world_realism": 60, "playability": 60}},
        seed=10,
        evidence_class="live-model",
        actor="agent:model-judge",
        idempotency_key="model-receipt",
    ).value
    evaluation = Evaluation(
        task.task_id,
        candidate.candidate_id,
        instrument().instrument_id,
        "blind",
        (judge.authority_id,),
        (receipt.receipt_id,),
        {"world_realism": 60, "playability": 60},
        (),
        {"package.verify": True},
        "fail",
    )
    experiment.ledger.register(evaluation, actor="system:panel", idempotency_key="model-evaluation")
    return experiment, binding, release, evaluation


def authorities(prefix: str):
    participants = (
        Authority(f"{prefix}-participant-a", "human", "participant", f"{prefix}-actor-a"),
        Authority(f"{prefix}-participant-b", "human", "participant", f"{prefix}-actor-b"),
    )
    facilitator = Authority(f"{prefix}-facilitator", "human", "facilitator", f"{prefix}-host")
    observer = Authority(f"{prefix}-observer", "human", "observer", f"{prefix}-observer-person")
    return participants, facilitator, (observer,)


def consent_for(participants, facilitator, observers):
    result = {}
    for authority in (*participants, facilitator, *observers):
        scopes = ["record-observations", "retain-anonymized-quotes"]
        if authority.role == "participant":
            scopes.append("participate")
        result[authority.authority_id] = {
            "decision": "consented",
            "consent_version": "playtest-consent-v1",
            "scopes": scopes,
        }
    return result


def observations(prefix: str):
    return (
        {
            "authority_id": f"{prefix}-participant-a",
            "observer_role": "participant",
            "phase_id": "opening",
            "category": "comprehension",
            "quote": "I understood the key record but not why the interview arrived immediately.",
            "note": "The opening evidence order made the intended question too obvious.",
            "finding": {
                "requirement_code": "play.progressive-disclosure",
                "severity": "major",
                "resource_path": "trial/materials/closing-interview",
                "locus": "opening delivery",
                "quote": "interview arrived immediately",
                "message": "The corroborating interview collapses the competing theory too early.",
            },
        },
        {
            "authority_id": f"{prefix}-participant-b",
            "observer_role": "participant",
            "phase_id": "resolution",
            "category": "agency",
            "quote": "My camera evidence changed which theory the group trusted.",
            "note": "The second Seat had a distinct and consequential contribution.",
        },
        {
            "authority_id": f"{prefix}-observer",
            "observer_role": "observer",
            "phase_id": "resolution",
            "category": "pacing",
            "quote": "The group resolved after comparing two independent records.",
            "note": "The resolution phase supported collaborative inference.",
        },
    )


def record_passing_run(program, protocol, binding, release, prefix, scores):
    participants, facilitator, observers = authorities(prefix)
    return program.record_run(
        protocol_id=protocol.protocol_id,
        run_key=prefix,
        session_history=complete_session(release, prefix=prefix),
        production_receipt={
            "release_id": binding.release_id,
            "physical_export_id": binding.physical_export_id,
            "prepared_copy_count": 2,
        },
        participants=participants,
        facilitator=facilitator,
        observers=observers,
        consent_responses=consent_for(participants, facilitator, observers),
        observations=observations(prefix),
        scores=scores,
        idempotency_key=f"run-{prefix}",
    )


def test_closed_run_preflight_rejects_without_partial_lineage_or_objects(tmp_path):
    """stage11.human-ingest-atomicity: a rejected Run leaves no partial evidence."""
    experiment, binding, release, _ = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="atomic human trace",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    participants, facilitator, observers = authorities("atomic")
    invalid = list(observations("atomic"))
    invalid[0] = {**invalid[0], "observer_role": "observer"}
    before_snapshot = experiment.ledger.snapshot()
    before_objects = experiment.workspace.store.references()
    before_heads = dict(experiment.workspace.manifest["journal_heads"])
    with pytest.raises(ClimbRejected):
        program.record_run(
            protocol_id=protocol.protocol_id,
            run_key="atomic",
            session_history=complete_session(release, prefix="atomic"),
            production_receipt={
                "release_id": binding.release_id,
                "physical_export_id": binding.physical_export_id,
            },
            participants=participants,
            facilitator=facilitator,
            observers=observers,
            consent_responses=consent_for(participants, facilitator, observers),
            observations=tuple(invalid),
            scores={"world_realism": 84, "playability": 82},
            idempotency_key="atomic-run",
        )
    assert experiment.ledger.snapshot() == before_snapshot
    assert experiment.workspace.store.references() == before_objects
    assert experiment.workspace.manifest["journal_heads"] == before_heads
    assert experiment.verify()["ok"]


def test_operator_bundle_records_and_verifies_exact_run_idempotently(tmp_path):
    """stage11.human-ingest-cli: completed files enter the exact Experiment offline."""
    experiment, binding, release, _ = prepared_experiment(tmp_path)
    protocol = PlaytestProgram(experiment).freeze_protocol(
        binding_id=binding.binding_id,
        name="operator bundle",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    participants, facilitator, observers = authorities("bundle")
    bundle = tmp_path / "bundle"
    completed = bundle / "completed"
    completed.mkdir(parents=True)
    (completed / "session-history.json").write_bytes(
        complete_session(release, prefix="bundle").to_bytes()
    )
    (completed / "production.json").write_bytes(canonical_json({
        "release_id": binding.release_id,
        "physical_export_id": binding.physical_export_id,
        "prepared_copy_count": 2,
    }))
    consent_paths = {}
    for authority_id, response in consent_for(
        participants, facilitator, observers
    ).items():
        path = f"completed/consent-{authority_id}.json"
        (bundle / path).write_bytes(canonical_json(response))
        consent_paths[authority_id] = path
    (completed / "observations.json").write_bytes(
        canonical_json(list(observations("bundle")))
    )
    manifest = {
        "schema_version": "1.0",
        "protocol_id": protocol.protocol_id,
        "run_key": "bundle-cohort",
        "idempotency_key": "bundle-cohort-run",
        "session_history_path": "completed/session-history.json",
        "production_receipt_path": "completed/production.json",
        "participants": [
            {"authority_id": item.authority_id, "principal": item.principal}
            for item in participants
        ],
        "facilitator": {
            "authority_id": facilitator.authority_id,
            "principal": facilitator.principal,
        },
        "observers": [
            {"authority_id": item.authority_id, "principal": item.principal}
            for item in observers
        ],
        "consent_paths": consent_paths,
        "observations_path": "completed/observations.json",
        "scores": {"world_realism": 84, "playability": 82},
    }
    manifest_path = bundle / "recording-manifest.json"
    manifest_path.write_bytes(canonical_json(manifest))
    first = record_playtest_bundle(experiment.workspace.root, manifest_path)
    second = record_playtest_bundle(experiment.workspace.root, manifest_path)
    assert first == second
    assert first["evidence_class"] == "fresh-human-play"
    assert first["outcome"] == "pass"
    assert (bundle / "playtest-run-record.json").read_bytes() == canonical_json(first)
    reopened = Experiment.open(experiment.workspace.root)
    assert len(reopened.ledger.snapshot()["playtest_runs"]) == 1
    assert reopened.verify()["ok"]


def test_playtest_run_binds_live_session_package_roles_consent_and_observations(tmp_path):
    """stage10.first-order-run: human play binds exact production, roles, consent, and responses."""
    experiment, binding, release, _ = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="two-seat facilitated play",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    run = record_passing_run(
        program,
        protocol,
        binding,
        release,
        "run-one",
        {"world_realism": 84, "playability": 82},
    )
    assert run.outcome == "pass"
    assert run.evidence_class == "fresh-human-play"
    assert len(run.consents) == 4
    assert {item.category for item in run.observations} == {"comprehension", "agency", "pacing"}
    assert experiment.verify()["ok"]


def test_strict_protocol_requires_individual_stages_and_timestamped_facilitation(tmp_path):
    """stage11.human-boundary: a rich Run cannot omit pre/post responses or phase notes."""
    experiment, binding, release, _ = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="strict human trace",
        version="1.0.0",
        consent_version="playtest-consent-v1",
        required_observation_categories=("comprehension", "agency", "pacing"),
        required_response_stages=("pre_game", "in_play", "post_game", "group_debrief"),
        individual_response_stages=("pre_game", "post_game"),
        require_facilitator_phase_observations=True,
        defect_owner_taxonomy=("dossier", "evidence", "hosting", "pacing", "ui"),
    )
    participants, facilitator, observers = authorities("strict")
    enriched = tuple(
        {
            **item,
            "response_stage": "in_play",
            "elapsed_seconds": 10 + index,
            "instrument_item_id": item["category"],
            **({"defect_owner": "pacing"} if item.get("finding") else {}),
        }
        for index, item in enumerate(observations("strict"))
    )
    extras = tuple(
        {
            "authority_id": participant.authority_id,
            "observer_role": "participant",
            "phase_id": phase,
            "category": "comprehension" if stage == "pre_game" else "agency",
            "quote": f"Exact {stage} response from {participant.authority_id}.",
            "note": "Required individual response.",
            "response_stage": stage,
            "instrument_item_id": f"{stage}.required",
        }
        for participant in participants
        for stage, phase in (("pre_game", "opening"), ("post_game", "resolution"))
    ) + (
        {
            "authority_id": facilitator.authority_id,
            "observer_role": "facilitator",
            "phase_id": "opening",
            "category": "pacing",
            "quote": "Opening observed.",
            "note": "Timestamped host note.",
            "response_stage": "in_play",
            "elapsed_seconds": 0,
            "instrument_item_id": "host.opening",
        },
        {
            "authority_id": facilitator.authority_id,
            "observer_role": "facilitator",
            "phase_id": "resolution",
            "category": "pacing",
            "quote": "Resolution observed.",
            "note": "Timestamped host note.",
            "response_stage": "in_play",
            "elapsed_seconds": 60,
            "instrument_item_id": "host.resolution",
        },
        {
            "authority_id": observers[0].authority_id,
            "observer_role": "observer",
            "phase_id": "resolution",
            "category": "agency",
            "quote": "The group compared their experiences.",
            "note": "Group debrief response.",
            "response_stage": "group_debrief",
            "instrument_item_id": "debrief.agency",
        },
    )
    run = program.record_run(
        protocol_id=protocol.protocol_id,
        run_key="strict",
        session_history=complete_session(release, prefix="strict"),
        production_receipt={"release_id": binding.release_id, "physical_export_id": binding.physical_export_id},
        participants=participants,
        facilitator=facilitator,
        observers=observers,
        consent_responses=consent_for(participants, facilitator, observers),
        observations=(*enriched, *extras),
        scores={"world_realism": 84, "playability": 82},
        idempotency_key="strict-run",
    )
    assert run.evidence_class == "fresh-human-play"
    assert experiment.verify()["ok"]


def test_playtest_findings_translate_to_answer_safe_requirements(tmp_path):
    """stage10.harvest: quoted human play tells become attributable builder Requirements."""
    experiment, binding, release, _ = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="two-seat facilitated play",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    run = record_passing_run(program, protocol, binding, release, "run-one", {"world_realism": 84, "playability": 82})

    def translate(current, findings):
        assert current.run_id == run.run_id
        return (
            Requirement(
                "play.preserve-progressive-disclosure",
                "Corroboration becomes available only after players test competing theories.",
                "Opening delivery can collapse the investigation before meaningful play.",
                "Move decisive corroboration later without naming the observed file or quote.",
                tuple(item.finding_id for item in findings),
            ),
        )

    requirements = program.translate_requirements(run_id=run.run_id, translator=translate)
    assert requirements[0].source_finding_ids == run.finding_ids
    assert "interview arrived immediately" not in requirements[0].builder_brief

    package_instrument = FrozenInstrument(
        "authoring-preview",
        "1.0.0",
        "anonymous game package",
        (Dimension("quality", "Package quality", 1, {"0": "broken", "100": "excellent"}),),
        ({"metric": "overall", "operator": ">=", "value": 0},),
        {"cover_story": "Anonymous investigation"},
        ("authoring.valid", "compiler.valid", "physical.valid", "blind.valid"),
    )
    source_package = FacilitatedInvestigationAuthoringAdapter().build(
        vanished_ledger_blueprint().to_mapping(),
        scratch_root=tmp_path / "package",
        instrument=package_instrument,
    )
    preview = replace(
        source_package,
        candidate_id=digest_bytes(b"human-play-revised-candidate"),
        hard_gate_results={"package.verify": True},
    )

    class FixtureProfile:
        profile_id = "fixture.facilitated-investigation"
        profile_version = "1.0.0"
        component_lock = {"components": []}

        def authoring_package(self, draft_data):
            return {"editable_game": dict(draft_data)}

        def proposal_contract(self):
            return {"schema_version": "0.10", "title": "string", "rationale": "string"}

        def apply_builder_output(self, draft_data, parsed_output, **kwargs):
            assert kwargs["requirements"] == requirements
            return ProposedRevision(
                {**draft_data, "title": parsed_output["title"]},
                parsed_output["rationale"],
                preview,
            )

    class Builder:
        def invoke(self, invocation):
            parsed = {
                "title": "Human-play-directed revision",
                "rationale": "Apply the answer-safe progressive-disclosure Requirement.",
            }
            return DriverOutput("fixture", "builder-v1", "capability-fixture", canonical_json(parsed), parsed)

    original = experiment.current_draft_ref
    prepared = experiment.propose_revision_from_requirements(
        FixtureProfile(),
        binding_id=binding.binding_id,
        requirement_ids=tuple(item.requirement_id for item in requirements),
        task_key="repair-from-human-play",
        authority_id="human-play-builder",
        principal="builder-model",
        requested_model="builder-v1",
        driver=Builder(),
        scratch_root=tmp_path / "preview",
        human_direction="Preserve the answer and restore progressive disclosure.",
    )
    assert experiment.current_draft_ref == original
    assert prepared.proposal.requirement_ids == tuple(
        item.requirement_id for item in requirements
    )
    assert experiment.verify()["ok"]


def test_two_fresh_runs_and_independent_review_can_support_accepted_standing(tmp_path):
    """stage10.standing: accepted Standing requires passing fresh cohorts and independent review."""
    experiment, binding, release, model_evaluation = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="two-seat facilitated play",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    first = record_passing_run(program, protocol, binding, release, "run-one", {"world_realism": 84, "playability": 82})
    second = record_passing_run(program, protocol, binding, release, "run-two", {"world_realism": 88, "playability": 86})
    comparison = program.compare_with_model(
        protocol_id=protocol.protocol_id,
        model_evaluation_id=model_evaluation.evaluation_id,
        playtest_run_ids=(first.run_id, second.run_id),
    )
    assert comparison.conclusion == "divergent"
    standing = program.issue_accepted_standing(
        comparison_id=comparison.comparison_id,
        reviewer=Authority("independent-reviewer", "human", "publisher", "release-reviewer"),
        statement="Accepted for this exact package after two fresh passing human runs; model divergence remains recorded.",
    )
    assert standing.level == "accepted"
    assert standing.playtest_run_ids == (first.run_id, second.run_id)
    assert experiment.verify()["ok"]


def test_simulation_reused_cohort_and_participant_reviewer_cannot_claim_fresh_standing(tmp_path):
    """stage10.freshness: simulations, reused cohorts, and interested reviewers are rejected."""
    experiment, binding, release, model_evaluation = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="two-seat facilitated play",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    with pytest.raises(ValueError, match="at least one Playtest Run"):
        program.compare_with_model(
            protocol_id=protocol.protocol_id,
            model_evaluation_id=model_evaluation.evaluation_id,
            playtest_run_ids=(),
        )
    simulation_participants, simulation_facilitator, simulation_observers = authorities("simulation")
    with pytest.raises(ValueError, match="live Session"):
        program.record_run(
            protocol_id=protocol.protocol_id,
            run_key="simulation",
            session_history=replace(
                complete_session(release, prefix="simulation"), mode="simulation"
            ),
            production_receipt={"release_id": binding.release_id, "physical_export_id": binding.physical_export_id},
            participants=simulation_participants,
            facilitator=simulation_facilitator,
            observers=simulation_observers,
            consent_responses=consent_for(simulation_participants, simulation_facilitator, simulation_observers),
            observations=observations("simulation"),
            scores={"world_realism": 90, "playability": 90},
            idempotency_key="simulation",
        )
    first = record_passing_run(program, protocol, binding, release, "run-one", {"world_realism": 84, "playability": 82})
    participants, facilitator, observers = authorities("run-one")
    with pytest.raises(ClimbRejected, match="reused-playtest-cohort"):
        program.record_run(
            protocol_id=protocol.protocol_id,
            run_key="copied-run",
            session_history=complete_session(release, prefix="run-one"),
            production_receipt={"release_id": binding.release_id, "physical_export_id": binding.physical_export_id},
            participants=participants,
            facilitator=facilitator,
            observers=observers,
            consent_responses=consent_for(participants, facilitator, observers),
            observations=observations("run-one"),
            scores={"world_realism": 84, "playability": 82},
            idempotency_key="copied-run",
        )
    second = record_passing_run(program, protocol, binding, release, "run-two", {"world_realism": 88, "playability": 86})
    comparison = program.compare_with_model(
        protocol_id=protocol.protocol_id,
        model_evaluation_id=model_evaluation.evaluation_id,
        playtest_run_ids=(first.run_id, second.run_id),
    )
    with pytest.raises(ClimbRejected, match="nonindependent-standing-review"):
        program.issue_accepted_standing(
            comparison_id=comparison.comparison_id,
            reviewer=participants[0],
            statement="A participant cannot review their own Standing.",
        )


def test_human_play_archive_is_identical_across_processes(tmp_path):
    """stage10.cross-process: exact play evidence and Standing have stable identities."""
    script = """
from pathlib import Path
import runpy
import sys
from narrative_game.climb import Authority
from narrative_game.contracts import digest_bytes
from narrative_game.playtest.program import PlaytestProgram

fixture = runpy.run_path('tests/test_stage10_playtest.py')
root = Path(sys.argv[1])
experiment, binding, release, model_evaluation = fixture['prepared_experiment'](root)
program = PlaytestProgram(experiment)
protocol = program.freeze_protocol(
    binding_id=binding.binding_id,
    name='two-seat facilitated play',
    version='1.0.0',
    consent_version='playtest-consent-v1',
)
first = fixture['record_passing_run'](
    program, protocol, binding, release, 'run-one',
    {'world_realism': 84, 'playability': 82},
)
second = fixture['record_passing_run'](
    program, protocol, binding, release, 'run-two',
    {'world_realism': 88, 'playability': 86},
)
comparison = program.compare_with_model(
    protocol_id=protocol.protocol_id,
    model_evaluation_id=model_evaluation.evaluation_id,
    playtest_run_ids=(first.run_id, second.run_id),
)
program.issue_accepted_standing(
    comparison_id=comparison.comparison_id,
    reviewer=Authority('independent-reviewer', 'human', 'publisher', 'release-reviewer'),
    statement='Accepted for the exact tested package.',
)
archive = root / 'playtest.ngw'
experiment.export_archive(archive)
print(digest_bytes(archive.read_bytes()))
"""
    outputs = []
    for index, hash_seed in enumerate(("1", "987654")):
        environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
        outputs.append(
            subprocess.check_output(
                [sys.executable, "-c", script, str(tmp_path / f"process-{index}")],
                cwd=Path.cwd(),
                env=environment,
            )
        )
    assert outputs[0] == outputs[1]


def test_human_play_evidence_survives_portable_archive_replay(tmp_path):
    """stage10.portability: Runs, responses, comparison, and Standing survive relocation."""
    experiment, binding, release, model_evaluation = prepared_experiment(tmp_path)
    program = PlaytestProgram(experiment)
    protocol = program.freeze_protocol(
        binding_id=binding.binding_id,
        name="two-seat facilitated play",
        version="1.0.0",
        consent_version="playtest-consent-v1",
    )
    first = record_passing_run(program, protocol, binding, release, "run-one", {"world_realism": 84, "playability": 82})
    second = record_passing_run(program, protocol, binding, release, "run-two", {"world_realism": 88, "playability": 86})
    comparison = program.compare_with_model(
        protocol_id=protocol.protocol_id,
        model_evaluation_id=model_evaluation.evaluation_id,
        playtest_run_ids=(first.run_id, second.run_id),
    )
    standing = program.issue_accepted_standing(
        comparison_id=comparison.comparison_id,
        reviewer=Authority("independent-reviewer", "human", "publisher", "release-reviewer"),
        statement="Accepted for the exact tested package.",
    )
    archive = tmp_path / "playtest.ngw"
    experiment.export_archive(archive)
    imported = Workspace.import_archive(archive, tmp_path / "imported")
    reopened = Experiment(imported)
    assert reopened.ledger.get("playtest_run", first.run_id).value == first
    assert reopened.ledger.get("evidence_comparison", comparison.comparison_id).value == comparison
    assert reopened.ledger.get("standing", standing.attestation_id).value == standing
    assert reopened.verify()["ok"]
