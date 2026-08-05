"""Prepare a real complete-package climb for human-triggered model execution."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from copy import deepcopy
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from narrative_game.climb import (
    Authority,
    BlindTrial,
    ClimbLedger,
    Dimension,
    Evaluation,
    ExperimentPlan,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReview,
    Task,
    TrialBinding,
    InvocationAttachment,
    ModelDriver,
    ModelInvocation,
    Proposal,
    Requirement,
    SelectionDecision,
    execute_model_task,
    load_blind_trial,
    prepare_blind_trial,
    verify_trial_quote,
)
from narrative_game.climb.drivers import JsonCommandDriver
from narrative_game.climb.selection import decide_selection, evaluation_passes
from narrative_game.compiler import GameRelease, compile_candidate, reference_component_lock
from narrative_game.contracts import canonical_json, digest_json
from narrative_game.experiment import (
    CompletePackage,
    Experiment,
    ModelPanelMember,
)
from narrative_game.physical import PhysicalExport, export_physical
from narrative_game.stage5_fixture import DEFAULT_SOURCE, WorkedBuild, build_worked_candidate
from narrative_game.workspace import Workspace


@dataclass(frozen=True)
class PreparedBaseline:
    build: WorkedBuild
    release: GameRelease
    physical: PhysicalExport
    trial: BlindTrial
    workspace: Workspace
    ledger: ClimbLedger
    instrument: FrozenInstrument
    task: Task
    binding: TrialBinding
    output_root: Path
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class BaselineMeasurement:
    workspace: Workspace
    ledger: ClimbLedger
    evaluation: Evaluation
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class PreparedProposal:
    workspace: Workspace
    ledger: ClimbLedger
    proposal: Proposal
    proposed_build: WorkedBuild
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class BoundChild:
    workspace: Workspace
    ledger: ClimbLedger
    build: WorkedBuild
    release: GameRelease
    physical: PhysicalExport
    trial: BlindTrial
    binding: TrialBinding
    summary: Mapping[str, Any]


@dataclass(frozen=True)
class PanelMember:
    authority_id: str
    principal: str
    requested_model: str
    assigned_lens: str
    driver: ModelDriver


@dataclass(frozen=True)
class PanelMeasurement:
    workspace: Workspace
    ledger: ClimbLedger
    evaluation: Evaluation
    individual_scores: Mapping[str, Mapping[str, int]]
    summary: Mapping[str, Any]


def _stage7_experiment(root: str | Path) -> Experiment:
    """Attach the worked Stage 7 profile to the reusable Stage 8 Experiment API."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    plans = ledger.snapshot()["experiment_plans"]
    if not plans:
        instrument = complete_experience_panel_instrument()
        if not any(
            item.instrument_id == instrument.instrument_id
            for item in ledger.snapshot()["instruments"]
        ):
            ledger.register(
                instrument,
                actor="human:operator",
                idempotency_key="instrument-complete-experience-panel-v1-1",
            )
        ledger.register(
            ExperimentPlan(
                "ashwood-ledger-stage7",
                "worked.facilitated-investigation",
                "1.0.0",
                instrument.instrument_id,
                "main",
            ),
            actor="human:operator",
            idempotency_key="experiment-plan-ashwood-ledger-stage7",
        )
    return Experiment(workspace)


def complete_experience_instrument() -> FrozenInstrument:
    """Freeze the first research-backed complete-player-experience rubric."""
    return FrozenInstrument(
        "facilitated-investigation-complete-experience",
        "1.0.0",
        "compiled-player-facing-blind-trial",
        (
            Dimension(
                "investigative_coherence",
                "World events, claims, materials, and timing form one coherent case.",
                25,
                {"0": "contradictory or generated", "60": "coherent with visible seams", "100": "expert-resistant world"},
            ),
            Dimension(
                "deduction_quality",
                "Evidence supports earned inference, competing hypotheses, and redundant proof.",
                30,
                {"0": "blocked or automatic", "60": "solvable but fragile", "100": "robust and earned"},
            ),
            Dimension(
                "character_agency",
                "Each Seat has distinct knowledge, goals, and meaningful contribution.",
                20,
                {"0": "spectator", "60": "functional role", "100": "indispensable unscripted agency"},
            ),
            Dimension(
                "facilitation_resilience",
                "Pacing, access, hints, and recovery protect progression without replacing play.",
                15,
                {"0": "likely stall", "60": "recoverable", "100": "resilient across plausible play"},
            ),
            Dimension(
                "production_realism",
                "Player-facing source and print materials are legible, credible, and usable.",
                10,
                {"0": "unusable", "60": "production-ready with tells", "100": "convincing and polished"},
            ),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 75},
            {"metric": "investigative_coherence", "operator": ">=", "value": 60},
            {"metric": "deduction_quality", "operator": ">=", "value": 60},
            {"metric": "character_agency", "operator": ">=", "value": 60},
            {"metric": "facilitation_resilience", "operator": ">=", "value": 60},
            {"metric": "production_realism", "operator": ">=", "value": 60},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Anonymous two-seat archival investigation",
            "allowed": ["blind-trial-archive", "frozen-instrument"],
            "forbidden": [
                "trusted-truth",
                "host-only-materials",
                "answer-key",
                "candidate-release-export-identities",
                "builder-rationale",
                "prior-score",
                "atlas",
            ],
            "selection_evidence_classes": ["live-model"],
            "research_register": "docs/research-evidence-register.md",
        },
        (
            "compiler.release",
            "physical.preflight",
            "blind-trial.verify",
            "stage5.access",
        ),
    )


def complete_experience_panel_instrument() -> FrozenInstrument:
    """Freeze the k=3 scorer before comparing the baseline and approved child."""
    original = complete_experience_instrument()
    protocol = dict(original.blind_protocol)
    protocol.update(
        {
            "panel_size": 3,
            "panel_aggregation": "median-per-dimension-v1",
            "panel_lenses": [
                "procedural-deduction",
                "forensic-production",
                "structural-coherence-agency",
            ],
        }
    )
    return FrozenInstrument(
        original.name,
        "1.1.0",
        original.scope,
        original.dimensions,
        original.acceptance_rules,
        protocol,
        original.hard_gate_codes,
    )


def prepare_baseline(
    root: str | Path,
    *,
    source_root: str | Path = DEFAULT_SOURCE,
) -> PreparedBaseline:
    """Compile, blind, persist, and archive the baseline without inventing a score."""
    root = Path(root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"Stage 7 experiment root is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    build = build_worked_candidate(root / "forge-experiment", source_root=source_root)
    compilation = compile_candidate(build.candidate)
    if compilation.release is None:
        raise ValueError([item.to_mapping() for item in compilation.attempt.findings])
    release = compilation.release
    physical = export_physical(release)
    trial = prepare_blind_trial(
        release,
        physical,
        cover_story="Evaluate this anonymous two-seat archival investigation as a complete player experience.",
    )

    workspace = Workspace.create(
        root / "workspace", workspace_id="ashwood-ledger-stage7", actor="human:operator"
    )
    manifest_ref = workspace.store.put_json(build.candidate.frozen_manifest)
    release_ref = workspace.store.put_bytes(release.bundle_bytes)
    physical_ref = workspace.store.put_bytes(physical.archive_bytes)
    trial_ref = workspace.store.put_bytes(trial.archive_bytes)
    baseline_head = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={
            "title": "The Ashwood Ledger",
            "human_readable_source": build.source,
            "compiler_candidate_id": build.candidate.candidate_id,
            "manifest": manifest_ref,
        },
        reason="materialize the complete compiled baseline before real measurement",
        actor="human:operator",
        component_lock=reference_component_lock(),
        operation_receipt={
            "operation": "stage7.prepare-baseline",
            "source_hash": digest_json(build.source),
            "release_bundle": release_ref,
            "physical_archive": physical_ref,
            "blind_trial": trial_ref,
        },
        idempotency_key="stage7-baseline-draft",
    )
    ledger = ClimbLedger(workspace)
    judge = Authority(
        "stage7-baseline-judge-slot", "agent", "judge", "configured-at-execution"
    )
    reviewer = Authority(
        "stage7-human-reviewer", "human", "reviewer", "repository-owner"
    )
    instrument = complete_experience_instrument()
    ledger.register(judge, actor="human:operator", idempotency_key="authority-baseline-judge")
    ledger.register(reviewer, actor="human:operator", idempotency_key="authority-reviewer")
    ledger.register(instrument, actor="human:operator", idempotency_key="instrument-complete-experience")
    hard_gates = {
        "compiler.release": compilation.ok,
        "physical.preflight": bool(physical.preflight["ok"]),
        "blind-trial.verify": True,
        "stage5.access": not any(
            item.severity == "blocker" for item in build.candidate.advisories
        ),
    }
    binding = TrialBinding(
        build.candidate.candidate_id,
        release.release_id,
        release_ref,
        physical.export_id,
        physical_ref,
        trial.trial_id,
        trial_ref,
        hard_gates,
    )
    binding_record = ledger.register(
        binding, actor="human:operator", idempotency_key="trial-binding-baseline"
    )
    task = Task(
        "measure-complete-baseline",
        "blind-measure",
        build.candidate.candidate_id,
        instrument.instrument_id,
        judge.authority_id,
        (),
        {"blind_trial": trial_ref, "trial_binding": binding_record.record_ref},
        "Apply the frozen complete-experience Instrument only to the attached Blind Trial.",
    )
    ledger.register(task, actor="human:operator", idempotency_key="task-baseline-measure")
    ledger.register(
        Exposure(judge.authority_id, trial_ref, "trial-tree", "complete baseline Blind Trial", task.task_id),
        actor="system:exposure-recorder",
        idempotency_key="exposure-baseline-trial",
    )
    _stage7_experiment(root)
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})

    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "baseline-game-release.zip").write_bytes(release.bundle_bytes)
    (output / "baseline-physical-package.zip").write_bytes(physical.archive_bytes)
    (output / "baseline-blind-trial.zip").write_bytes(trial.archive_bytes)
    summary = {
        "schema_version": "0.7",
        "status": "awaiting-real-baseline-measurement",
        "candidate_id": build.candidate.candidate_id,
        "release_id": release.release_id,
        "physical_export_id": physical.export_id,
        "blind_trial_id": trial.trial_id,
        "instrument_id": instrument.instrument_id,
        "task_id": task.task_id,
        "trial_binding_id": binding.binding_id,
        "baseline_draft_head": baseline_head,
        "model_receipts": 0,
        "evaluations": 0,
        "standing": None,
        "workspace_verified": True,
        "climb_verified": True,
    }
    (output / "stage7-preparation.json").write_bytes(canonical_json(summary))
    workspace.export_archive(output / "ashwood-stage7-prepared.ngw")
    return PreparedBaseline(
        build,
        release,
        physical,
        trial,
        workspace,
        ledger,
        instrument,
        task,
        binding,
        output,
        summary,
    )


def measure_prepared_baseline(
    root: str | Path,
    driver: ModelDriver,
    *,
    requested_model: str,
    task_key: str = "measure-complete-baseline",
) -> BaselineMeasurement:
    """Run the configured baseline judge and persist only evidenced output."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    snapshot = ledger.snapshot()
    tasks = [item for item in snapshot["tasks"] if item.task_key == task_key]
    if len(tasks) != 1:
        raise ValueError("prepared baseline measurement Task is missing or ambiguous")
    task = tasks[0]
    instruments = [item for item in snapshot["instruments"] if item.instrument_id == task.instrument_id]
    bindings = [item for item in snapshot["trial_bindings"] if item.candidate_id == task.candidate_id]
    if len(instruments) != 1 or len(bindings) != 1:
        raise ValueError("prepared baseline Instrument or Trial Binding is missing")
    instrument = instruments[0]
    binding = bindings[0]
    trial_bytes = workspace.store.read_bytes(binding.blind_trial_ref)
    trial = load_blind_trial(trial_bytes)
    invocation = ModelInvocation(
        task.task_id,
        task.assigned_authority_id,
        "judge",
        requested_model,
        "Judge the attached Blind Trial under every frozen dimension. Every finding must name exactly one literal archive resource_path and quote an exact span contained in that same file. If a concern crosses files, emit one finding per file. Return only the contracted JSON evaluation.",
        {
            "cover_story": instrument.blind_protocol["cover_story"],
            "instrument": instrument.to_mapping(),
            "standing_warning": "This is baseline measurement only; do not compare, select, or claim human-play standing.",
        },
        {
            "schema_version": "0.7",
            "output": {
                "scores": {item.dimension_id: "integer 0..100" for item in instrument.dimensions},
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
        (InvocationAttachment("blind-trial.zip", "application/zip", trial_bytes),),
        1997,
    )
    receipt_record = execute_model_task(
        ledger,
        invocation,
        driver,
        idempotency_key=f"stage7-model-{task.task_id}",
    )
    parsed = workspace.store.read_json(receipt_record.value.parsed_output_ref)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("scores"), dict) or not isinstance(parsed.get("findings"), list):
        raise ValueError("baseline judge output does not match the frozen contract")
    dimension_ids = {item.dimension_id for item in instrument.dimensions}
    scores = parsed["scores"]
    if set(scores) != dimension_ids or any(
        isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100
        for value in scores.values()
    ):
        raise ValueError("baseline judge scores do not cover every frozen dimension from 0 to 100")
    finding_ids = []
    required = {
        "requirement_code",
        "severity",
        "resource_path",
        "locus",
        "quote",
        "message",
    }
    for index, mapping in enumerate(parsed["findings"]):
        if not isinstance(mapping, dict) or set(mapping) != required:
            raise ValueError(f"baseline judge Finding {index} does not match the contract")
        verify_trial_quote(trial, mapping["resource_path"], mapping["quote"])
        finding = Finding(
            mapping["requirement_code"],
            mapping["severity"],
            mapping["resource_path"],
            mapping["locus"],
            mapping["quote"],
            mapping["message"],
        )
        ledger.register(
            finding,
            actor=f"agent:{task.assigned_authority_id}",
            idempotency_key=f"stage7-finding-{task.task_id}-{index}",
        )
        finding_ids.append(finding.finding_id)
    provisional = Evaluation(
        task.task_id,
        task.candidate_id,
        instrument.instrument_id,
        "blind",
        (task.assigned_authority_id,),
        (receipt_record.record_id,),
        scores,
        tuple(finding_ids),
        binding.hard_gate_results,
        "fail",
    )
    outcome = "pass" if evaluation_passes(instrument, provisional) else "fail"
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
        outcome,
    )
    ledger.register(
        evaluation,
        actor=f"agent:{task.assigned_authority_id}",
        idempotency_key=f"stage7-evaluation-{task.task_id}",
    )
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    score = evaluation.overall_score(instrument)
    summary = {
        "schema_version": "0.7",
        "status": "baseline-measured-awaiting-requirement-translation",
        "candidate_id": task.candidate_id,
        "instrument_id": instrument.instrument_id,
        "model_receipt_id": receipt_record.record_id,
        "evaluation_id": evaluation.evaluation_id,
        "overall_score": score,
        "outcome": outcome,
        "finding_ids": list(finding_ids),
        "evidence_class": receipt_record.value.evidence_class,
        "standing": None,
    }
    output = root / "output"
    safe_task_key = "".join(character if character.isalnum() or character == "-" else "-" for character in task.task_key)
    (output / f"stage7-{safe_task_key}-measurement.json").write_bytes(canonical_json(summary))
    workspace.export_archive(output / f"ashwood-stage7-{safe_task_key}-measured.ngw")
    return BaselineMeasurement(workspace, ledger, evaluation, summary)


def add_fresh_baseline_judge(
    root: str | Path,
    *,
    authority_id: str,
    principal: str,
    task_key: str,
) -> Task:
    """Add an unexposed judge slot over the same frozen baseline Trial."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    snapshot = ledger.snapshot()
    if len(snapshot["instruments"]) != 1 or len(snapshot["trial_bindings"]) != 1:
        raise ValueError("prepared baseline Instrument or Trial Binding is ambiguous")
    instrument = snapshot["instruments"][0]
    binding = snapshot["trial_bindings"][0]
    authority = Authority(authority_id, "agent", "judge", principal)
    ledger.register(
        authority,
        actor="human:operator",
        idempotency_key=f"authority-{authority_id}",
    )
    binding_record = ledger.get("trial_binding", binding.binding_id)
    task = Task(
        task_key,
        "blind-measure",
        binding.candidate_id,
        instrument.instrument_id,
        authority.authority_id,
        (),
        {"blind_trial": binding.blind_trial_ref, "trial_binding": binding_record.record_ref},
        "Apply the frozen complete-experience Instrument only to the attached Blind Trial.",
    )
    ledger.register(
        task,
        actor="human:operator",
        idempotency_key=f"task-{task_key}",
    )
    ledger.register(
        Exposure(
            authority.authority_id,
            binding.blind_trial_ref,
            "trial-tree",
            "fresh complete baseline Blind Trial",
            task.task_id,
        ),
        actor="system:exposure-recorder",
        idempotency_key=f"exposure-{task_key}",
    )
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    return task


def record_stage7_requirements(root: str | Path) -> tuple[Requirement, ...]:
    """Translate blind Findings into generalized, answer-safe builder contracts."""
    root = Path(root)
    ledger = ClimbLedger(Workspace.open(root / "workspace"))
    findings = ledger.snapshot()["findings"]
    if not findings:
        raise ValueError("a valid blind Evaluation must precede Requirement translation")

    def ids_for(*suffixes: str) -> tuple[str, ...]:
        matches = tuple(
            item.finding_id
            for item in findings
            if any(item.resource_path.endswith(suffix) for suffix in suffixes)
        )
        if not matches:
            raise ValueError(f"no source Findings match {suffixes!r}")
        return matches

    translated = (
        Requirement(
            "artifact.named-party-role-coherence",
            "Every named person in a flagship artifact has one unambiguous document role.",
            "Unexplained party-name or surname collisions make intentional evidence look generated.",
            "Simplify or constrain artifact party configuration so every displayed person has an unambiguous role and no unexplained collision distracts from the case.",
            ids_for("madison-deed-1997", "madison-deed-1997.pdf"),
        ),
        Requirement(
            "seat.delivered-evidence-framing",
            "Every artifact delivered to a Seat is framed in that Seat's phase-aware projection.",
            "A Seat receives evidence without knowing why it matters to that role or phase.",
            "Give each Seat phase-aware framing for every artifact that can be delivered to it, including the artifact's role in that Seat's distinct objective.",
            ids_for("avery.json", "blake.json"),
        ),
        Requirement(
            "resolution.player-facing-language",
            "The resolution action uses language and fields players can understand from the package.",
            "Internal engine identifiers leak into the climactic player action without a player-visible key.",
            "Rewrite the resolution artifact around in-fiction conclusions and named evidence; do not require internal identifiers or undeclared system vocabulary.",
            ids_for("accusation-form", "accusation-form.pdf"),
        ),
        Requirement(
            "pacing.earned-disclosure",
            "Disclosure timing preserves a meaningful chain of inference through investigation.",
            "An early artifact resolves access, motive, and concealment before players combine later evidence.",
            "Stage admissions and corroboration so opening material creates questions, investigation material supports competing inferences, and resolution evidence completes rather than repeats the answer.",
            ids_for("schedule.json", "closing-interview"),
        ),
    )
    existing = {item.requirement_id: item for item in ledger.snapshot()["requirements"]}
    for item in translated:
        if item.requirement_id not in existing:
            ledger.register(
                item,
                actor="human:operator",
                idempotency_key=f"stage7-requirement-{item.requirement_code}",
            )
    return translated


def record_stage7_followup_requirements(
    root: str | Path,
    *,
    evaluation_id: str,
) -> tuple[Requirement, ...]:
    """Translate a failed child panel into generalized, answer-safe contracts."""
    root = Path(root)
    ledger = ClimbLedger(Workspace.open(root / "workspace"))
    evaluation = ledger.get("evaluation", evaluation_id).value
    if evaluation.mode != "blind" or evaluation.outcome != "fail":
        raise ValueError("follow-up Requirements require one failed blind Evaluation")
    all_findings = {item.finding_id: item for item in ledger.snapshot()["findings"]}
    findings = tuple(all_findings[item] for item in evaluation.finding_ids)

    def ids_where(predicate) -> tuple[str, ...]:
        return tuple(item.finding_id for item in findings if predicate(item))

    translated: list[Requirement] = []

    def translate(
        requirement_code: str,
        property: str,
        failure: str,
        builder_brief: str,
        predicate,
    ) -> None:
        source_finding_ids = ids_where(predicate)
        if source_finding_ids:
            translated.append(
                Requirement(
                    requirement_code,
                    property,
                    failure,
                    builder_brief,
                    source_finding_ids,
                )
            )

    translate(
            "evidence.earned-inference",
            "Player records present observations and data without supplying their own conclusions.",
            "Interpretive captions, confessions, or evidence labels can turn the central deduction into transcription.",
            "Remove conclusion-bearing commentary from player records; distribute the facts needed to infer access, motive, and transaction across records that must be compared.",
            lambda item: item.requirement_code.startswith("deduction_quality"),
    )
    translate(
            "evidence.independent-act-trace",
            "The central physical act has an independently attributable trace beyond access and motive.",
            "Opportunity plus payment evidence supports suspicion but cannot establish who performed the central act.",
            "Add an observational record, recovery trace, possession fact, or bounded admission that independently links an actor to the central act without printing the conclusion.",
            lambda item: item.requirement_code.startswith("deduction_quality")
            and any(marker in item.message.casefold() for marker in ("actually removed", "central act", "possession evidence")),
    )
    translate(
            "evidence.explicit-resolution-referent",
            "Every comparison named at Resolution points to a specific delivered record or explicitly named set of earlier observations.",
            "A final checkpoint that names an absent or ambiguous earlier record makes the payoff depend on reconstructing the authoring model.",
            "Rewrite the Resolution instruction and response form to name the exact delivered records or exact earlier observations players must compare; do not imply an undelivered artifact.",
            lambda item: "resolution_reference" in item.requirement_code
            or "resolution_evidence_gap" in item.requirement_code,
    )
    translate(
            "evidence.competing-hypotheses",
            "Opening preserves at least two plausible actor-level explanations that later evidence can discriminate.",
            "When Opening already isolates the only named actor, Investigation becomes confirmation rather than deduction.",
            "Keep at least two live actor-level hypotheses through Opening and give later records discriminating facts for each without naming a conclusion in player text.",
            lambda item: any(
                marker in item.requirement_code
                for marker in ("single_suspect", "competing_hypotheses")
            ),
    )
    translate(
            "evidence.substantive-alternate-hypothesis",
            "A competing actor-level hypothesis has plausible motive, opportunity, and observable behavior before later evidence discriminates it.",
            "A rival named in only one access row is a structural placeholder rather than a hypothesis players can genuinely test.",
            "Give each live alternate actor a plausible motive, opportunity, and at least one behavior or record players can test, then include a later discriminating fact that resolves the competition.",
            lambda item: item.requirement_code.startswith("deduction_quality")
            and "competing hypothesis" in item.message.casefold(),
    )
    translate(
            "evidence.independent-attribution",
            "Every material actor, payment, and motive link has attributable evidence plus independent corroboration.",
            "An anonymous or ambiguous record can make a central payer, recipient, or causal link underdetermined.",
            "Support each material identity, payment, and motive link with two independent records, or with one attributable record and a separately sourced corroborating fact; keep each record observational rather than conclusion-bearing.",
            lambda item: any(
                marker in item.requirement_code
                for marker in ("payment_attribution", "redundant_proof")
            ),
    )
    translate(
            "seat.balanced-positive-agency",
            "Every required Seat contributes distinct positive evidence and meaningful judgment to the accepted proof chain.",
            "A Seat whose material is freely interchangeable, purely scripted, phase-incoherent, or limited to eliminating a red herring lacks meaningful agency.",
            "Make each Seat's expertise, choices, and unique material necessary to a positive conclusion while preserving a collaborative proof chain and phase-earned role-specific work.",
            lambda item: item.requirement_code.startswith("character_agency"),
    )
    translate(
            "seat.role-distinct-decisions",
            "Each Seat owns a different investigative question and must choose what to disclose, test, or commit before exchanging conclusions.",
            "Mirrored checklists and unrestricted immediate sharing collapse distinct roles into two copies of one procedure.",
            "Replace mirrored step lists with role-specific questions and bounded choices; stage information exchange so each Seat must interpret its own evidence before contributing a distinct conclusion to the joint proof.",
            lambda item: item.requirement_code == "character_agency"
            or any(
                marker in item.requirement_code
                for marker in ("mirrored_instruction", "distinct_contribution")
            ),
    )
    translate(
            "seat.staged-nonduplicative-disclosure",
            "Shared evidence does not restate the private facts whose interpretation and exchange create each Seat's contribution.",
            "An automatically delivered shared record can make a private-selection ritual procedurally elaborate but evidentially optional.",
            "Remove private payment, action, and timing terms from shared records; let shared evidence supply only context or an independent partial trace, so each Seat must interpret and exchange a distinct fact.",
            lambda item: item.requirement_code.startswith("character_agency")
            and any(marker in item.message.casefold() for marker in ("shared", "automatically", "duplicat")),
    )
    translate(
            "facilitation.visible-progression-and-recovery",
            "Players can tell how phases advance and the host has a non-answer recovery path for every proof leg.",
            "Private single-point evidence or invisible phase transitions can stall a complete package.",
            "Provide player-facing phase instructions and host recovery prompts or alternate deliveries that restore progress without revealing the answer.",
            lambda item: item.requirement_code.startswith("facilitation_resilience"),
    )
    translate(
            "facilitation.operational-checkpoints",
            "Every phase has an observable host checkpoint, a validation method, and a graduated fallback that does not reveal the answer.",
            "A player instruction to request the next phase is not an operational recovery system when the host cannot validate or repair a mistaken inference.",
            "Give the host objective advance criteria, a way to validate the players' current claim, and at least two graduated recovery actions for each phase; expose enough of the checkpoint to players that progression is not invisible.",
            lambda item: item.requirement_code == "facilitation_resilience"
            or "phase_recovery" in item.requirement_code,
    )
    translate(
            "facilitation.host-arbitrated-disclosure",
            "Conditional extra disclosure has an objective trigger and a visible host adjudication path.",
            "Players asked to decide for themselves whether an inference is unresolved can either over-disclose or stall in disagreement.",
            "State an observable checkpoint in player materials and instruct the host how to authorize graduated extra disclosure when that checkpoint is unmet.",
            lambda item: "self_arbitrated" in item.requirement_code
            or "adjudication" in item.message.casefold(),
    )
    translate(
            "artifact.in-fiction-boundary",
            "Every player-facing artifact stays in-world and carries only audience-appropriate safety treatment.",
            "Pipeline names, internal model terms, or unmarked record-like assets break immersion and package trust.",
            "Rewrite player-facing companion text and projection summaries as in-world records; remove authoring, emitter, model, and provenance-pipeline vocabulary.",
            lambda item: item.requirement_code.startswith("production_realism")
            and not item.resource_path.startswith("trial/print/")
            and item.resource_path != "trial/schedule.json",
    )
    translate(
            "world.closed-verifiable-claims",
            "Every material claim is chronologically possible, supportable within its delivered time window, and tied to a resolvable actor or record.",
            "Future evidence presented as prior history, phase-inaccessible support, uncovered intervals, and dangling actors weaken a coherent case.",
            "Align represented dates, phase activation, and record contents so players can verify every material claim from evidence available at the appropriate point in play.",
            lambda item: item.requirement_code.startswith("investigative_coherence"),
    )
    translate(
            "world.canonical-record-names",
            "Each evidence object has one canonical in-fiction name wherever characters, dossiers, schedules, and records refer to it.",
            "Synonyms that sound like different producing systems make a single record appear inconsistent.",
            "Choose one in-fiction record name and use it across Seat beliefs, player dossiers, schedules, and evidence summaries.",
            lambda item: "terminology_drift" in item.requirement_code,
    )
    translate(
            "physical.archive-fidelity",
            "Production verification names the exact shipped paths and all rendered text extracts cleanly.",
            "Pre-packaging namespaces or control glyphs make preflight evidence non-re-executable.",
            "Use the shared renderer and trial packager fixes; preserve exact shipped-path preflight and cleanly extractable list markers in the rebuilt package.",
            lambda item: item.requirement_code == "physical.preflight"
            or item.resource_path == "trial/schedule.json"
            and item.requirement_code.startswith("production_realism")
            or item.resource_path == "trial/print/avery-dossier.pdf",
    )
    translate(
            "artifact.single-system-provenance",
            "Each record-like artifact represents one plausible producing system, or explicitly labels a compiled export and every source system within it.",
            "Unlabeled mixtures of camera observations, badge-controller events, and identity directories read as purpose-built evidence rather than an authentic record.",
            "Separate unlike source systems into distinct records, or label the artifact as an in-fiction compiled export with explicit source columns and provenance for every row.",
            lambda item: "document_provenance" in item.requirement_code,
    )
    translate(
            "physical.preflight-coverage",
            "Physical preflight verifies the usability claims it reports, including text size, clipping, table flow, contrast, and print geometry.",
            "A file-exists and non-empty check can overstate production readiness while leaving visual defects unmeasured.",
            "Extend deterministic preflight evidence beyond presence and extraction to cover minimum text size, clipping, table bounds and flow, contrast, and page geometry; report only checks that were actually executed.",
            lambda item: item.requirement_code == "physical.preflight",
    )
    translate(
            "accessibility.equivalent-evidence",
            "An accessible rendition carries every game-relevant fact and comparison available in its visual counterpart.",
            "A player relying on the accessible rendition cannot complete an objective that visual-document readers can complete.",
            "Make every accessible rendition evidence-equivalent to the visual artifact for all player objectives while keeping it in fiction.",
            lambda item: item.requirement_code.startswith("stage5.access"),
    )
    translate(
            "accessibility.party-role-parity",
            "An accessible rendition exposes every party, signatory, and acknowledgment identity needed to inspect the visual instrument's role coherence.",
            "Omitted party identities can hide a forensic inconsistency from readers who rely on the accessible rendition.",
            "Include grantor, grantee, joining spouse, execution signatories, and acknowledged persons from the Artifact Forge public fact projection.",
            lambda item: item.resource_path.endswith("deed-accessible")
            and item.requirement_code.startswith("production_realism")
            and any(marker in item.message.casefold() for marker in ("omit", "identit", "signator")),
    )
    translate(
            "physical.player-material-readability",
            "Printed player materials preserve readable structure, grammatical role agreement, and unambiguous names.",
            "Collapsed tables, role-inconsistent language, or accidental name collisions create production tells and play confusion.",
            "Repair print structure and displayed role language so records scan cleanly and every displayed name has one unambiguous function in the game world.",
            lambda item: item.requirement_code.startswith("production_realism")
            and item.resource_path.startswith("trial/print/"),
    )
    if not translated:
        raise ValueError("failed Evaluation produced no translatable follow-up Findings")

    translated_tuple = tuple(translated)
    existing = {item.requirement_id for item in ledger.snapshot()["requirements"]}
    for item in translated_tuple:
        if item.requirement_id not in existing:
            ledger.register(
                item,
                actor="agent:answer-safe-requirements-translator",
                idempotency_key=f"stage7-followup-requirement-{evaluation.evaluation_id}-{item.requirement_code}",
            )
    if not ledger.verify()["ok"]:
        raise ValueError(ledger.verify())
    return translated_tuple


def _builder_source_package() -> dict[str, Any]:
    scenario = json.loads((DEFAULT_SOURCE / "scenario.json").read_bytes())
    materials = {}
    for resource in scenario["kernel"]["resources"]:
        if "source_path" in resource:
            materials[resource["id"]] = (DEFAULT_SOURCE / resource["source_path"]).read_text()
    return {
        "scenario": scenario,
        "materials": materials,
        "artifact_pins": {
            "execution_date": "1997-10-17",
            "consideration": 425000,
            "grantor_married": True,
            "new_construction": False,
            "partial_exemption": "none",
        },
    }


def _replace_pointer(document: Any, pointer: str, value: Any) -> None:
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError(f"replacement path must be a non-root JSON Pointer: {pointer!r}")
    tokens = [item.replace("~1", "/").replace("~0", "~") for item in pointer[1:].split("/")]
    target = document
    for token in tokens[:-1]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    final = tokens[-1]
    if isinstance(target, list):
        index = int(final)
        if not 0 <= index < len(target):
            raise ValueError(f"replacement index is unavailable: {pointer}")
        target[index] = deepcopy(value)
    else:
        if final not in target:
            raise ValueError(f"replacement member is unavailable: {pointer}")
        target[final] = deepcopy(value)


def _preview_worked_build(
    root: Path,
    *,
    source: dict[str, Any],
    material_overrides: Mapping[str, str],
    artifact_pins: dict[str, Any],
) -> WorkedBuild:
    with TemporaryDirectory(prefix="stage7-proposal-", dir=root) as temporary:
        return build_worked_candidate(
            Path(temporary) / "forge",
            source_mapping=source,
            material_overrides=material_overrides,
            artifact_pins=artifact_pins,
        )


def review_stage7_proposal(
    root: str | Path,
    *,
    proposal_id: str,
    decision: str,
    reason: str,
) -> HumanReview:
    """Persist the repository owner's first-order decision on one Proposal."""
    return _stage7_experiment(root).review_proposal(
        proposal_id=proposal_id,
        reviewer_authority_id="stage7-human-reviewer",
        decision=decision,
        reason=reason,
    )


def prepare_stage7_proposal(
    root: str | Path,
    driver: ModelDriver,
    *,
    requested_model: str,
    task_key: str = "repair-complete-baseline",
    authority_id: str = "stage7-child-builder",
    human_direction: str | None = None,
    require_artifact_pin_change: bool = False,
    require_host_guide_sync: bool = False,
) -> PreparedProposal:
    """Run a blind-safe builder and persist a rebuildable Proposal for human review."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    requirements = record_stage7_requirements(root)
    task_ids = {
        item.task_id for item in ledger.snapshot()["tasks"] if item.task_key == task_key
    }
    existing = [
        item for item in ledger.snapshot()["proposals"] if item.task_id in task_ids
    ]
    if existing:
        proposal = existing[-1]
        proposed_data = workspace.store.read_json(proposal.proposed_data_ref)
        build = _preview_worked_build(
            root,
            source=proposed_data["human_readable_source"],
            material_overrides=proposed_data["material_overrides"],
            artifact_pins=proposed_data["artifact_pins"],
        )
        existing_summary = proposed_data.get(
            "proposal_summary",
            {
                "schema_version": "0.7",
                "status": "awaiting-human-review",
                "proposal_id": proposal.proposal_id,
                "proposed_candidate_id": build.candidate.candidate_id,
                "requirement_codes": [item.requirement_code for item in requirements],
                "standing": None,
            },
        )
        return PreparedProposal(workspace, ledger, proposal, build, existing_summary)

    binding = ledger.snapshot()["trial_bindings"][0]
    instrument = ledger.snapshot()["instruments"][0]
    authority = Authority(authority_id, "agent", "builder", "configured-at-execution")
    ledger.register(
        authority,
        actor="human:operator",
        idempotency_key=f"authority-{authority_id}",
    )
    safe_requirements = {
        "schema_version": "0.7",
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
    source_package = _builder_source_package()
    requirements_ref = workspace.store.put_json(safe_requirements)
    source_ref = workspace.store.put_json(source_package)
    task = Task(
        task_key,
        "fix",
        binding.candidate_id,
        instrument.instrument_id,
        authority.authority_id,
        (),
        {"answer_safe_requirements": requirements_ref, "authoring_package": source_ref},
        "Propose the smallest coherent authoring changes that satisfy every Requirement and any human direction; do not alter canonical culprit, motive, transaction, or answer.",
    )
    ledger.register(task, actor="human:operator", idempotency_key=f"task-{task_key}")
    for label, object_ref in task.input_refs.items():
        ledger.register(
            Exposure(authority.authority_id, object_ref, label, "answer-safe builder input", task.task_id),
            actor="system:exposure-recorder",
            idempotency_key=f"exposure-{task_key}-{label}",
        )
    invocation = ModelInvocation(
        task.task_id,
        authority.authority_id,
        "builder",
        requested_model,
        "Repair the attached authoring package against every attached Requirement. Preserve the canonical mystery answer. Return only the contracted JSON patch; include complete replacement text for each changed material.",
        {
            "requirements": safe_requirements,
            "human_direction": human_direction,
            "constraints": [
                "Do not infer or discuss judge quotes, paths, scores, or prior answers.",
                "Use only replace operations against existing scenario members.",
                "Keep changes minimal and mutually coherent.",
                "The library now emits phase-aware evidence framing automatically.",
                "When human direction requires a visual artifact repair, change at least one supported Artifact Forge pin from its baseline value.",
            ],
        },
        {
            "schema_version": "0.7",
            "output": {
                "scenario_replacements": [{"path": "existing JSON Pointer", "value": "JSON value"}],
                "material_overrides": {"existing non-artifact resource id": "complete replacement text"},
                "artifact_pin_overrides": {"supported pin": "replacement value"},
                "rationale": "concise explanation mapped to Requirement codes",
            },
        },
        (InvocationAttachment("authoring-package.json", "application/json", canonical_json(source_package)),),
        1997,
    )
    receipt_record = execute_model_task(
        ledger,
        invocation,
        driver,
        idempotency_key=f"stage7-model-{task.task_id}",
    )
    parsed = workspace.store.read_json(receipt_record.value.parsed_output_ref)
    required_keys = {"scenario_replacements", "material_overrides", "artifact_pin_overrides", "rationale"}
    if not isinstance(parsed, dict) or set(parsed) != required_keys:
        raise ValueError("builder output does not match the frozen Proposal contract")
    if not isinstance(parsed["scenario_replacements"], list) or not isinstance(parsed["material_overrides"], dict) or not isinstance(parsed["artifact_pin_overrides"], dict) or not isinstance(parsed["rationale"], str):
        raise ValueError("builder output fields have invalid types")
    source = deepcopy(source_package["scenario"])
    normalized_replacement_paths = []
    for operation in parsed["scenario_replacements"]:
        if not isinstance(operation, dict) or set(operation) != {"path", "value"}:
            raise ValueError("scenario replacements require exactly path and value")
        pointer = operation["path"]
        if pointer.startswith("/scenario/"):
            pointer = pointer.removeprefix("/scenario")
        _replace_pointer(source, pointer, operation["value"])
        normalized_replacement_paths.append(pointer)
    material_ids = {
        item["id"] for item in source["kernel"]["resources"] if "source_path" in item
    }
    if any(key not in material_ids or not isinstance(value, str) for key, value in parsed["material_overrides"].items()):
        raise ValueError("material overrides require existing authored resources and complete text")
    interview_reveal = next(
        item for item in source["narrative"]["reveals"]
        if item["id"] == "reveal-interview"
    )
    if require_host_guide_sync:
        host_guide = parsed["material_overrides"].get("host-guide", "").lower()
        if (
            "closing interview" not in host_guide
            or interview_reveal["phase_id"].lower() not in host_guide
        ):
            raise ValueError(
                "human direction requires the host guide to match the revised interview phase"
            )
    changed_reveals = []
    for pointer in normalized_replacement_paths:
        parts = pointer.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["narrative", "reveals"] and parts[3] == "phase_id":
            changed_reveals.append(source["narrative"]["reveals"][int(parts[2])])
    if changed_reveals:
        host_guide = parsed["material_overrides"].get("host-guide")
        if host_guide is None:
            raise ValueError("reveal timing changes require a synchronized host-guide replacement")
        evidence = {item["id"]: item for item in source["narrative"]["evidence"]}
        resources = {item["id"]: item for item in source["kernel"]["resources"]}
        guide_lines = [line.lower() for line in host_guide.splitlines()]
        for reveal in changed_reveals:
            resource_id = evidence[reveal["evidence_id"]]["resource_id"]
            label = resources[resource_id]["label"].lower()
            phase_id = reveal["phase_id"].lower()
            if not any(label in line and phase_id in line for line in guide_lines):
                raise ValueError(
                    f"host guide must place {label!r} in the {phase_id!r} phase"
                )
    allowed_pins = {"execution_date", "consideration", "grantor_married", "new_construction", "partial_exemption"}
    if set(parsed["artifact_pin_overrides"]) - allowed_pins:
        raise ValueError("builder proposed an unsupported Artifact Forge pin")
    if require_artifact_pin_change and (
        not parsed["artifact_pin_overrides"]
        or all(
            source_package["artifact_pins"].get(key) == value
            for key, value in parsed["artifact_pin_overrides"].items()
        )
    ):
        raise ValueError("human direction requires a visual Artifact Forge configuration change")
    pins = {**source_package["artifact_pins"], **parsed["artifact_pin_overrides"]}
    build = _preview_worked_build(
        root,
        source=source,
        material_overrides=parsed["material_overrides"],
        artifact_pins=pins,
    )
    compilation = compile_candidate(build.candidate)
    if compilation.release is None:
        raise ValueError([item.to_mapping() for item in compilation.attempt.findings])
    physical = export_physical(compilation.release)
    trial = prepare_blind_trial(
        compilation.release,
        physical,
        cover_story=instrument.blind_protocol["cover_story"],
    )
    summary = {
        "schema_version": "0.7",
        "status": "awaiting-human-review",
        "baseline_candidate_id": binding.candidate_id,
        "proposed_candidate_id": build.candidate.candidate_id,
        "proposed_release_id": compilation.release.release_id,
        "proposed_physical_export_id": physical.export_id,
        "proposed_blind_trial_id": trial.trial_id,
        "requirement_codes": [item.requirement_code for item in requirements],
        "scenario_replacements": parsed["scenario_replacements"],
        "material_override_ids": sorted(parsed["material_overrides"]),
        "artifact_pin_overrides": parsed["artifact_pin_overrides"],
        "rationale": parsed["rationale"],
        "hard_gates": {
            "compiler.release": True,
            "physical.preflight": bool(physical.preflight["ok"]),
            "blind-trial.verify": True,
            "stage5.access": not any(item.severity == "blocker" for item in build.candidate.advisories),
        },
        "standing": None,
    }
    proposed_data = {
        "title": "The Ashwood Ledger",
        "human_readable_source": source,
        "material_overrides": parsed["material_overrides"],
        "artifact_pins": pins,
    }
    baseline_head = workspace.branches["main"]
    proposal_record = ledger.record_proposal(
        task_id=task.task_id,
        baseline_draft_ref=baseline_head,
        proposed_data=proposed_data,
        requirement_ids=tuple(item.requirement_id for item in requirements),
        builder_authority_id=authority.authority_id,
        model_receipt_id=receipt_record.value.receipt_id,
        rationale=parsed["rationale"],
        actor=f"agent:{authority.principal}",
        idempotency_key=f"stage7-proposal-{task_key}",
    )
    summary = {**summary, "proposal_id": proposal_record.value.proposal_id, "model_receipt_id": receipt_record.value.receipt_id}
    output = root / "output"
    safe_task_key = "".join(
        character if character.isalnum() or character == "-" else "-"
        for character in task_key
    )
    (output / f"stage7-proposal-{safe_task_key}.json").write_bytes(canonical_json(summary))
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    return PreparedProposal(workspace, ledger, proposal_record.value, build, summary)


def _current_authoring_package(workspace: Workspace, draft_ref: str) -> dict[str, Any]:
    revision = workspace.store.read_json(draft_ref)
    data = revision["data"]
    source = deepcopy(data["human_readable_source"])
    overrides = dict(data.get("material_overrides", {}))
    materials = {}
    for resource in source["kernel"]["resources"]:
        if "source_path" not in resource:
            continue
        resource_id = resource["id"]
        materials[resource_id] = overrides.get(
            resource_id,
            (DEFAULT_SOURCE / resource["source_path"]).read_text(),
        )
    return {
        "scenario": source,
        "materials": materials,
        "artifact_pins": dict(data["artifact_pins"]),
    }


def _validate_followup_repair(
    source: Mapping[str, Any],
    materials: Mapping[str, str],
) -> None:
    player_grantees: dict[str, set[str]] = {}
    for policy in source["kernel"]["access_policies"]:
        resource_id = policy["resource"].removeprefix("resource:")
        player_grantees.setdefault(resource_id, set()).update(
            item for item in policy["grantees"] if item.startswith("seat:")
        )
    player_text = "\n".join(
        materials[resource_id]
        for resource_id, grantees in player_grantees.items()
        if grantees and resource_id in materials
    ).casefold()
    banned_pipeline_terms = (
        "artifact forge",
        "canonical game model",
        "deed emitter",
        "trusted package manifest",
        "forged deed",
    )
    if any(item in player_text for item in banned_pipeline_terms):
        raise ValueError("follow-up repair leaks authoring or pipeline language to players")
    conclusion_phrases = (
        "establishes that a staff key was used",
        "supports the proposition",
        "corroborate which transaction",
        "game relevance:",
    )
    if any(item in player_text for item in conclusion_phrases):
        raise ValueError("follow-up repair still supplies evidence conclusions to players")

    resources = {item["id"] for item in source["kernel"]["resources"]}
    interview = materials.get("closing-interview", "").casefold()
    unavailable_alarm_references = ("alarm log", "panel activity sheet", "alarm panel")
    if any(item in interview for item in unavailable_alarm_references) and "alarm-log" not in resources:
        raise ValueError("follow-up repair references an undelivered alarm record")
    if "a man asked" in interview:
        raise ValueError("follow-up repair leaves the intermediary unresolved")

    guide = materials.get("host-guide", "").casefold()
    if not all(item in guide for item in ("opening", "investigation", "resolution", "recovery")):
        raise ValueError("follow-up host guide must define progression and recovery")
    if guide.count("hint") < 2:
        raise ValueError("follow-up host guide requires at least two graduated hints")

    evidence_resources = {
        item["id"]: item["resource_id"] for item in source["narrative"]["evidence"]
    }
    unique_by_seat = {
        seat: {
            resource_id
            for resource_id, grantees in player_grantees.items()
            if grantees == {seat}
        }
        for seat in ("seat:avery", "seat:blake")
    }
    for proof_path in source["narrative"]["proof_paths"]:
        path_resources = {
            evidence_resources[item] for item in proof_path["evidence_ids"]
        }
        if any(not (path_resources & unique_by_seat[seat]) for seat in unique_by_seat):
            raise ValueError(
                "every accepted proof path must require positive evidence from both Seats"
            )


def prepare_stage7_followup_proposal(
    root: str | Path,
    driver: ModelDriver,
    *,
    requested_model: str,
    failed_evaluation_id: str,
    task_key: str,
    authority_id: str,
    human_direction: str | None = None,
    prior_builder_receipt_id: str | None = None,
) -> PreparedProposal:
    """Build the next answer-safe proposal from a failed child panel."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    requirements = record_stage7_followup_requirements(
        root, evaluation_id=failed_evaluation_id
    )
    failed = ledger.get("evaluation", failed_evaluation_id).value
    baseline_head = workspace.branches["main"]
    source_package = _current_authoring_package(workspace, baseline_head)
    prior_builder_patch = None
    prior_patch_ref = None
    if prior_builder_receipt_id is not None:
        prior_receipt = ledger.get("model_receipt", prior_builder_receipt_id).value
        if prior_receipt.role != "builder":
            raise ValueError("prior follow-up attempt must be a builder Model Receipt")
        prior_builder_patch = workspace.store.read_json(prior_receipt.parsed_output_ref)
        prior_patch_ref = workspace.store.put_json(prior_builder_patch)
    authority = Authority(authority_id, "agent", "builder", "configured-at-execution")
    ledger.register(
        authority,
        actor="human:operator",
        idempotency_key=f"authority-{authority_id}",
    )
    safe_requirements = {
        "schema_version": "0.7",
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
    requirements_ref = workspace.store.put_json(safe_requirements)
    source_ref = workspace.store.put_json(source_package)
    excluded = tuple(
        sorted(
            item.authority_id
            for item in ledger.snapshot()["authorities"]
            if item.kind == "agent" and item.role == "judge"
        )
    )
    task_inputs = {
        "answer_safe_requirements": requirements_ref,
        "authoring_package": source_ref,
    }
    if prior_patch_ref is not None:
        task_inputs["prior_builder_patch"] = prior_patch_ref
    task = Task(
        task_key,
        "fix",
        failed.candidate_id,
        failed.instrument_id,
        authority.authority_id,
        excluded,
        task_inputs,
        "Propose a coherent next child that satisfies every answer-safe Requirement without seeing judge findings, quotes, or scores.",
    )
    ledger.register(task, actor="human:operator", idempotency_key=f"task-{task_key}")
    for label, object_ref in task.input_refs.items():
        ledger.register(
            Exposure(
                authority.authority_id,
                object_ref,
                label,
                "answer-safe follow-up builder input",
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
        "Revise the attached current authoring package against every attached Requirement. Preserve the canonical culprit, motive, transaction, execution date, and consideration. Return only the contracted JSON patch, with complete replacement text for every changed material.",
        {
            "requirements": safe_requirements,
            "human_direction": human_direction,
            "prior_builder_patch": prior_builder_patch,
            "constraints": [
                "Do not infer or discuss judge quotes, paths, scores, prior proposals, or hidden answer keys.",
                "Use only replace operations against existing scenario members.",
                "Do not add a resource unless its complete material can be supplied in material_overrides.",
                "Keep player-facing artifacts in fiction and make the inference earned.",
                "Every acceptable proof path must include unique positive evidence from both Seats.",
                "Across acceptable proof paths, no Evidence item may be a dependency shared by every path.",
                "Supply at least two graduated non-answer hints in the host guide.",
            ],
        },
        {
            "schema_version": "0.7",
            "output": {
                "scenario_replacements": [
                    {"path": "existing JSON Pointer", "value": "any JSON value"}
                ],
                "material_overrides": {
                    "existing non-artifact resource id": "complete replacement text"
                },
                "artifact_pin_overrides": {"supported pin": "replacement value"},
                "rationale": "concise explanation mapped to every Requirement code",
            },
        },
        (
            InvocationAttachment(
                "authoring-package.json",
                "application/json",
                canonical_json(source_package),
            ),
        ),
        1997,
    )
    receipt_record = execute_model_task(
        ledger,
        invocation,
        driver,
        idempotency_key=f"stage7-model-{task.task_id}",
    )
    parsed = workspace.store.read_json(receipt_record.value.parsed_output_ref)
    required_keys = {
        "scenario_replacements",
        "material_overrides",
        "artifact_pin_overrides",
        "rationale",
    }
    if not isinstance(parsed, dict) or set(parsed) != required_keys:
        raise ValueError("follow-up builder output does not match the Proposal contract")
    if (
        not isinstance(parsed["scenario_replacements"], list)
        or not isinstance(parsed["material_overrides"], dict)
        or not isinstance(parsed["artifact_pin_overrides"], dict)
        or not isinstance(parsed["rationale"], str)
    ):
        raise ValueError("follow-up builder output fields have invalid types")
    source = deepcopy(source_package["scenario"])
    for operation in parsed["scenario_replacements"]:
        if not isinstance(operation, dict) or set(operation) != {"path", "value"}:
            raise ValueError("scenario replacements require exactly path and value")
        pointer = operation["path"]
        if pointer.startswith("/scenario/"):
            pointer = pointer.removeprefix("/scenario")
        _replace_pointer(source, pointer, operation["value"])
    material_ids = {
        item["id"] for item in source["kernel"]["resources"] if "source_path" in item
    }
    if any(
        key not in material_ids or not isinstance(value, str)
        for key, value in parsed["material_overrides"].items()
    ):
        raise ValueError("material overrides require existing authored text resources")
    materials = {**source_package["materials"], **parsed["material_overrides"]}
    allowed_pins = {
        "execution_date",
        "consideration",
        "grantor_married",
        "new_construction",
        "partial_exemption",
    }
    if set(parsed["artifact_pin_overrides"]) - allowed_pins:
        raise ValueError("follow-up builder proposed an unsupported Artifact Forge pin")
    pins = {**source_package["artifact_pins"], **parsed["artifact_pin_overrides"]}
    _validate_followup_repair(source, materials)
    build = _preview_worked_build(
        root,
        source=source,
        material_overrides=materials,
        artifact_pins=pins,
    )
    compilation = compile_candidate(build.candidate)
    if compilation.release is None:
        raise ValueError([item.to_mapping() for item in compilation.attempt.findings])
    physical = export_physical(compilation.release)
    trial = prepare_blind_trial(
        compilation.release,
        physical,
        cover_story=complete_experience_panel_instrument().blind_protocol["cover_story"],
    )
    proposed_data = {
        "title": "The Ashwood Ledger",
        "human_readable_source": source,
        "material_overrides": materials,
        "artifact_pins": pins,
    }
    proposal_record = ledger.record_proposal(
        task_id=task.task_id,
        baseline_draft_ref=baseline_head,
        proposed_data=proposed_data,
        requirement_ids=tuple(item.requirement_id for item in requirements),
        builder_authority_id=authority.authority_id,
        model_receipt_id=receipt_record.value.receipt_id,
        rationale=parsed["rationale"],
        actor=f"agent:{authority.principal}",
        idempotency_key=f"stage7-proposal-{task_key}",
    )
    summary = {
        "schema_version": "0.7",
        "status": "awaiting-human-review",
        "failed_evaluation_id": failed.evaluation_id,
        "baseline_candidate_id": failed.candidate_id,
        "proposed_candidate_id": build.candidate.candidate_id,
        "proposed_release_id": compilation.release.release_id,
        "proposed_physical_export_id": physical.export_id,
        "proposed_blind_trial_id": trial.trial_id,
        "proposal_id": proposal_record.value.proposal_id,
        "model_receipt_id": receipt_record.value.receipt_id,
        "requirement_codes": [item.requirement_code for item in requirements],
        "scenario_replacements": parsed["scenario_replacements"],
        "material_override_ids": sorted(parsed["material_overrides"]),
        "artifact_pin_overrides": parsed["artifact_pin_overrides"],
        "rationale": parsed["rationale"],
        "hard_gates": {
            "compiler.release": True,
            "physical.preflight": bool(physical.preflight["ok"]),
            "blind-trial.verify": True,
            "stage5.access": not any(
                item.severity == "blocker" for item in build.candidate.advisories
            ),
        },
        "standing": None,
    }
    output = root / "output"
    safe_task_key = "".join(
        character if character.isalnum() or character == "-" else "-"
        for character in task_key
    )
    (output / f"stage7-proposal-{safe_task_key}.json").write_bytes(canonical_json(summary))
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    return PreparedProposal(workspace, ledger, proposal_record.value, build, summary)


def bind_approved_stage7_child(
    root: str | Path,
    *,
    transition_id: str,
) -> BoundChild:
    """Compile and bind the exact human-approved Draft as immutable trial bytes."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    transition_record = ledger.get("transition", transition_id)
    transition = transition_record.value
    child_revision = workspace.store.read_json(transition.child_draft_ref)
    if child_revision.get("kind") != "draft_revision":
        raise ValueError("approved child reference is not a Draft Revision")
    data = child_revision["data"]
    if workspace.branches.get(transition.branch) != transition.child_draft_ref:
        raise ValueError("approved child is no longer the canonical branch head")
    build = _preview_worked_build(
        root,
        source=data["human_readable_source"],
        material_overrides=data["material_overrides"],
        artifact_pins=data["artifact_pins"],
    )
    compilation = compile_candidate(build.candidate)
    if compilation.release is None:
        raise ValueError([item.to_mapping() for item in compilation.attempt.findings])
    release = compilation.release
    physical = export_physical(release)
    instrument = complete_experience_panel_instrument()
    trial = prepare_blind_trial(
        release,
        physical,
        cover_story=instrument.blind_protocol["cover_story"],
    )
    package = CompletePackage(
        build.candidate.candidate_id,
        release.release_id,
        release.bundle_bytes,
        physical.export_id,
        physical.archive_bytes,
        trial,
        {
            "compiler.release": True,
            "physical.preflight": bool(physical.preflight["ok"]),
            "blind-trial.verify": True,
            "stage5.access": not any(
                item.severity == "blocker" for item in build.candidate.advisories
            ),
        },
    )
    binding = _stage7_experiment(root).bind_package(
        package,
        actor="system:stage7-worked-profile",
        idempotency_key=f"trial-binding-approved-child-{transition.transition_id}",
    )
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "approved-child-game-release.zip").write_bytes(release.bundle_bytes)
    (output / "approved-child-physical-package.zip").write_bytes(physical.archive_bytes)
    (output / "approved-child-blind-trial.zip").write_bytes(trial.archive_bytes)
    summary = {
        "schema_version": "0.7",
        "status": "approved-child-bound-awaiting-fresh-panel",
        "transition_id": transition.transition_id,
        "child_draft_ref": transition.child_draft_ref,
        "candidate_id": build.candidate.candidate_id,
        "release_id": release.release_id,
        "physical_export_id": physical.export_id,
        "blind_trial_id": trial.trial_id,
        "binding_id": binding.binding_id,
        "hard_gates": dict(binding.hard_gate_results),
        "standing": None,
    }
    (output / "stage7-approved-child-binding.json").write_bytes(canonical_json(summary))
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    return BoundChild(workspace, ledger, build, release, physical, trial, binding, summary)


def measure_stage7_blind_panel(
    root: str | Path,
    *,
    binding_id: str,
    task_key: str,
    members: tuple[PanelMember, ...],
) -> PanelMeasurement:
    """Measure the worked example through the reusable Experiment API."""
    root = Path(root)
    experiment = _stage7_experiment(root)
    measured = experiment.measure_model_panel(
        binding_id=binding_id,
        task_key=task_key,
        members=tuple(
            ModelPanelMember(
                item.authority_id,
                item.principal,
                item.requested_model,
                item.assigned_lens,
                item.driver,
            )
            for item in members
        ),
        seed=1997,
    )
    evaluation = measured.evaluation
    summary = {
        "schema_version": "0.8",
        "status": "blind-panel-complete",
        "task_id": evaluation.task_id,
        "candidate_id": evaluation.candidate_id,
        "instrument_id": evaluation.instrument_id,
        "evaluation_id": evaluation.evaluation_id,
        "panel_size": len(evaluation.judge_authority_ids),
        "aggregation": experiment.instrument.blind_protocol["panel_aggregation"],
        "individual_scores": measured.individual_scores,
        "scores": dict(evaluation.scores),
        "overall_score": evaluation.overall_score(experiment.instrument),
        "outcome": evaluation.outcome,
        "finding_ids": list(evaluation.finding_ids),
        "standing": None,
    }
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    safe_task_key = "".join(
        character if character.isalnum() or character == "-" else "-"
        for character in task_key
    )
    (output / f"stage7-panel-{safe_task_key}.json").write_bytes(
        canonical_json(summary)
    )
    experiment.export_archive(output / f"ashwood-stage7-panel-{safe_task_key}.ngw")
    verification = experiment.verify()
    if not verification["ok"]:
        raise ValueError(verification)
    return PanelMeasurement(
        experiment.workspace,
        experiment.ledger,
        evaluation,
        measured.individual_scores,
        summary,
    )


def _measure_stage7_blind_panel_legacy(
    root: str | Path,
    *,
    binding_id: str,
    task_key: str,
    members: tuple[PanelMember, ...],
) -> PanelMeasurement:
    """Run one fresh k=3 absolute panel and persist its frozen median score."""
    root = Path(root)
    workspace = Workspace.open(root / "workspace")
    ledger = ClimbLedger(workspace)
    instrument = complete_experience_panel_instrument()
    expected_size = int(instrument.blind_protocol["panel_size"])
    if len(members) != expected_size:
        raise ValueError(f"blind panel requires exactly {expected_size} members")
    member_ids = tuple(item.authority_id for item in members)
    if len(member_ids) != len(set(member_ids)):
        raise ValueError("blind panel Authority identities must be distinct")
    expected_lenses = set(instrument.blind_protocol["panel_lenses"])
    if {item.assigned_lens for item in members} != expected_lenses:
        raise ValueError("blind panel must assign every frozen lens exactly once")

    binding_record = ledger.get("trial_binding", binding_id)
    binding = binding_record.value
    existing_tasks = [item for item in ledger.snapshot()["tasks"] if item.task_key == task_key]
    existing_evaluations = {
        item.task_id: item for item in ledger.snapshot()["evaluations"]
    }
    if existing_tasks:
        if len(existing_tasks) != 1 or existing_tasks[0].task_id not in existing_evaluations:
            raise ValueError("panel Task exists without one completed Evaluation")
        evaluation = existing_evaluations[existing_tasks[0].task_id]
        individual = {
            receipt.authority_id: workspace.store.read_json(receipt.parsed_output_ref)["scores"]
            for receipt in ledger.snapshot()["model_receipts"]
            if receipt.receipt_id in evaluation.model_receipt_ids
        }
        summary = {
            "schema_version": "0.7",
            "status": "blind-panel-complete",
            "task_id": evaluation.task_id,
            "candidate_id": evaluation.candidate_id,
            "instrument_id": evaluation.instrument_id,
            "evaluation_id": evaluation.evaluation_id,
            "panel_size": len(evaluation.judge_authority_ids),
            "aggregation": instrument.blind_protocol["panel_aggregation"],
            "individual_scores": individual,
            "scores": dict(evaluation.scores),
            "overall_score": evaluation.overall_score(instrument),
            "outcome": evaluation.outcome,
            "standing": None,
        }
        return PanelMeasurement(workspace, ledger, evaluation, individual, summary)

    snapshot_before = ledger.snapshot()
    occupied_before = {item.authority_id for item in snapshot_before["authorities"]}
    reused = occupied_before & set(member_ids)
    if reused:
        raise ValueError(f"fresh panel reuses prior Authority identities: {sorted(reused)}")
    if not any(item.instrument_id == instrument.instrument_id for item in snapshot_before["instruments"]):
        ledger.register(
            instrument,
            actor="human:operator",
            idempotency_key="instrument-complete-experience-panel-v1-1",
        )
    for member in members:
        ledger.register(
            Authority(member.authority_id, "agent", "judge", member.principal),
            actor="human:operator",
            idempotency_key=f"authority-{member.authority_id}",
        )
    excluded = tuple(
        sorted(
            item.authority_id
            for item in snapshot_before["authorities"]
            if item.kind == "agent" and item.role in {"builder", "fixer", "judge"}
        )
    )
    task = Task(
        task_key,
        "blind-measure",
        binding.candidate_id,
        instrument.instrument_id,
        members[0].authority_id,
        excluded,
        {
            "blind_trial": binding.blind_trial_ref,
            "trial_binding": binding_record.record_ref,
        },
        "Independently score every frozen dimension; apply the assigned lens without seeing provenance, answers, prior scores, or builder rationale.",
        tuple(item.authority_id for item in members[1:]),
    )
    ledger.register(task, actor="human:operator", idempotency_key=f"task-{task_key}")
    for member in members:
        ledger.register(
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

    trial_bytes = workspace.store.read_bytes(binding.blind_trial_ref)
    trial = load_blind_trial(trial_bytes)
    receipt_ids: list[str] = []
    finding_ids: list[str] = []
    individual_scores: dict[str, dict[str, int]] = {}
    dimensions = {item.dimension_id for item in instrument.dimensions}
    finding_contract = {
        "requirement_code",
        "severity",
        "resource_path",
        "locus",
        "quote",
        "message",
    }
    for member in members:
        invocation = ModelInvocation(
            task.task_id,
            member.authority_id,
            "judge",
            member.requested_model,
            "Judge the attached anonymous Blind Trial under every frozen dimension. Apply your assigned lens as extra scrutiny, not as permission to omit dimensions. Every finding must name exactly one literal archive resource_path and quote an exact span contained in that same file. Return only the contracted JSON evaluation.",
            {
                "cover_story": instrument.blind_protocol["cover_story"],
                "instrument": instrument.to_mapping(),
                "assigned_lens": member.assigned_lens,
                "blindness_warning": "Do not infer provenance, answer keys, builder identity, prior scores, or whether this is a baseline or revision.",
                "standing_warning": "This panel measures package quality only and cannot claim human-play standing.",
            },
            {
                "schema_version": "0.7",
                "output": {
                    "scores": {
                        item.dimension_id: "integer 0..100"
                        for item in instrument.dimensions
                    },
                    "findings": [
                        {
                            "requirement_code": "string",
                            "severity": "major|minor",
                            "resource_path": "one exact path inside Blind Trial",
                            "locus": "precise human-readable locus",
                            "quote": "exact visible span in that resource",
                            "message": "why this is a quality tell",
                        }
                    ],
                },
            },
            (InvocationAttachment("blind-trial.zip", "application/zip", trial_bytes),),
            1997,
        )
        receipt_record = execute_model_task(
            ledger,
            invocation,
            member.driver,
            idempotency_key=f"stage7-panel-model-{task.task_id}-{member.authority_id}",
        )
        parsed = workspace.store.read_json(receipt_record.value.parsed_output_ref)
        if not isinstance(parsed, dict) or set(parsed) != {"scores", "findings"}:
            raise ValueError(f"judge {member.authority_id} output does not match the panel contract")
        scores = parsed["scores"]
        if not isinstance(scores, dict) or set(scores) != dimensions or any(
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100
            for value in scores.values()
        ):
            raise ValueError(f"judge {member.authority_id} scores are incomplete")
        if not isinstance(parsed["findings"], list):
            raise ValueError(f"judge {member.authority_id} findings are not a list")
        individual_scores[member.authority_id] = dict(scores)
        receipt_ids.append(receipt_record.value.receipt_id)
        existing_findings = {item.finding_id for item in ledger.snapshot()["findings"]}
        for index, mapping in enumerate(parsed["findings"]):
            if not isinstance(mapping, dict) or set(mapping) != finding_contract:
                raise ValueError(f"judge {member.authority_id} Finding {index} is invalid")
            verify_trial_quote(trial, mapping["resource_path"], mapping["quote"])
            finding = Finding(
                mapping["requirement_code"],
                mapping["severity"],
                mapping["resource_path"],
                mapping["locus"],
                mapping["quote"],
                mapping["message"],
            )
            if finding.finding_id not in existing_findings:
                ledger.register(
                    finding,
                    actor=f"agent:{member.principal}",
                    idempotency_key=f"stage7-panel-finding-{task.task_id}-{member.authority_id}-{index}",
                )
                existing_findings.add(finding.finding_id)
            if finding.finding_id not in finding_ids:
                finding_ids.append(finding.finding_id)

    aggregated = {
        dimension_id: int(median(scores[dimension_id] for scores in individual_scores.values()))
        for dimension_id in sorted(dimensions)
    }
    provisional = Evaluation(
        task.task_id,
        binding.candidate_id,
        instrument.instrument_id,
        "blind",
        member_ids,
        tuple(receipt_ids),
        aggregated,
        tuple(finding_ids),
        binding.hard_gate_results,
        "fail",
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
        "pass" if evaluation_passes(instrument, provisional) else "fail",
    )
    ledger.register(
        evaluation,
        actor="system:median-panel-scorer-v1",
        idempotency_key=f"stage7-panel-evaluation-{task.task_id}",
    )
    summary = {
        "schema_version": "0.7",
        "status": "blind-panel-complete",
        "task_id": task.task_id,
        "candidate_id": evaluation.candidate_id,
        "instrument_id": instrument.instrument_id,
        "evaluation_id": evaluation.evaluation_id,
        "panel_size": len(members),
        "aggregation": instrument.blind_protocol["panel_aggregation"],
        "individual_scores": individual_scores,
        "scores": dict(evaluation.scores),
        "overall_score": evaluation.overall_score(instrument),
        "outcome": evaluation.outcome,
        "finding_ids": list(evaluation.finding_ids),
        "standing": None,
    }
    safe_task_key = "".join(
        character if character.isalnum() or character == "-" else "-"
        for character in task_key
    )
    output = root / "output"
    (output / f"stage7-panel-{safe_task_key}.json").write_bytes(canonical_json(summary))
    workspace.export_archive(output / f"ashwood-stage7-panel-{safe_task_key}.ngw")
    if not ledger.verify()["ok"] or not workspace.verify()["ok"]:
        raise ValueError({"climb": ledger.verify(), "workspace": workspace.verify()})
    return PanelMeasurement(workspace, ledger, evaluation, individual_scores, summary)


def select_stage7_child(
    root: str | Path,
    *,
    baseline_evaluation_id: str,
    child_evaluation_id: str,
) -> SelectionDecision:
    """Persist the evidence-only Selection Decision under the panel Instrument."""
    root = Path(root)
    experiment = _stage7_experiment(root)
    baseline = experiment.ledger.get("evaluation", baseline_evaluation_id).value
    child = experiment.ledger.get("evaluation", child_evaluation_id).value
    decision = experiment.select(
        baseline_evaluation_id=baseline_evaluation_id,
        child_evaluation_id=child_evaluation_id,
    )
    summary = {
        "schema_version": "0.7",
        "status": "stage7-selection-complete",
        "instrument_id": experiment.instrument.instrument_id,
        "baseline_evaluation_id": baseline.evaluation_id,
        "baseline_score": baseline.overall_score(experiment.instrument),
        "child_evaluation_id": child.evaluation_id,
        "child_score": child.overall_score(experiment.instrument),
        "child_outcome": child.outcome,
        "selection_id": decision.decision_id,
        "selection_outcome": decision.outcome,
        "selected_candidate_id": decision.selected_candidate_id,
        "reason": decision.reason,
        "standing": None,
    }
    output = root / "output"
    (output / "stage7-selection.json").write_bytes(canonical_json(summary))
    experiment.export_archive(output / "ashwood-stage7-selected.ngw")
    verification = experiment.verify()
    if not verification["ok"]:
        raise ValueError(verification)
    return decision


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare the complete Ashwood Ledger baseline for real blind measurement"
    )
    parser.add_argument("root", help="new user-owned experiment directory")
    args = parser.parse_args()
    print(json.dumps(prepare_baseline(args.root).summary, sort_keys=True, indent=2))


def measure_main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a configured JSON-command model against a prepared Stage 7 baseline"
    )
    parser.add_argument("root", help="prepared Stage 7 experiment directory")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--task-key", default="measure-complete-baseline")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = tuple(item for item in args.command if item != "--")
    driver = JsonCommandDriver(command, args.provider, "live-model")
    print(
        json.dumps(
            measure_prepared_baseline(
                args.root,
                driver,
                requested_model=args.model,
                task_key=args.task_key,
            ).summary,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
