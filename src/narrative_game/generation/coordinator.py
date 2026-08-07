"""Resumable orchestration from a Creative Brief to a selected game Candidate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from narrative_game.climb import (
    Authority,
    Exposure,
    InvocationAttachment,
    ModelDriver,
    ModelInvocation,
    Task,
    execute_model_task,
)
from narrative_game.contracts import ArtifactResult, canonical_json, digest_json
from narrative_game.experiment import Experiment, ModelPanelMember

from .artifacts import ArtifactSuiteMaterialization, ArtifactSuiteMaterializer
from .model import CreativeBrief, GenerationPlan, ModelRoleAssignment
from .status import write_generation_status


class GenerationStopped(RuntimeError):
    """The frozen plan reached a terminal rule and preserved why it stopped."""


class InvalidGenerationOutput(ValueError):
    """One receipted creator result failed the exact initial-creation contract."""


@dataclass(frozen=True)
class GenerationDrivers:
    """Configured model effects keyed by the Plan's base Authority identities."""

    by_authority_id: Mapping[str, ModelDriver]

    def for_assignment(self, assignment: ModelRoleAssignment) -> ModelDriver:
        try:
            return self.by_authority_id[assignment.authority_id]
        except KeyError as exc:
            raise ValueError(
                f"no Model Driver configured for {assignment.authority_id}"
            ) from exc


class GenerationCoordinator:
    """Human-triggered, agent-operated controller over one durable Experiment.

    Every mutating step is idempotent. ``run`` may therefore be interrupted and
    called again against the same directory without inventing a second lineage.
    """

    def __init__(
        self,
        experiment: Experiment,
        plan: GenerationPlan,
        brief: CreativeBrief,
    ) -> None:
        self.experiment = experiment
        self.plan = plan
        self.brief = brief
        if experiment.plan.experiment_id != plan.experiment_id:
            raise ValueError("Generation Plan names another Experiment")
        if (
            experiment.plan.profile_id != plan.profile_id
            or experiment.plan.profile_version != plan.profile_version
        ):
            raise ValueError("Generation Plan differs from the Experiment profile")

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        plan: GenerationPlan,
        brief: CreativeBrief,
        instrument: Any,
        component_lock: Mapping[str, Any],
        actor: str = "human:operator",
    ) -> "GenerationCoordinator":
        reviewer = cls._one_assignment(plan, "reviewer")
        experiment = Experiment.create(
            root,
            experiment_id=plan.experiment_id,
            profile_id=plan.profile_id,
            profile_version=plan.profile_version,
            instrument=instrument,
            initial_data={
                "schema_version": plan.schema_version,
                "kind": "generation_brief",
                "brief": brief.to_mapping(),
            },
            component_lock=component_lock,
            reviewer=Authority(
                reviewer.authority_id,
                "agent",
                "reviewer",
                reviewer.authority_id,
            ),
            actor=actor,
        )
        plan_ref = experiment.workspace.store.put_json(plan.to_mapping())
        brief_ref = experiment.workspace.store.put_json(brief.to_mapping())
        experiment.workspace.operational.append(
            "generation_plan_recorded",
            actor=actor,
            payload={
                "plan_ref": plan_ref,
                "brief_ref": brief_ref,
                "plan_id": plan.plan_id,
                "brief_id": brief.brief_id,
            },
            object_refs=(plan_ref, brief_ref),
            idempotency_key=f"generation-plan:{plan.plan_id}",
        )
        experiment.workspace.rebuild_indexes()
        result = cls(experiment, plan, brief)
        write_generation_status(experiment, plan)
        return result

    @classmethod
    def open(cls, root: str | Path) -> "GenerationCoordinator":
        experiment = Experiment.open(root)
        events = [
            event
            for event in experiment.workspace.operational.read()
            if event["event_type"] == "generation_plan_recorded"
        ]
        if len(events) != 1:
            raise ValueError("Workspace must contain exactly one Generation Plan")
        payload = events[0]["payload"]
        plan = GenerationPlan.from_mapping(
            experiment.workspace.store.read_json(payload["plan_ref"])
        )
        brief = CreativeBrief.from_mapping(
            experiment.workspace.store.read_json(payload["brief_ref"])
        )
        return cls(experiment, plan, brief)

    @staticmethod
    def _assignments(plan: GenerationPlan, role: str) -> tuple[ModelRoleAssignment, ...]:
        return tuple(item for item in plan.role_assignments if item.role == role)

    @classmethod
    def _one_assignment(
        cls, plan: GenerationPlan, role: str
    ) -> ModelRoleAssignment:
        matches = cls._assignments(plan, role)
        if len(matches) != 1:
            raise ValueError(f"Generation Plan requires exactly one {role} assignment")
        return matches[0]

    def _event(
        self,
        event_type: str,
        *,
        payload: Mapping[str, Any],
        idempotency_key: str,
        object_refs: tuple[str, ...] = (),
        actor: str = "system:generation",
    ) -> Mapping[str, Any]:
        event = self.experiment.workspace.operational.append(
            event_type,
            actor=actor,
            payload=dict(payload),
            object_refs=object_refs,
            idempotency_key=idempotency_key,
        )
        self.experiment.workspace.rebuild_indexes()
        write_generation_status(self.experiment, self.plan)
        return event

    def _stop(self, reason: str, *, key: str) -> None:
        self._event(
            "generation_stopped",
            payload={"reason": reason},
            idempotency_key=f"generation-stop:{key}",
        )
        raise GenerationStopped(reason)

    @staticmethod
    def _receipt_tokens(receipt: Any) -> int:
        usage = dict(receipt.usage)
        if "total_tokens" in usage:
            return usage["total_tokens"]
        if "input_tokens" in usage and "output_tokens" in usage:
            return usage["input_tokens"] + usage["output_tokens"]
        raise ValueError("Generation Model Drivers must report token usage")

    def _usage(self) -> tuple[int, int]:
        receipts = self.experiment.ledger.snapshot()["model_receipts"]
        return len(receipts), sum(self._receipt_tokens(item) for item in receipts)

    def _check_budget(self, additional_calls: int, *, operation_key: str) -> None:
        calls, tokens = self._usage()
        if calls + additional_calls > self.plan.budget.max_model_calls:
            self._stop("model-call budget exhausted", key=operation_key)
        if tokens >= self.plan.budget.max_tokens:
            self._stop("token budget exhausted", key=operation_key)

    def _validate_receipt(
        self, receipt: Any, assignment: ModelRoleAssignment, *, operation_key: str
    ) -> None:
        if (
            receipt.authority_id != assignment.authority_id
            or receipt.provider != assignment.provider
            or receipt.requested_model != assignment.requested_model
            or receipt.role != assignment.role
            or receipt.agent_id != assignment.agent_id
            or receipt.context_id != assignment.context_id
        ):
            self._stop("model receipt differs from its frozen role assignment", key=operation_key)
        try:
            _, tokens = self._usage()
        except ValueError as exc:
            self._stop(str(exc), key=operation_key)
        if tokens > self.plan.budget.max_tokens:
            self._stop("token budget exceeded", key=operation_key)

    def _initial_attempt_number(self) -> int:
        return 1 + sum(
            event["event_type"] == "generation_invalid_output"
            for event in self.experiment.workspace.operational.read()
        )

    def generate_initial_blueprint(
        self,
        adapter: Any,
        *,
        drivers: GenerationDrivers,
        research: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Generate, independently review, and canonically apply the first Blueprint."""
        self.experiment.require_profile(adapter)
        current = self.experiment.current_draft_data
        if current.get("kind") != "generation_brief":
            return current
        attempt = self._initial_attempt_number()
        assignment = self._one_assignment(self.plan, "builder")
        authority = Authority(
            assignment.authority_id, "agent", "builder", assignment.authority_id
        )
        self.experiment.ledger.register(
            authority,
            actor="human:operator",
            idempotency_key=f"authority-{authority.authority_id}",
        )
        brief_ref = self.experiment.workspace.store.put_json(self.brief.to_mapping())
        input_refs = {"creative_brief": brief_ref}
        attachments = [
            InvocationAttachment(
                "creative-brief.json", "application/json", canonical_json(self.brief.to_mapping())
            )
        ]
        if research is not None:
            research_ref = self.experiment.workspace.store.put_json(research)
            input_refs["research"] = research_ref
            attachments.append(
                InvocationAttachment(
                    "research.json", "application/json", canonical_json(research)
                )
            )
        prior_invalid_outputs = [
            {
                "attempt": event["payload"]["attempt"],
                "model_receipt_id": event["payload"]["model_receipt_id"],
                "reason": event["payload"]["reason"],
            }
            for event in self.experiment.workspace.operational.read()
            if event["event_type"] == "generation_invalid_output"
        ]
        task_key = f"generation-initial-{attempt}"
        task = Task(
            task_key,
            "build",
            self.experiment.current_draft_ref,
            self.experiment.instrument.instrument_id,
            authority.authority_id,
            (),
            input_refs,
            "Create one complete canonical Game Blueprint from the Creative Brief.",
        )
        self.experiment.ledger.register(
            task, actor="human:operator", idempotency_key=f"task-{task_key}"
        )
        for label, object_ref in input_refs.items():
            self.experiment.ledger.register(
                Exposure(
                    authority.authority_id,
                    object_ref,
                    label,
                    "initial creation input",
                    task.task_id,
                ),
                actor="system:exposure-recorder",
                idempotency_key=f"exposure-{task_key}-{label}",
            )
        model_key = f"model-{task.task_id}"
        if self.experiment.ledger.journal.event_for_key(model_key) is None:
            self._check_budget(1, operation_key=task_key)
        invocation = ModelInvocation(
            task.task_id,
            authority.authority_id,
            "builder",
            assignment.requested_model,
            "Create the complete game. Return only the exact initial-creation contract.",
            {
                "creative_brief": self.brief.to_mapping(),
                "research": dict(research or {}),
                "generation_plan": self.plan.to_mapping(),
                "prior_contract_failures": prior_invalid_outputs,
                "remaining_token_budget": max(
                    0, self.plan.budget.max_tokens - self._usage()[1]
                ),
            },
            adapter.creation_contract(),
            tuple(attachments),
            self.plan.seed,
        )
        receipt = execute_model_task(
            self.experiment.ledger,
            invocation,
            drivers.for_assignment(assignment),
            idempotency_key=model_key,
        ).value
        self._validate_receipt(receipt, assignment, operation_key=task_key)
        parsed = self.experiment.workspace.store.read_json(receipt.parsed_output_ref)
        try:
            blueprint = adapter.parse_initial_creation_output(
                self.brief, parsed, research=research
            )
            if tuple(blueprint.artifact_specifications) != tuple(
                self.plan.artifact_plan.specifications
            ):
                raise ValueError(
                    "initial Blueprint Artifact Specifications differ from the frozen Plan"
                )
        except (TypeError, ValueError, KeyError) as exc:
            self._event(
                "generation_invalid_output",
                payload={
                    "attempt": attempt,
                    "model_receipt_id": receipt.receipt_id,
                    "reason": str(exc),
                },
                idempotency_key=f"generation-invalid:{receipt.receipt_id}",
            )
            if attempt >= self.plan.stop_policy.max_consecutive_invalid_outputs:
                self._stop("initial generation produced too many invalid outputs", key="invalid")
            raise InvalidGenerationOutput(str(exc)) from exc
        proposed_data = blueprint.to_mapping()
        proposal = self.experiment.ledger.record_proposal(
            task_id=task.task_id,
            baseline_draft_ref=self.experiment.current_draft_ref,
            proposed_data=proposed_data,
            requirement_ids=(),
            builder_authority_id=authority.authority_id,
            model_receipt_id=receipt.receipt_id,
            rationale=str(parsed["rationale"]),
            actor=f"agent:{authority.principal}",
            idempotency_key=f"proposal-{task_key}",
        ).value
        review = self._review_proposal(
            proposal.proposal_id,
            drivers=drivers,
            operation_key=f"initial-{attempt}",
        )
        if review.decision != "approved":
            self._stop("independent reviewer rejected the initial Blueprint", key=review.review_id)
        self.experiment.apply_review(
            adapter,
            proposal_id=proposal.proposal_id,
            review_id=review.review_id,
            idempotency_key=f"apply-{proposal.proposal_id}",
        )
        self._event(
            "generation_initial_blueprint_applied",
            payload={
                "proposal_id": proposal.proposal_id,
                "review_id": review.review_id,
                "draft_ref": self.experiment.current_draft_ref,
            },
            object_refs=(self.experiment.current_draft_ref,),
            idempotency_key=f"generation-initial-applied:{proposal.proposal_id}",
        )
        return self.experiment.current_draft_data

    def _review_proposal(
        self,
        proposal_id: str,
        *,
        drivers: GenerationDrivers,
        operation_key: str,
    ) -> Any:
        assignment = self._one_assignment(self.plan, "reviewer")
        proposal_record = self.experiment.ledger.get("proposal", proposal_id)
        proposal = proposal_record.value
        proposed = self.experiment.workspace.store.read_json(proposal.proposed_data_ref)
        task_key = f"generation-review-{operation_key}"
        task = Task(
            task_key,
            "review",
            digest_json(proposed),
            self.experiment.instrument.instrument_id,
            assignment.authority_id,
            (proposal.builder_authority_id,),
            {"proposal": proposal_record.record_ref},
            "Independently approve or reject this complete Proposal.",
        )
        self.experiment.ledger.register(
            task, actor="human:operator", idempotency_key=f"task-{task_key}"
        )
        self.experiment.ledger.register(
            Exposure(
                assignment.authority_id,
                proposal_record.record_ref,
                "proposal",
                "independent proposal review",
                task.task_id,
            ),
            actor="system:exposure-recorder",
            idempotency_key=f"exposure-{task_key}-proposal",
        )
        model_key = f"model-{task.task_id}"
        if self.experiment.ledger.journal.event_for_key(model_key) is None:
            self._check_budget(1, operation_key=task_key)
        invocation = ModelInvocation(
            task.task_id,
            assignment.authority_id,
            "reviewer",
            assignment.requested_model,
            "Review the proposed game for contract compliance and internal coherence. Return only the exact decision contract.",
            {
                "creative_brief": self.brief.to_mapping(),
                "proposal_id": proposal_id,
                "independence_warning": "You did not build this Proposal. Review it as an independent authority.",
            },
            {
                "schema_version": self.plan.schema_version,
                "output": {
                    "decision": "approved | rejected",
                    "reason": "non-empty string",
                },
            },
            (
                InvocationAttachment(
                    "proposed-blueprint.json", "application/json", canonical_json(proposed)
                ),
            ),
            self.plan.seed,
        )
        receipt = execute_model_task(
            self.experiment.ledger,
            invocation,
            drivers.for_assignment(assignment),
            idempotency_key=model_key,
        ).value
        self._validate_receipt(receipt, assignment, operation_key=task_key)
        parsed = self.experiment.workspace.store.read_json(receipt.parsed_output_ref)
        if (
            not isinstance(parsed, Mapping)
            or set(parsed) != {"decision", "reason"}
            or parsed["decision"] not in {"approved", "rejected"}
            or not isinstance(parsed["reason"], str)
            or not parsed["reason"].strip()
        ):
            self._stop("independent reviewer returned an invalid decision", key=receipt.receipt_id)
        return self.experiment.review_proposal_agentically(
            proposal_id=proposal_id,
            reviewer_authority_id=assignment.authority_id,
            model_receipt_id=receipt.receipt_id,
            decision=parsed["decision"],
            reason=parsed["reason"],
        )

    def materialize_current_artifacts(
        self,
        materializer: ArtifactSuiteMaterializer,
        *,
        scratch_root: str | Path,
    ) -> ArtifactSuiteMaterialization:
        """Obtain and seal the independently accepted Verismill suite for this Draft."""
        existing = self._artifact_event(self.experiment.current_draft_ref)
        if existing is not None:
            return self._load_artifact_materialization(existing)
        from narrative_game.blueprint import GameBlueprint

        blueprint = GameBlueprint.from_mapping(self.experiment.current_draft_data)
        materialization = materializer.materialize(
            self.plan.artifact_plan,
            blueprint,
            scratch_root=Path(scratch_root),
        )
        materialization.validate_for(self.plan.artifact_plan)
        suite_ref = self.experiment.workspace.store.put_json(
            materialization.suite_attestation
        )
        members: dict[str, Any] = {}
        refs = [suite_ref]
        for artifact_id, result in sorted(materialization.results.items()):
            member = {
                "document_ref": self.experiment.workspace.store.put_bytes(result.document),
                "manifest_ref": self.experiment.workspace.store.put_json(result.manifest),
                "attestation_ref": self.experiment.workspace.store.put_json(result.attestation),
                "request_ref": self.experiment.workspace.store.put_json(result.request),
            }
            refs.extend(member.values())
            members[artifact_id] = member
        self._event(
            "generation_artifact_suite_materialized",
            payload={
                "draft_ref": self.experiment.current_draft_ref,
                "suite_attestation_ref": suite_ref,
                "members": members,
            },
            object_refs=tuple(refs),
            idempotency_key=f"generation-artifacts:{self.experiment.current_draft_ref}",
        )
        return materialization

    def _artifact_event(self, draft_ref: str) -> Mapping[str, Any] | None:
        return next(
            (
                event
                for event in self.experiment.workspace.operational.read()
                if event["event_type"] == "generation_artifact_suite_materialized"
                and event["payload"]["draft_ref"] == draft_ref
            ),
            None,
        )

    def _bound_event(self, draft_ref: str) -> Mapping[str, Any] | None:
        return next(
            (
                event
                for event in reversed(self.experiment.workspace.operational.read())
                if event["event_type"] == "generation_candidate_bound"
                and event["payload"]["draft_ref"] == draft_ref
            ),
            None,
        )

    def _draft_for_candidate(self, candidate_id: str) -> str:
        matches = [
            event["payload"]["draft_ref"]
            for event in self.experiment.workspace.operational.read()
            if event["event_type"] == "generation_candidate_bound"
            and event["payload"]["candidate_id"] == candidate_id
        ]
        if not matches:
            raise ValueError("selected Candidate has no Draft lineage binding")
        if len(set(matches)) != 1:
            raise ValueError("selected Candidate ambiguously names multiple Drafts")
        return matches[0]

    def _align_selected_draft(self) -> None:
        selections = self.experiment.ledger.snapshot()["selections"]
        if not selections:
            return
        decision = selections[-1]
        selected_draft = self._draft_for_candidate(decision.selected_candidate_id)
        current = self.experiment.current_draft_ref
        if current == selected_draft:
            return
        selection_record = self.experiment.ledger.get(
            "selection", decision.decision_id
        )
        self.experiment.workspace.select_revision(
            branch=self.experiment.plan.branch,
            expected_head=current,
            selected_revision=selected_draft,
            selection_ref=selection_record.record_ref,
            actor="system:frozen-selection-rule",
            idempotency_key=f"generation-select-draft:{decision.decision_id}",
        )
        self._event(
            "generation_draft_selected",
            payload={
                "selection_id": decision.decision_id,
                "candidate_id": decision.selected_candidate_id,
                "draft_ref": selected_draft,
            },
            object_refs=(selected_draft, selection_record.record_ref),
            idempotency_key=f"generation-draft-selected:{decision.decision_id}",
        )

    def _load_artifact_materialization(
        self, event: Mapping[str, Any]
    ) -> ArtifactSuiteMaterialization:
        payload = event["payload"]
        results = {}
        for artifact_id, member in payload["members"].items():
            results[artifact_id] = ArtifactResult(
                artifact_id,
                self.experiment.workspace.store.read_bytes(member["document_ref"]),
                self.experiment.workspace.store.read_json(member["manifest_ref"]),
                self.experiment.workspace.store.read_json(member["attestation_ref"]),
                self.experiment.workspace.store.read_json(member["request_ref"]),
            )
        materialization = ArtifactSuiteMaterialization(
            self.experiment.workspace.store.read_json(
                payload["suite_attestation_ref"]
            ),
            results,
        )
        materialization.validate_for(self.plan.artifact_plan)
        return materialization

    def build_current(
        self,
        adapter: Any,
        *,
        scratch_root: str | Path,
        materializer: ArtifactSuiteMaterializer | None = None,
    ) -> tuple[Any, Any]:
        """Compile and bind the current Draft, requiring its accepted artifacts."""
        if self.plan.artifact_plan.specifications:
            event = self._artifact_event(self.experiment.current_draft_ref)
            if event is None:
                if materializer is None:
                    raise ValueError("current Draft requires an Artifact Suite Materializer")
                materialization = self.materialize_current_artifacts(
                    materializer, scratch_root=scratch_root
                )
            else:
                materialization = self._load_artifact_materialization(event)
            if not hasattr(adapter, "with_artifact_suite"):
                raise TypeError("Game Profile Adapter cannot bind Artifact Suite results")
            adapter = adapter.with_artifact_suite(materialization)
        key = f"generation-bind:{self.experiment.current_draft_ref}"
        result = self.experiment.build_and_bind(
            adapter,
            scratch_root=scratch_root,
            idempotency_key=key,
        )
        self._event(
            "generation_candidate_bound",
            payload={
                "draft_ref": self.experiment.current_draft_ref,
                "candidate_id": result[0].candidate_id,
                "binding_id": result[1].binding_id,
            },
            idempotency_key=f"generation-bound:{result[1].binding_id}",
        )
        return result

    def measure_current(
        self,
        *,
        drivers: GenerationDrivers,
        round_index: int,
    ) -> Any:
        """Run a fresh blind panel for the latest bound Candidate."""
        bound_event = self._bound_event(self.experiment.current_draft_ref)
        if bound_event is None:
            raise ValueError("current Draft has no bound Candidate available for measurement")
        binding = self.experiment.ledger.get(
            "trial_binding", bound_event["payload"]["binding_id"]
        ).value
        assignments = self._assignments(self.plan, "judge")
        lenses = tuple(self.experiment.instrument.blind_protocol.get("panel_lenses", ()))
        if not lenses:
            lenses = tuple("complete-experience" for _ in assignments)
        if len(lenses) != len(assignments):
            raise ValueError("Generation Plan judge assignments do not match the blind panel")
        task_key = f"generation-measure-{round_index}"
        existing_tasks = [
            item
            for item in self.experiment.ledger.snapshot()["tasks"]
            if item.task_key == task_key
        ]
        if existing_tasks:
            task = existing_tasks[0]
            missing_calls = sum(
                self.experiment.ledger.journal.event_for_key(
                    f"model-{task.task_id}-{item.authority_id}-round-{round_index}"
                )
                is None
                for item in assignments
            )
        else:
            missing_calls = len(assignments)
        if missing_calls:
            self._check_budget(missing_calls, operation_key=task_key)
        members = tuple(
            ModelPanelMember(
                f"{item.authority_id}-round-{round_index}",
                f"{item.authority_id}:round:{round_index}",
                item.requested_model,
                lens,
                drivers.for_assignment(item),
            )
            for item, lens in zip(assignments, lenses, strict=True)
        )
        measurement = self.experiment.measure_model_panel(
            binding_id=binding.binding_id,
            task_key=task_key,
            members=members,
            seed=self.plan.seed + round_index,
        )
        for assignment, receipt_id in zip(
            assignments, measurement.evaluation.model_receipt_ids, strict=True
        ):
            receipt = self.experiment.ledger.get("model_receipt", receipt_id).value
            # The concrete round Authority is derived from the frozen base assignment.
            if (
                receipt.provider != assignment.provider
                or receipt.requested_model != assignment.requested_model
                or receipt.role != "judge"
                or receipt.agent_id != assignment.agent_id
                or receipt.context_id != assignment.context_id
            ):
                self._stop(
                    "blind panel receipt differs from its frozen model assignment",
                    key=task_key,
                )
            try:
                self._receipt_tokens(receipt)
            except ValueError as exc:
                self._stop(str(exc), key=task_key)
        if self._usage()[1] > self.plan.budget.max_tokens:
            self._stop("token budget exceeded", key=task_key)
        self._event(
            "generation_candidate_measured",
            payload={
                "round": round_index,
                "candidate_id": measurement.evaluation.candidate_id,
                "evaluation_id": measurement.evaluation.evaluation_id,
                "outcome": measurement.evaluation.outcome,
            },
            idempotency_key=f"generation-measured:{measurement.evaluation.evaluation_id}",
        )
        return measurement

    def climb_once(
        self,
        adapter: Any,
        *,
        drivers: GenerationDrivers,
        translator: Any,
        scratch_root: str | Path,
        materializer: ArtifactSuiteMaterializer | None = None,
        human_direction: str | None = None,
    ) -> Any:
        """Create, review, remeasure, and select one child rung."""
        self._align_selected_draft()
        selections = self.experiment.ledger.snapshot()["selections"]
        round_index = len(selections) + 1
        if round_index > self.plan.budget.max_rounds:
            self._stop("climb-round budget exhausted", key="rounds")
        evaluations = self.experiment.ledger.snapshot()["evaluations"]
        if not evaluations:
            raise ValueError("a baseline Evaluation is required before climbing")
        if selections:
            selected_candidate_id = selections[-1].selected_candidate_id
            baseline = next(
                item
                for item in reversed(evaluations)
                if item.candidate_id == selected_candidate_id
            )
        else:
            baseline = evaluations[-1]
        builder = self._one_assignment(self.plan, "builder")
        revision_task_key = f"generation-revision-{round_index}"
        revision_tasks = [
            item
            for item in self.experiment.ledger.snapshot()["tasks"]
            if item.task_key == revision_task_key
        ]
        if len(revision_tasks) > 1:
            raise ValueError("revision Task key identifies more than one Task")
        existing_proposals = [
            item
            for item in self.experiment.ledger.snapshot()["proposals"]
            if revision_tasks and item.task_id == revision_tasks[0].task_id
        ]
        if len(existing_proposals) > 1:
            raise ValueError("revision Task identifies more than one Proposal")
        if existing_proposals:
            proposal = existing_proposals[0]
        else:
            if not revision_tasks or self.experiment.ledger.journal.event_for_key(
                f"model-{revision_tasks[0].task_id}"
            ) is None:
                self._check_budget(1, operation_key=revision_task_key)
            proposal_adapter = adapter
            if self.plan.artifact_plan.specifications:
                event = self._artifact_event(self.experiment.current_draft_ref)
                if event is None:
                    raise ValueError("baseline Draft has no bound Artifact Suite")
                proposal_adapter = adapter.with_artifact_suite(
                    self._load_artifact_materialization(event)
                )
            prepared = self.experiment.propose_revision(
                proposal_adapter,
                evaluation_id=baseline.evaluation_id,
                translator=translator,
                task_key=revision_task_key,
                authority_id=builder.authority_id,
                principal=builder.authority_id,
                requested_model=builder.requested_model,
                driver=drivers.for_assignment(builder),
                scratch_root=scratch_root,
                human_direction=human_direction,
                seed=self.plan.seed + round_index,
            )
            proposal = prepared.proposal
        builder_receipt = self.experiment.ledger.get(
            "model_receipt", proposal.model_receipt_id
        ).value
        self._validate_receipt(
            builder_receipt, builder, operation_key=f"revision-{round_index}"
        )
        reviews = [
            item
            for item in self.experiment.ledger.snapshot()["reviews"]
            if item.proposal_id == proposal.proposal_id
        ]
        if len(reviews) > 1:
            raise ValueError("Proposal identifies more than one Review")
        if reviews:
            review = reviews[0]
            if not hasattr(review, "model_receipt_id"):
                self._stop(
                    "autonomous generation cannot resume from a human Proposal review",
                    key=review.review_id,
                )
            reviewer = self._one_assignment(self.plan, "reviewer")
            review_receipt = self.experiment.ledger.get(
                "model_receipt", review.model_receipt_id
            ).value
            self._validate_receipt(
                review_receipt,
                reviewer,
                operation_key=f"revision-review-{round_index}",
            )
        else:
            review = self._review_proposal(
                proposal.proposal_id,
                drivers=drivers,
                operation_key=f"revision-{round_index}",
            )
        if review.decision != "approved":
            self._stop("independent reviewer rejected the child Proposal", key=review.review_id)
        transitions = [
            item
            for item in self.experiment.ledger.snapshot()["transitions"]
            if item.proposal_id == proposal.proposal_id
        ]
        if len(transitions) > 1:
            raise ValueError("Proposal identifies more than one Transition")
        if transitions:
            if self.experiment.current_draft_ref != transitions[0].child_draft_ref:
                raise ValueError("resumed revision is not the current development Draft")
        else:
            self.experiment.apply_review(
                adapter,
                proposal_id=proposal.proposal_id,
                review_id=review.review_id,
                idempotency_key=f"apply-{proposal.proposal_id}",
            )
        bound_event = self._bound_event(self.experiment.current_draft_ref)
        if bound_event is None:
            _, binding = self.build_current(
                adapter,
                scratch_root=scratch_root,
                materializer=materializer,
            )
        else:
            binding = self.experiment.ledger.get(
                "trial_binding", bound_event["payload"]["binding_id"]
            ).value
        child = self.measure_current(drivers=drivers, round_index=round_index)
        decision = self.experiment.select(
            baseline_evaluation_id=baseline.evaluation_id,
            child_evaluation_id=child.evaluation.evaluation_id,
        )
        self._align_selected_draft()
        self._event(
            "generation_rung_selected",
            payload={
                "round": round_index,
                "binding_id": binding.binding_id,
                "baseline_evaluation_id": baseline.evaluation_id,
                "child_evaluation_id": child.evaluation.evaluation_id,
                "selection_id": decision.decision_id,
                "outcome": decision.outcome,
                "selected_candidate_id": decision.selected_candidate_id,
            },
            idempotency_key=f"generation-selection:{decision.decision_id}",
        )
        return decision

    def run(
        self,
        adapter: Any,
        *,
        drivers: GenerationDrivers,
        translator: Any,
        scratch_root: str | Path,
        research: Mapping[str, Any] | None = None,
        materializer: ArtifactSuiteMaterializer | None = None,
    ) -> Any:
        """Advance without human gates until a Candidate passes or policy stops it."""
        self._align_selected_draft()
        while self.experiment.current_draft_data.get("kind") == "generation_brief":
            try:
                self.generate_initial_blueprint(
                    adapter, drivers=drivers, research=research
                )
            except InvalidGenerationOutput:
                continue
        if self._bound_event(self.experiment.current_draft_ref) is None:
            self.build_current(
                adapter, scratch_root=scratch_root, materializer=materializer
            )
        bound_event = self._bound_event(self.experiment.current_draft_ref)
        assert bound_event is not None
        current_binding = self.experiment.ledger.get(
            "trial_binding", bound_event["payload"]["binding_id"]
        ).value
        current_evaluations = [
            item
            for item in self.experiment.ledger.snapshot()["evaluations"]
            if item.candidate_id == current_binding.candidate_id
        ]
        if not current_evaluations:
            measurement = self.measure_current(drivers=drivers, round_index=0)
        else:
            measurement = current_evaluations[-1]
        outcome = (
            measurement.evaluation.outcome
            if hasattr(measurement, "evaluation")
            else measurement.outcome
        )
        while outcome != "pass":
            decision = self.climb_once(
                adapter,
                drivers=drivers,
                translator=translator,
                scratch_root=scratch_root,
                materializer=materializer,
            )
            selected = next(
                item
                for item in reversed(self.experiment.ledger.snapshot()["evaluations"])
                if item.candidate_id == decision.selected_candidate_id
            )
            outcome = selected.outcome
        selections = self.experiment.ledger.snapshot()["selections"]
        selected_candidate_id = (
            selections[-1].selected_candidate_id
            if selections
            else current_binding.candidate_id
        )
        selected = next(
            item
            for item in reversed(self.experiment.ledger.snapshot()["evaluations"])
            if item.candidate_id == selected_candidate_id and item.outcome == "pass"
        )
        self._event(
            "generation_completed",
            payload={
                "candidate_id": selected.candidate_id,
                "evaluation_id": selected.evaluation_id,
            },
            idempotency_key=f"generation-completed:{selected.candidate_id}",
        )
        write_generation_status(self.experiment, self.plan)
        return selected


__all__ = [
    "GenerationCoordinator",
    "GenerationDrivers",
    "GenerationStopped",
    "InvalidGenerationOutput",
]
