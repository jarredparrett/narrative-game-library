"""Public, profile-neutral orchestration for human-triggered quality climbs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Protocol

from narrative_game.climb import (
    Authority,
    BlindTrial,
    ClimbLedger,
    Evaluation,
    ExperimentPlan,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReview,
    InvocationAttachment,
    ModelDriver,
    ModelExecution,
    ModelInvocation,
    Proposal,
    Requirement,
    SelectionDecision,
    Task,
    TrialBinding,
    Transition,
    decide_selection,
    execute_model_task,
    execute_model_tasks_concurrently,
    load_blind_trial,
    verify_blind_trial,
    verify_trial_quote,
)
from narrative_game.climb.selection import evaluation_passes
from narrative_game.contracts import canonical_json
from narrative_game.workspace import Workspace
from .efficiency import EfficiencyController
from .standing import ExperimentSpine


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class CompletePackage:
    """One Candidate's complete immutable measurement package."""

    candidate_id: str
    release_id: str
    release_bytes: bytes
    physical_export_id: str
    physical_archive: bytes
    blind_trial: BlindTrial
    hard_gate_results: Mapping[str, bool]

    def __post_init__(self) -> None:
        object.__setattr__(self, "hard_gate_results", _copy(self.hard_gate_results))
        if not self.release_bytes or not self.physical_archive:
            raise ValueError("Complete Package requires Release and Physical Export bytes")
        verify_blind_trial(self.blind_trial)


@dataclass(frozen=True)
class ProposedRevision:
    """A profile-interpreted revision plus its complete preview package."""

    data: Mapping[str, Any]
    rationale: str
    preview: CompletePackage

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _copy(self.data))
        if not self.rationale.strip():
            raise ValueError("Proposal rationale is required")


class GameProfileAdapter(Protocol):
    """Domain-owned build and revision behavior plugged into an Experiment."""

    profile_id: str
    profile_version: str
    component_lock: Mapping[str, Any]

    def build(
        self,
        draft_data: Mapping[str, Any],
        *,
        scratch_root: Path,
        instrument: FrozenInstrument,
    ) -> CompletePackage: ...

    def authoring_package(self, draft_data: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def proposal_contract(self) -> Mapping[str, Any]: ...

    def apply_builder_output(
        self,
        draft_data: Mapping[str, Any],
        parsed_output: Any,
        *,
        requirements: tuple[Requirement, ...],
        human_direction: str | None,
        scratch_root: Path,
        instrument: FrozenInstrument,
    ) -> ProposedRevision: ...


class RequirementTranslator(Protocol):
    def __call__(
        self,
        evaluation: Evaluation,
        findings: tuple[Finding, ...],
    ) -> tuple[Requirement, ...]: ...


class ScoreAggregator(Protocol):
    algorithm_id: str

    def aggregate(
        self,
        dimension_ids: tuple[str, ...],
        observations: tuple[Mapping[str, int], ...],
    ) -> Mapping[str, int]: ...


@dataclass(frozen=True)
class MedianPerDimension:
    algorithm_id: str = "median-per-dimension-v1"

    def aggregate(
        self,
        dimension_ids: tuple[str, ...],
        observations: tuple[Mapping[str, int], ...],
    ) -> Mapping[str, int]:
        if not observations:
            raise ValueError("score aggregation requires at least one observation")
        return {
            dimension_id: int(median(item[dimension_id] for item in observations))
            for dimension_id in sorted(dimension_ids)
        }


@dataclass(frozen=True)
class ModelPanelMember:
    authority_id: str
    principal: str
    requested_model: str
    assigned_lens: str
    driver: ModelDriver


@dataclass(frozen=True)
class HumanPanelMember:
    authority_id: str
    principal: str
    assigned_lens: str
    scores: Mapping[str, int]
    findings: tuple[Mapping[str, str], ...]
    evidence_class: str = "fresh-human"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", _copy(self.scores))
        object.__setattr__(
            self, "findings", tuple(_copy(item) for item in self.findings)
        )


@dataclass(frozen=True)
class PanelMeasurement:
    evaluation: Evaluation
    individual_scores: Mapping[str, Mapping[str, int]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "individual_scores", _copy(self.individual_scores))


@dataclass(frozen=True)
class PreparedProposal:
    proposal: Proposal
    preview: CompletePackage


_FINDING_FIELDS = {
    "requirement_code",
    "severity",
    "resource_path",
    "locus",
    "quote",
    "message",
}


class Experiment:
    """One persisted plan, lineage, authority graph, and measurement history."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.spine = ExperimentSpine(workspace)
        self.efficiency = EfficiencyController(workspace)
        if self.efficiency.plan_events:
            self.efficiency.write_projection()
        self.ledger = ClimbLedger(workspace)
        plans = self.ledger.snapshot()["experiment_plans"]
        if len(plans) != 1:
            raise ValueError("Workspace must contain exactly one Experiment Plan")
        self.plan = plans[0]
        self.instrument = self.ledger.get(
            "instrument", self.plan.instrument_id
        ).value

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        experiment_id: str,
        profile_id: str,
        profile_version: str,
        instrument: FrozenInstrument,
        initial_data: Mapping[str, Any],
        component_lock: Mapping[str, Any],
        reviewer: Authority,
        branch: str = "main",
        actor: str = "human:operator",
    ) -> "Experiment":
        """Create one persisted Experiment and its initial human-owned Draft."""
        if reviewer.kind != "human" or reviewer.role != "reviewer":
            raise ValueError("Experiment reviewer must be a human reviewer Authority")
        workspace = Workspace.create(root, workspace_id=experiment_id, actor=actor)
        workspace.commit_draft(
            branch=branch,
            expected_head=None,
            data=dict(_copy(initial_data)),
            reason="create experiment baseline",
            actor=actor,
            component_lock=dict(component_lock),
            operation_receipt={
                "operation": "experiment.create",
                "experiment_id": experiment_id,
                "profile_id": profile_id,
                "profile_version": profile_version,
                "instrument_id": instrument.instrument_id,
            },
            idempotency_key=f"experiment-create-{experiment_id}",
        )
        ledger = ClimbLedger(workspace)
        ledger.register(
            instrument,
            actor=actor,
            idempotency_key=f"instrument-{instrument.instrument_id}",
        )
        ledger.register(
            reviewer,
            actor=actor,
            idempotency_key=f"authority-{reviewer.authority_id}",
        )
        ledger.register(
            ExperimentPlan(
                experiment_id,
                profile_id,
                profile_version,
                instrument.instrument_id,
                branch,
            ),
            actor=actor,
            idempotency_key=f"experiment-plan-{experiment_id}",
        )
        return cls(workspace)

    @classmethod
    def open(cls, root: str | Path) -> "Experiment":
        """Open an existing Experiment without changing its lineage."""
        return cls(Workspace.open(root))

    @property
    def current_draft_ref(self) -> str:
        """Return the exact canonical Draft Revision selected by the Plan."""
        try:
            return self.workspace.branches[self.plan.branch]
        except KeyError as exc:
            raise ValueError("Experiment branch is unavailable") from exc

    @property
    def current_draft_data(self) -> Mapping[str, Any]:
        """Return a detached value copy of the current domain authoring data."""
        return self.workspace.store.read_json(self.current_draft_ref)["data"]

    def require_profile(self, adapter: GameProfileAdapter) -> None:
        """Reject ambient substitution of a differently identified profile adapter."""
        if (
            adapter.profile_id != self.plan.profile_id
            or adapter.profile_version != self.plan.profile_version
        ):
            raise ValueError(
                "Game Profile Adapter identity differs from the persisted Experiment Plan"
            )

    def bind_package(
        self,
        package: CompletePackage,
        *,
        actor: str = "system:experiment",
        idempotency_key: str,
    ) -> TrialBinding:
        """Persist exact package bytes and bind them to one Candidate for measurement."""
        if set(package.hard_gate_results) != set(self.instrument.hard_gate_codes):
            raise ValueError("Complete Package must replay every frozen hard gate")
        if not all(package.hard_gate_results.values()):
            raise ValueError("Complete Package cannot bind while a hard gate fails")
        release_ref = self.workspace.store.put_bytes(package.release_bytes)
        physical_ref = self.workspace.store.put_bytes(package.physical_archive)
        trial_ref = self.workspace.store.put_bytes(package.blind_trial.archive_bytes)
        binding = TrialBinding(
            package.candidate_id,
            package.release_id,
            release_ref,
            package.physical_export_id,
            physical_ref,
            package.blind_trial.trial_id,
            trial_ref,
            package.hard_gate_results,
        )
        return self.ledger.register(
            binding, actor=actor, idempotency_key=idempotency_key
        ).value

    def build_and_bind(
        self,
        adapter: GameProfileAdapter,
        *,
        scratch_root: str | Path,
        idempotency_key: str,
    ) -> tuple[CompletePackage, TrialBinding]:
        """Build the current Draft through its profile adapter and bind the result."""
        self.require_profile(adapter)
        package = adapter.build(
            self.current_draft_data,
            scratch_root=Path(scratch_root),
            instrument=self.instrument,
        )
        return package, self.bind_package(package, idempotency_key=idempotency_key)

    def _panel_protocol(
        self,
        members: tuple[ModelPanelMember | HumanPanelMember, ...],
        aggregator: ScoreAggregator,
    ) -> None:
        expected_size = int(self.instrument.blind_protocol.get("panel_size", 0))
        if expected_size < 1 or len(members) != expected_size:
            raise ValueError(f"blind panel requires exactly {expected_size} members")
        ids = tuple(item.authority_id for item in members)
        if len(ids) != len(set(ids)):
            raise ValueError("blind panel Authority identities must be distinct")
        expected_lenses = tuple(self.instrument.blind_protocol.get("panel_lenses", ()))
        if expected_lenses and set(item.assigned_lens for item in members) != set(
            expected_lenses
        ):
            raise ValueError("blind panel must assign every frozen lens exactly once")
        expected_aggregator = self.instrument.blind_protocol.get("panel_aggregation")
        if expected_aggregator != aggregator.algorithm_id:
            raise ValueError("score aggregator differs from the frozen Instrument")

    def _existing_panel(
        self, task_key: str, member_ids: tuple[str, ...]
    ) -> PanelMeasurement | None:
        tasks = [item for item in self.ledger.snapshot()["tasks"] if item.task_key == task_key]
        if not tasks:
            return None
        evaluations = {
            item.task_id: item for item in self.ledger.snapshot()["evaluations"]
        }
        if len(tasks) != 1 or tasks[0].task_id not in evaluations:
            raise ValueError("panel Task exists without one completed Evaluation")
        evaluation = evaluations[tasks[0].task_id]
        if set(evaluation.judge_authority_ids) != set(member_ids):
            raise ValueError("panel Task key was reused for different Authorities")
        scores: dict[str, Mapping[str, int]] = {}
        for receipt_id in evaluation.model_receipt_ids:
            receipt = self.ledger.get("model_receipt", receipt_id).value
            scores[receipt.authority_id] = self.workspace.store.read_json(
                receipt.parsed_output_ref
            )["scores"]
        for receipt_id in evaluation.human_receipt_ids:
            receipt = self.ledger.get("human_receipt", receipt_id).value
            scores[receipt.authority_id] = self.workspace.store.read_json(
                receipt.response_ref
            )["scores"]
        return PanelMeasurement(evaluation, scores)

    def _prepare_panel_task(
        self,
        binding_id: str,
        *,
        task_key: str,
        members: tuple[ModelPanelMember | HumanPanelMember, ...],
    ) -> tuple[TrialBinding, Task, BlindTrial]:
        binding_record = self.ledger.get("trial_binding", binding_id)
        binding = binding_record.value
        snapshot = self.ledger.snapshot()
        occupied = {item.authority_id for item in snapshot["authorities"]}
        reused = occupied & {item.authority_id for item in members}
        if reused:
            raise ValueError(f"fresh panel reuses prior Authority identities: {sorted(reused)}")
        for member in members:
            kind = "agent" if isinstance(member, ModelPanelMember) else "human"
            self.ledger.register(
                Authority(member.authority_id, kind, "judge", member.principal),
                actor="human:operator",
                idempotency_key=f"authority-{member.authority_id}",
            )
        excluded = tuple(
            sorted(
                item.authority_id
                for item in snapshot["authorities"]
                if item.kind == "agent" and item.role in {"builder", "fixer", "judge"}
            )
        )
        task = Task(
            task_key,
            "blind-measure",
            binding.candidate_id,
            self.instrument.instrument_id,
            members[0].authority_id,
            excluded,
            {
                "blind_trial": binding.blind_trial_ref,
                "trial_binding": binding_record.record_ref,
            },
            "Independently score every frozen dimension from the anonymous complete Trial.",
            tuple(item.authority_id for item in members[1:]),
        )
        self.ledger.register(
            task, actor="human:operator", idempotency_key=f"task-{task_key}"
        )
        for member in members:
            self.ledger.register(
                Exposure(
                    member.authority_id,
                    binding.blind_trial_ref,
                    "trial-tree",
                    f"fresh anonymous Blind Trial; assigned lens={member.assigned_lens}",
                    task.task_id,
                ),
                actor="system:exposure-recorder",
                idempotency_key=f"exposure-{task_key}-{member.authority_id}",
            )
        trial = load_blind_trial(
            self.workspace.store.read_bytes(binding.blind_trial_ref)
        )
        return binding, task, trial

    def _validate_observation(
        self,
        trial: BlindTrial,
        scores: Mapping[str, Any],
        findings: Any,
    ) -> tuple[dict[str, int], tuple[Finding, ...]]:
        dimension_ids = {item.dimension_id for item in self.instrument.dimensions}
        if set(scores) != dimension_ids or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 100
            for value in scores.values()
        ):
            raise ValueError("judge scores must cover every frozen dimension from 0 to 100")
        if not isinstance(findings, (list, tuple)):
            raise ValueError("judge findings must be a list")
        parsed_findings: list[Finding] = []
        for index, mapping in enumerate(findings):
            if not isinstance(mapping, Mapping) or set(mapping) != _FINDING_FIELDS:
                raise ValueError(f"judge Finding {index} does not match the contract")
            verify_trial_quote(trial, mapping["resource_path"], mapping["quote"])
            parsed_findings.append(
                Finding(
                    mapping["requirement_code"],
                    mapping["severity"],
                    mapping["resource_path"],
                    mapping["locus"],
                    mapping["quote"],
                    mapping["message"],
                )
            )
        return dict(scores), tuple(parsed_findings)

    def _record_findings(
        self,
        *,
        task: Task,
        authority_id: str,
        principal: str,
        findings: tuple[Finding, ...],
    ) -> tuple[str, ...]:
        existing = {item.finding_id for item in self.ledger.snapshot()["findings"]}
        result: list[str] = []
        for index, finding in enumerate(findings):
            if finding.finding_id not in existing:
                self.ledger.register(
                    finding,
                    actor=f"judge:{principal}",
                    idempotency_key=(
                        f"finding-{task.task_id}-{authority_id}-{index}"
                    ),
                )
                existing.add(finding.finding_id)
            if finding.finding_id not in result:
                result.append(finding.finding_id)
        return tuple(result)

    def _finalize_panel(
        self,
        *,
        binding: TrialBinding,
        task: Task,
        judges: tuple[str, ...],
        model_receipt_ids: tuple[str, ...],
        human_receipt_ids: tuple[str, ...],
        individual_scores: Mapping[str, Mapping[str, int]],
        finding_ids: tuple[str, ...],
        aggregator: ScoreAggregator,
    ) -> PanelMeasurement:
        """Aggregate one fully receipted panel under the frozen strategy."""
        dimension_ids = tuple(item.dimension_id for item in self.instrument.dimensions)
        aggregated = aggregator.aggregate(
            dimension_ids,
            tuple(individual_scores[item] for item in judges),
        )
        provisional = Evaluation(
            task.task_id,
            binding.candidate_id,
            self.instrument.instrument_id,
            "blind",
            judges,
            model_receipt_ids,
            aggregated,
            finding_ids,
            binding.hard_gate_results,
            "fail",
            human_receipt_ids=human_receipt_ids,
        )
        evaluation = Evaluation(
            provisional.task_id,
            provisional.candidate_id,
            provisional.instrument_id,
            provisional.mode,
            provisional.judge_authority_ids,
            provisional.model_receipt_ids,
            provisional.scores,
            provisional.finding_ids,
            provisional.hard_gate_results,
            "pass" if evaluation_passes(self.instrument, provisional) else "fail",
            human_receipt_ids=human_receipt_ids,
        )
        self.ledger.register(
            evaluation,
            actor=f"system:{aggregator.algorithm_id}",
            idempotency_key=f"evaluation-{task.task_id}",
        )
        return PanelMeasurement(evaluation, individual_scores)

    def measure_model_panel(
        self,
        *,
        binding_id: str,
        task_key: str,
        members: tuple[ModelPanelMember, ...],
        aggregator: ScoreAggregator | None = None,
        seed: int | None = None,
    ) -> PanelMeasurement:
        """Run a fresh blind model panel and persist its exact replay evidence."""
        aggregator = aggregator or MedianPerDimension()
        self._panel_protocol(members, aggregator)
        existing = self._existing_panel(
            task_key, tuple(item.authority_id for item in members)
        )
        if existing is not None:
            return existing
        binding, task, trial = self._prepare_panel_task(
            binding_id, task_key=task_key, members=members
        )
        scores: dict[str, Mapping[str, int]] = {}
        receipt_ids: list[str] = []
        finding_ids: list[str] = []
        executions = []
        for member in members:
            invocation = ModelInvocation(
                task.task_id,
                member.authority_id,
                "judge",
                member.requested_model,
                "Judge the attached anonymous complete Trial under every frozen dimension. Apply the assigned lens as extra scrutiny. Return only the contracted JSON evaluation and quote exact spans from exact trial paths for every finding.",
                {
                    "cover_story": self.instrument.blind_protocol.get(
                        "cover_story", "Anonymous narrative game"
                    ),
                    "instrument": self.instrument.to_mapping(),
                    "assigned_lens": member.assigned_lens,
                    "standing_warning": "Measurement alone cannot claim human-play standing.",
                },
                {
                    "schema_version": "0.8",
                    "output": {
                        "scores": {
                            item.dimension_id: "integer 0..100"
                            for item in self.instrument.dimensions
                        },
                        "findings": [
                            {
                                "requirement_code": "string",
                                "severity": "major|minor",
                                "resource_path": "exact path inside Blind Trial",
                                "locus": "precise human-readable locus",
                                "quote": "exact visible span",
                                "message": "why this is a quality tell",
                            }
                        ],
                    },
                },
                (
                    InvocationAttachment(
                        "blind-trial.zip", "application/zip", trial.archive_bytes
                    ),
                ),
                seed,
            )
            executions.append(
                ModelExecution(
                    invocation,
                    member.driver,
                    f"model-{task.task_id}-{member.authority_id}",
                )
            )
        records = execute_model_tasks_concurrently(
            self.ledger, tuple(executions), max_workers=len(executions)
        )
        for member, record in zip(members, records, strict=True):
            receipt = record.value
            parsed = self.workspace.store.read_json(receipt.parsed_output_ref)
            if not isinstance(parsed, Mapping) or set(parsed) != {"scores", "findings"}:
                raise ValueError("judge output does not match the panel contract")
            member_scores, member_findings = self._validate_observation(
                trial, parsed["scores"], parsed["findings"]
            )
            scores[member.authority_id] = member_scores
            receipt_ids.append(receipt.receipt_id)
            for finding_id in self._record_findings(
                task=task,
                authority_id=member.authority_id,
                principal=member.principal,
                findings=member_findings,
            ):
                if finding_id not in finding_ids:
                    finding_ids.append(finding_id)
        return self._finalize_panel(
            binding=binding,
            task=task,
            judges=tuple(item.authority_id for item in members),
            model_receipt_ids=tuple(receipt_ids),
            human_receipt_ids=(),
            individual_scores=scores,
            finding_ids=tuple(finding_ids),
            aggregator=aggregator,
        )

    def measure_human_panel(
        self,
        *,
        binding_id: str,
        task_key: str,
        members: tuple[HumanPanelMember, ...],
        aggregator: ScoreAggregator | None = None,
    ) -> PanelMeasurement:
        """Record a fresh blind human panel as human—not model—evidence."""
        aggregator = aggregator or MedianPerDimension()
        self._panel_protocol(members, aggregator)
        existing = self._existing_panel(
            task_key, tuple(item.authority_id for item in members)
        )
        if existing is not None:
            return existing
        binding, task, trial = self._prepare_panel_task(
            binding_id, task_key=task_key, members=members
        )
        scores: dict[str, Mapping[str, int]] = {}
        receipt_ids: list[str] = []
        finding_ids: list[str] = []
        for member in members:
            member_scores, member_findings = self._validate_observation(
                trial, member.scores, member.findings
            )
            response = {
                "schema_version": "0.8",
                "scores": member_scores,
                "findings": [item.to_mapping() for item in member_findings],
            }
            receipt = self.ledger.record_human_observation(
                authority_id=member.authority_id,
                task_id=task.task_id,
                input_refs={"blind_trial": binding.blind_trial_ref},
                response=response,
                evidence_class=member.evidence_class,
                actor=f"human:{member.principal}",
                idempotency_key=f"human-{task.task_id}-{member.authority_id}",
            ).value
            scores[member.authority_id] = member_scores
            receipt_ids.append(receipt.receipt_id)
            for finding_id in self._record_findings(
                task=task,
                authority_id=member.authority_id,
                principal=member.principal,
                findings=member_findings,
            ):
                if finding_id not in finding_ids:
                    finding_ids.append(finding_id)
        return self._finalize_panel(
            binding=binding,
            task=task,
            judges=tuple(item.authority_id for item in members),
            model_receipt_ids=(),
            human_receipt_ids=tuple(receipt_ids),
            individual_scores=scores,
            finding_ids=tuple(finding_ids),
            aggregator=aggregator,
        )

    def translate_requirements(
        self,
        *,
        evaluation_id: str,
        translator: RequirementTranslator,
    ) -> tuple[Requirement, ...]:
        """Translate one Evaluation's quoted Findings into answer-safe Requirements."""
        evaluation = self.ledger.get("evaluation", evaluation_id).value
        findings_by_id = {
            item.finding_id: item for item in self.ledger.snapshot()["findings"]
        }
        findings = tuple(findings_by_id[item] for item in evaluation.finding_ids)
        requirements = translator(evaluation, findings)
        for requirement in requirements:
            if not requirement.source_finding_ids or not set(
                requirement.source_finding_ids
            ) <= set(evaluation.finding_ids):
                raise ValueError(
                    "Translated Requirement must cite this Evaluation's Findings"
                )
            existing = {
                item.requirement_id for item in self.ledger.snapshot()["requirements"]
            }
            if requirement.requirement_id not in existing:
                self.ledger.register(
                    requirement,
                    actor="human:operator",
                    idempotency_key=f"requirement-{requirement.requirement_id}",
                )
        return requirements

    def propose_revision(
        self,
        adapter: GameProfileAdapter,
        *,
        evaluation_id: str,
        translator: RequirementTranslator,
        task_key: str,
        authority_id: str,
        principal: str,
        requested_model: str,
        driver: ModelDriver,
        scratch_root: str | Path,
        human_direction: str | None = None,
        seed: int | None = None,
    ) -> PreparedProposal:
        """Run a profile-aware builder and persist an inert, previewed Proposal."""
        self.require_profile(adapter)
        evaluation = self.ledger.get("evaluation", evaluation_id).value
        requirements = self.translate_requirements(
            evaluation_id=evaluation_id, translator=translator
        )
        return self._propose_revision_with_requirements(
            adapter,
            baseline_candidate_id=evaluation.candidate_id,
            requirements=requirements,
            task_key=task_key,
            authority_id=authority_id,
            principal=principal,
            requested_model=requested_model,
            driver=driver,
            scratch_root=scratch_root,
            human_direction=human_direction,
            seed=seed,
        )

    def propose_revision_from_requirements(
        self,
        adapter: GameProfileAdapter,
        *,
        binding_id: str,
        requirement_ids: tuple[str, ...],
        task_key: str,
        authority_id: str,
        principal: str,
        requested_model: str,
        driver: ModelDriver,
        scratch_root: str | Path,
        human_direction: str | None = None,
        seed: int | None = None,
    ) -> PreparedProposal:
        """Build from already translated human-play Requirements."""
        self.require_profile(adapter)
        if not requirement_ids:
            raise ValueError("human-play proposal requires at least one Requirement")
        binding = self.ledger.get("trial_binding", binding_id).value
        requirements = tuple(
            self.ledger.get("requirement", item).value for item in requirement_ids
        )
        return self._propose_revision_with_requirements(
            adapter,
            baseline_candidate_id=binding.candidate_id,
            requirements=requirements,
            task_key=task_key,
            authority_id=authority_id,
            principal=principal,
            requested_model=requested_model,
            driver=driver,
            scratch_root=scratch_root,
            human_direction=human_direction,
            seed=seed,
        )

    def _propose_revision_with_requirements(
        self,
        adapter: GameProfileAdapter,
        *,
        baseline_candidate_id: str,
        requirements: tuple[Requirement, ...],
        task_key: str,
        authority_id: str,
        principal: str,
        requested_model: str,
        driver: ModelDriver,
        scratch_root: str | Path,
        human_direction: str | None,
        seed: int | None,
    ) -> PreparedProposal:
        """Run the shared answer-safe builder path for model or human-play findings."""
        authority = Authority(authority_id, "agent", "builder", principal)
        self.ledger.register(
            authority,
            actor="human:operator",
            idempotency_key=f"authority-{authority_id}",
        )
        safe_requirements = {
            "schema_version": "0.8",
            "requirements": [
                {
                    "requirement_id": item.requirement_id,
                    "requirement_code": item.requirement_code,
                    "property": item.property,
                    "failure": item.failure,
                    "builder_brief": item.builder_brief,
                }
                for item in requirements
            ],
        }
        authoring_package = adapter.authoring_package(self.current_draft_data)
        requirements_ref = self.workspace.store.put_json(safe_requirements)
        authoring_ref = self.workspace.store.put_json(authoring_package)
        excluded = tuple(
            sorted(
                item.authority_id
                for item in self.ledger.snapshot()["authorities"]
                if item.role == "judge"
            )
        )
        task = Task(
            task_key,
            "fix",
            baseline_candidate_id,
            self.instrument.instrument_id,
            authority.authority_id,
            excluded,
            {
                "answer_safe_requirements": requirements_ref,
                "authoring_package": authoring_ref,
            },
            "Propose a coherent child from answer-safe Requirements and human direction without seeing judge-only evidence.",
        )
        self.ledger.register(
            task, actor="human:operator", idempotency_key=f"task-{task_key}"
        )
        for label, object_ref in task.input_refs.items():
            self.ledger.register(
                Exposure(
                    authority.authority_id,
                    object_ref,
                    label,
                    "answer-safe builder input",
                    task.task_id,
                ),
                actor="system:exposure-recorder",
                idempotency_key=f"exposure-{task_key}-{label}",
            )
        invocation = ModelInvocation(
            task.task_id,
            authority.authority_id,
            "builder",
            requested_model,
            "Revise the attached authoring package against every Requirement. Return only the Game Profile Adapter's contracted response.",
            {
                "requirements": safe_requirements,
                "human_direction": human_direction,
                "profile": {
                    "profile_id": self.plan.profile_id,
                    "profile_version": self.plan.profile_version,
                },
                "blindness_warning": "Do not infer judge quotes, paths, scores, or hidden answers.",
            },
            adapter.proposal_contract(),
            (
                InvocationAttachment(
                    "authoring-package.json",
                    "application/json",
                    canonical_json(authoring_package),
                ),
            ),
            seed,
        )
        receipt = execute_model_task(
            self.ledger,
            invocation,
            driver,
            idempotency_key=f"model-{task.task_id}",
        ).value
        parsed = self.workspace.store.read_json(receipt.parsed_output_ref)
        proposed = adapter.apply_builder_output(
            self.current_draft_data,
            parsed,
            requirements=requirements,
            human_direction=human_direction,
            scratch_root=Path(scratch_root),
            instrument=self.instrument,
        )
        if proposed.preview.candidate_id == baseline_candidate_id:
            raise ValueError("Proposal must produce a distinct Candidate")
        if set(proposed.preview.hard_gate_results) != set(
            self.instrument.hard_gate_codes
        ) or not all(proposed.preview.hard_gate_results.values()):
            raise ValueError("Proposal preview must pass every frozen hard gate")
        proposal = self.ledger.record_proposal(
            task_id=task.task_id,
            baseline_draft_ref=self.current_draft_ref,
            proposed_data=proposed.data,
            requirement_ids=tuple(item.requirement_id for item in requirements),
            builder_authority_id=authority.authority_id,
            model_receipt_id=receipt.receipt_id,
            rationale=proposed.rationale,
            actor=f"agent:{principal}",
            idempotency_key=f"proposal-{task_key}",
        ).value
        return PreparedProposal(proposal, proposed.preview)

    def review_proposal(
        self,
        *,
        proposal_id: str,
        reviewer_authority_id: str,
        decision: str,
        reason: str,
    ) -> HumanReview:
        """Persist an exact human decision without applying the Proposal."""
        if decision not in {"approved", "rejected"} or not reason.strip():
            raise ValueError("Review requires an approved/rejected decision and reason")
        proposal = self.ledger.get("proposal", proposal_id).value
        review = HumanReview(
            proposal.proposal_id,
            reviewer_authority_id,
            decision,
            reason,
            proposal.requirement_ids if decision == "approved" else (),
        )
        return self.ledger.register(
            review,
            actor=f"human:{reviewer_authority_id}",
            idempotency_key=f"review-{proposal.proposal_id}",
        ).value

    def apply_review(
        self,
        adapter: GameProfileAdapter,
        *,
        proposal_id: str,
        review_id: str,
        idempotency_key: str,
    ) -> Transition:
        """Apply only an exact approved Review through the frozen profile adapter."""
        self.require_profile(adapter)
        return self.ledger.apply_approved_transition(
            proposal_id=proposal_id,
            review_id=review_id,
            branch=self.plan.branch,
            component_lock=adapter.component_lock,
            idempotency_key=idempotency_key,
        )

    def select(
        self,
        *,
        baseline_evaluation_id: str,
        child_evaluation_id: str,
    ) -> SelectionDecision:
        """Apply the frozen evidence rules to baseline and child Evaluations."""
        baseline = self.ledger.get("evaluation", baseline_evaluation_id).value
        child = self.ledger.get("evaluation", child_evaluation_id).value
        receipt_ids = (
            *baseline.model_receipt_ids,
            *baseline.human_receipt_ids,
            *child.model_receipt_ids,
            *child.human_receipt_ids,
        )
        receipts = tuple(
            self.ledger.get(
                "human_receipt" if item.startswith("human-receipt:") else "model_receipt",
                item,
            ).value
            for item in receipt_ids
        )
        decision = decide_selection(self.instrument, baseline, child, receipts)
        return self.ledger.register(
            decision,
            actor="system:frozen-selection-rule",
            idempotency_key=(
                f"selection-{baseline.evaluation_id}-{child.evaluation_id}"
            ),
        ).value

    def verify(self) -> Mapping[str, Any]:
        """Verify the Workspace and climb hash chains plus every referenced object."""
        workspace = self.workspace.verify()
        climb = self.ledger.verify()
        standing = self.spine.verify()
        efficiency = self.efficiency.verify()
        return {
            "ok": (
                workspace["ok"] and climb["ok"] and standing["ok"]
                and efficiency["ok"]
            ),
            "workspace": workspace,
            "climb": climb,
            "standing": standing,
            "efficiency": efficiency,
        }

    def record_selected_rung(self, **kwargs: Any) -> Mapping[str, Any]:
        """Persist one exact selected Candidate and export its portable `.ngw`."""
        return self.spine.record_selected_rung(**kwargs)

    def current_standing(self) -> Mapping[str, Any]:
        """Rebuild the current qualification projection from journals."""
        return self.spine.write_projection()

    def export_archive(self, target: str | Path) -> None:
        """Write a deterministic, relocatable archive of the complete Experiment."""
        self.workspace.export_archive(target)
