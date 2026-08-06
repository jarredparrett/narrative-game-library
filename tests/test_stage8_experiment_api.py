"""Stage 8 acceptance for the reusable, profile-neutral Experiment API."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest

from narrative_game.climb import (
    Authority,
    Dimension,
    DriverOutput,
    Finding,
    FrozenInstrument,
    Requirement,
)
from narrative_game.compiler import compile_candidate
from narrative_game.contracts import canonical_json, digest_json
from narrative_game.experiment import (
    CompletePackage,
    Experiment,
    HumanPanelMember,
    MedianPerDimension,
    ModelPanelMember,
    ProposedRevision,
)
from narrative_game.physical import export_physical
from narrative_game.playtest.model_baseline import measure_model_baseline
from narrative_game.stage5_fixture import build_worked_candidate
from narrative_game.climb import prepare_blind_trial
from narrative_game.workspace import Workspace


def instrument() -> FrozenInstrument:
    return FrozenInstrument(
        "reusable-complete-experience",
        "1.0.0",
        "anonymous-complete-trial",
        (
            Dimension(
                "quality",
                "Complete game quality",
                1,
                {"0": "broken", "60": "usable", "100": "excellent"},
            ),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 60},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Anonymous narrative game",
            "panel_size": 1,
            "panel_lenses": ["complete-experience"],
            "panel_aggregation": "median-per-dimension-v1",
            "selection_evidence_classes": ["live-model", "fresh-human"],
        },
        ("package.verify",),
    )


@pytest.fixture(scope="module")
def complete_package(tmp_path_factory) -> CompletePackage:
    root = tmp_path_factory.mktemp("stage8-package")
    build = build_worked_candidate(root / "forge")
    compilation = compile_candidate(build.candidate)
    assert compilation.release is not None
    release = compilation.release
    physical = export_physical(release)
    trial = prepare_blind_trial(
        release,
        physical,
        cover_story="Anonymous narrative game",
    )
    return CompletePackage(
        build.candidate.candidate_id,
        release.release_id,
        release.bundle_bytes,
        physical.export_id,
        physical.archive_bytes,
        trial,
        {"package.verify": True},
    )


def create_experiment(tmp_path: Path) -> Experiment:
    return Experiment.create(
        tmp_path / "workspace",
        experiment_id="stage8-capability",
        profile_id="fixture.investigation",
        profile_version="1.0.0",
        instrument=instrument(),
        initial_data={"title": "Baseline"},
        component_lock={"components": []},
        reviewer=Authority(
            "human-reviewer", "human", "reviewer", "repository-owner"
        ),
    )


class JudgeDriver:
    def __init__(self, score: int):
        self.score = score
        self.calls = 0

    def invoke(self, invocation):
        self.calls += 1
        parsed = {
            "scores": {"quality": self.score},
            "findings": [
                {
                    "requirement_code": "experience.progression",
                    "severity": "major",
                    "resource_path": "trial/cover-story.txt",
                    "locus": "cover story",
                    "quote": "Anonymous narrative game",
                    "message": "The package needs a clearer progression contract.",
                }
            ],
        }
        return DriverOutput(
            "fixture-provider",
            "fixture-judge-v1",
            "live-model",
            canonical_json(parsed),
            parsed,
        )


class BuilderDriver:
    def invoke(self, invocation):
        parsed = {
            "title": "Approved revision",
            "rationale": "Satisfies experience.progression without judge-only detail.",
        }
        return DriverOutput(
            "fixture-provider",
            "fixture-builder-v1",
            "capability-fixture",
            canonical_json(parsed),
            parsed,
        )


class FixtureProfile:
    profile_id = "fixture.investigation"
    profile_version = "1.0.0"
    component_lock = {"components": []}

    def __init__(self, package: CompletePackage):
        self.package = package

    def build(self, draft_data, *, scratch_root, instrument):
        candidate_id = digest_json(
            {
                "profile": self.profile_id,
                "version": self.profile_version,
                "draft": draft_data,
            }
        )
        return replace(self.package, candidate_id=candidate_id)

    def authoring_package(self, draft_data):
        return {"editable_game": dict(draft_data)}

    def proposal_contract(self):
        return {
            "schema_version": "0.8",
            "output": {"title": "string", "rationale": "string"},
        }

    def apply_builder_output(
        self,
        draft_data,
        parsed_output,
        *,
        requirements,
        human_direction,
        scratch_root,
        instrument,
    ):
        assert requirements
        assert set(parsed_output) == {"title", "rationale"}
        data = {**draft_data, "title": parsed_output["title"]}
        return ProposedRevision(
            data,
            parsed_output["rationale"],
            self.build(data, scratch_root=scratch_root, instrument=instrument),
        )


def translator(evaluation, findings):
    assert evaluation.outcome == "fail"
    return (
        Requirement(
            "experience.phase-accurate-progression",
            "Every required action is available in the phase where players need it.",
            "A later delivery cannot satisfy an earlier dependency.",
            "Align required actions and their inputs by phase.",
            tuple(item.finding_id for item in findings),
        ),
    )


def test_experiment_plan_persists_profile_instrument_and_archive_identity(
    tmp_path, complete_package
):
    """stage8.plan: one portable Plan binds profile identity to one Instrument."""
    experiment = create_experiment(tmp_path)
    binding = experiment.bind_package(
        complete_package, idempotency_key="bind-baseline"
    )
    assert binding.candidate_id == complete_package.candidate_id
    measured = experiment.measure_model_panel(
        binding_id=binding.binding_id,
        task_key="portable-baseline",
        members=(
            ModelPanelMember(
                "portable-judge",
                "fixture-model",
                "judge-latest",
                "complete-experience",
                JudgeDriver(70),
            ),
        ),
    )
    archive = tmp_path / "experiment.ngw"
    experiment.export_archive(archive)
    imported = Workspace.import_archive(archive, tmp_path / "imported")
    reopened = Experiment(imported)
    assert reopened.plan.profile_id == "fixture.investigation"
    assert reopened.plan.profile_version == "1.0.0"
    assert reopened.instrument.instrument_id == instrument().instrument_id
    assert reopened.ledger.get(
        "evaluation", measured.evaluation.evaluation_id
    ).value == measured.evaluation
    assert len(reopened.ledger.snapshot()["model_receipts"]) == 1
    assert reopened.verify()["ok"]


def test_operator_model_baseline_records_exact_evaluation_for_later_human_comparison(
    tmp_path, complete_package
):
    """stage11.model-baseline-cli: configured models produce a persisted blind Evaluation."""
    experiment = create_experiment(tmp_path)
    binding = experiment.bind_package(
        complete_package, idempotency_key="bind-model-baseline"
    )
    manifest = tmp_path / "model-panel.json"
    manifest.write_bytes(canonical_json({
        "schema_version": "1.0",
        "binding_id": binding.binding_id,
        "task_key": "human-comparison-baseline",
        "seed": 17,
        "members": [{
            "authority_id": "human-comparison-model-judge",
            "principal": "offline-fixture-model",
            "provider": "fixture-json-command",
            "requested_model": "fixture-model-v1",
            "assigned_lens": "complete-experience",
            "command": [
                sys.executable,
                str(Path("tests/fixtures/json_model_driver.py").resolve()),
            ],
        }],
    }))
    first = measure_model_baseline(experiment.workspace.root, manifest)
    second = measure_model_baseline(experiment.workspace.root, manifest)
    assert second == first
    assert first["outcome"] == "pass"
    assert first["scores"] == {"quality": 80}
    assert len(experiment.ledger.snapshot()["evaluations"]) == 1
    assert experiment.verify()["ok"]


def test_model_and_human_judges_are_distinct_first_order_receipts(
    tmp_path, complete_package
):
    """stage8.human-evidence: human observations are never labeled model calls."""
    experiment = create_experiment(tmp_path)
    baseline = experiment.bind_package(
        complete_package, idempotency_key="bind-baseline"
    )
    driver = JudgeDriver(50)
    model_measurement = experiment.measure_model_panel(
        binding_id=baseline.binding_id,
        task_key="model-baseline",
        members=(
            ModelPanelMember(
                "model-judge",
                "fixture-model",
                "judge-latest",
                "complete-experience",
                driver,
            ),
        ),
    )
    assert model_measurement.evaluation.model_receipt_ids
    assert model_measurement.evaluation.human_receipt_ids == ()
    assert driver.calls == 1

    child_package = replace(
        complete_package,
        candidate_id="sha256:" + "b" * 64,
    )
    child = experiment.bind_package(child_package, idempotency_key="bind-child")
    human_measurement = experiment.measure_human_panel(
        binding_id=child.binding_id,
        task_key="human-child",
        members=(
            HumanPanelMember(
                "human-judge",
                "independent-playtester",
                "complete-experience",
                {"quality": 85},
                (
                    {
                        "requirement_code": "experience.progression",
                        "severity": "minor",
                        "resource_path": "trial/cover-story.txt",
                        "locus": "cover story",
                        "quote": "Anonymous narrative game",
                        "message": "Progression is understandable after the revision.",
                    },
                ),
            ),
        ),
    )
    assert human_measurement.evaluation.model_receipt_ids == ()
    assert human_measurement.evaluation.human_receipt_ids
    decision = experiment.select(
        baseline_evaluation_id=model_measurement.evaluation.evaluation_id,
        child_evaluation_id=human_measurement.evaluation.evaluation_id,
    )
    assert decision.outcome == "select_child"
    assert experiment.ledger.snapshot()["standings"] == ()
    assert experiment.verify()["ok"]


def test_profile_adapter_builds_answer_safe_proposal_but_human_moves_branch(
    tmp_path, complete_package
):
    """stage8.profile-adapter: domain revision is inert until exact human approval."""
    experiment = create_experiment(tmp_path)
    baseline = experiment.bind_package(
        complete_package, idempotency_key="bind-baseline"
    )
    measured = experiment.measure_model_panel(
        binding_id=baseline.binding_id,
        task_key="failed-baseline",
        members=(
            ModelPanelMember(
                "fresh-judge",
                "fixture-judge",
                "judge-latest",
                "complete-experience",
                JudgeDriver(50),
            ),
        ),
    )
    original_head = experiment.current_draft_ref
    profile = FixtureProfile(complete_package)
    prepared = experiment.propose_revision(
        profile,
        evaluation_id=measured.evaluation.evaluation_id,
        translator=translator,
        task_key="repair-baseline",
        authority_id="fresh-builder",
        principal="fixture-builder",
        requested_model="builder-latest",
        driver=BuilderDriver(),
        scratch_root=tmp_path / "scratch",
        human_direction="Preserve the core answer while making progression usable.",
    )
    assert experiment.current_draft_ref == original_head
    review = experiment.review_proposal(
        proposal_id=prepared.proposal.proposal_id,
        reviewer_authority_id="human-reviewer",
        decision="approved",
        reason="The proposed direction is approved for remeasurement.",
    )
    transition = experiment.apply_review(
        profile,
        proposal_id=prepared.proposal.proposal_id,
        review_id=review.review_id,
        idempotency_key="apply-approved-revision",
    )
    assert transition.parent_draft_ref == original_head
    assert experiment.current_draft_data["title"] == "Approved revision"
    rebound_package, rebound = experiment.build_and_bind(
        profile,
        scratch_root=tmp_path / "rebuild",
        idempotency_key="bind-approved-child",
    )
    assert rebound.candidate_id == rebound_package.candidate_id
    assert experiment.verify()["ok"]


def test_frozen_aggregation_and_profile_identity_cannot_be_swapped(
    tmp_path, complete_package
):
    """stage8.frozen-strategy: alternate strategies require a differently identified plan."""
    experiment = create_experiment(tmp_path)
    binding = experiment.bind_package(
        complete_package, idempotency_key="bind-baseline"
    )

    class MeanAggregator:
        algorithm_id = "mean-per-dimension-v1"

        def aggregate(self, dimension_ids, observations):
            return MedianPerDimension().aggregate(dimension_ids, observations)

    with pytest.raises(ValueError, match="aggregator differs"):
        experiment.measure_model_panel(
            binding_id=binding.binding_id,
            task_key="wrong-aggregation",
            members=(
                ModelPanelMember(
                    "judge-wrong-aggregation",
                    "fixture",
                    "judge",
                    "complete-experience",
                    JudgeDriver(70),
                ),
            ),
            aggregator=MeanAggregator(),
        )
    wrong_profile = FixtureProfile(complete_package)
    wrong_profile.profile_version = "2.0.0"
    with pytest.raises(ValueError, match="identity differs"):
        experiment.require_profile(wrong_profile)


def test_public_experiment_api_has_no_ashwood_or_stage_fixture_dependency():
    """stage8.fixture-independence: reusable orchestration imports no worked fixture."""
    source = Path("src/narrative_game/experiment/api.py").read_text()
    assert "stage5_fixture" not in source
    assert "stage6_fixture" not in source
    assert "stage7_experiment" not in source
    assert "Ashwood" not in source
