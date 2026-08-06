"""Human-triggered recording and standing for first-order play evidence."""

from __future__ import annotations

from statistics import median
from typing import Any, Callable, Mapping

from narrative_game.climb import (
    Authority,
    Evaluation,
    Finding,
    Requirement,
    StandingAttestation,
)
from narrative_game.climb.selection import evaluation_passes
from narrative_game.contracts import digest_bytes, digest_json
from narrative_game.experiment import Experiment
from narrative_game.runtime import SessionHistory
from narrative_game.runtime.runtime import verify_history

from .model import (
    EvidenceComparison,
    ParticipantConsent,
    PlayObservation,
    PlaytestProtocol,
    PlaytestRun,
)


PlaytestTranslator = Callable[
    [PlaytestRun, tuple[Finding, ...]], tuple[Requirement, ...]
]


class PlaytestProgram:
    """Persist exact human play evidence inside one Experiment lineage."""

    def __init__(self, experiment: Experiment):
        self.experiment = experiment
        self.ledger = experiment.ledger
        self.store = experiment.workspace.store

    def freeze_protocol(
        self,
        *,
        binding_id: str,
        name: str,
        version: str,
        consent_version: str,
        minimum_fresh_runs: int = 2,
        minimum_participants_per_run: int = 2,
        required_observation_categories: tuple[str, ...] = (
            "comprehension",
            "agency",
            "pacing",
        ),
        require_model_comparison: bool = True,
        model_human_delta_tolerance: int = 10,
        required_response_stages: tuple[str, ...] = (),
        individual_response_stages: tuple[str, ...] = (),
        require_facilitator_phase_observations: bool = False,
        defect_owner_taxonomy: tuple[str, ...] = (),
    ) -> PlaytestProtocol:
        """Freeze protocol and package identity before recruiting a run."""
        binding = self.ledger.get("trial_binding", binding_id).value
        protocol = PlaytestProtocol(
            name,
            version,
            binding.binding_id,
            self.experiment.instrument.instrument_id,
            consent_version,
            minimum_fresh_runs,
            minimum_participants_per_run,
            required_observation_categories,
            require_model_comparison,
            model_human_delta_tolerance,
            required_response_stages,
            individual_response_stages,
            require_facilitator_phase_observations,
            defect_owner_taxonomy,
        )
        return self.ledger.register(
            protocol,
            actor="human:playtest-operator",
            idempotency_key=f"playtest-protocol-{protocol.protocol_id}",
        ).value

    def record_run(
        self,
        *,
        protocol_id: str,
        run_key: str,
        session_history: SessionHistory,
        production_receipt: Mapping[str, Any],
        participants: tuple[Authority, ...],
        facilitator: Authority,
        observers: tuple[Authority, ...],
        consent_responses: Mapping[str, Mapping[str, Any]],
        observations: tuple[Mapping[str, Any], ...],
        scores: Mapping[str, int],
        idempotency_key: str,
    ) -> PlaytestRun:
        """Record one completed live Session without converting humans to model calls."""
        protocol = self.ledger.get("playtest_protocol", protocol_id).value
        binding = self.ledger.get("trial_binding", protocol.binding_id).value
        if (
            len(participants) < protocol.minimum_participants_per_run
            or len({item.principal for item in participants}) != len(participants)
        ):
            raise ValueError("Playtest Run requires the frozen number of distinct humans")
        verify_history(session_history)
        if session_history.mode != "live" or session_history.release_id != binding.release_id:
            raise ValueError("fresh Playtest Run requires a live Session for the exact Release")
        if not any(
            item.event_type == "resolution-recorded"
            for item in session_history.ordered_events
        ):
            raise ValueError("Playtest Run requires a completed resolved Session")
        if production_receipt.get("release_id") != binding.release_id or production_receipt.get(
            "physical_export_id"
        ) != binding.physical_export_id:
            raise ValueError("production receipt differs from the frozen playtest package")
        authorities = (*participants, facilitator, *observers)
        if (
            len({item.principal for item in authorities}) != len(authorities)
            or len({item.authority_id for item in authorities}) != len(authorities)
        ):
            raise ValueError("one human cannot occupy multiple Playtest Run roles")
        authority_ids = {item.authority_id for item in authorities}
        genesis = session_history.ordered_events[0]
        session_actor_ids = {
            item["actor"]["id"] for item in genesis.payload["bindings"]
        }
        host_viewer_ids = {
            item["viewer_id"]
            for item in genesis.payload["viewers"]
            if item["role"] == "host"
        }
        if {item.principal for item in participants} != session_actor_ids:
            raise ValueError("participant Authorities must identify the Session Actors")
        if facilitator.principal not in host_viewer_ids:
            raise ValueError("facilitator Authority must identify the Session host")
        if set(consent_responses) != {item.authority_id for item in authorities}:
            raise ValueError("every Playtest Run human requires one consent response")
        consents = []
        for authority in authorities:
            response = consent_responses[authority.authority_id]
            if response.get("decision") != "consented":
                raise ValueError(f"Playtest consent is not affirmative: {authority.authority_id}")
            required_scopes = {"record-observations", "retain-anonymized-quotes"}
            if authority.role == "participant":
                required_scopes.add("participate")
            if (
                response.get("consent_version") != protocol.consent_version
                or not required_scopes <= set(response.get("scopes", ()))
            ):
                raise ValueError(
                    f"Playtest consent version or scope is incomplete: {authority.authority_id}"
                )
            response_ref = digest_json(response)
            consents.append(
                ParticipantConsent(
                    authority.authority_id,
                    str(response["consent_version"]),
                    tuple(str(item) for item in response["scopes"]),
                    response_ref,
                )
            )
        session_bytes = session_history.to_bytes()
        session_ref = digest_bytes(session_bytes)
        production_ref = digest_json(production_receipt)
        phase_ids = {item.represented_phase_id for item in session_history.ordered_events}
        play_observations = []
        finding_values = []
        for index, raw in enumerate(observations):
            if str(raw["phase_id"]) not in phase_ids:
                raise ValueError(f"Play Observation names a Phase absent from the Session: {raw['phase_id']}")
            response_ref = digest_json(raw)
            observation = PlayObservation(
                str(raw["authority_id"]),
                str(raw["observer_role"]),
                str(raw["phase_id"]),
                str(raw["category"]),
                str(raw["quote"]),
                str(raw["note"]),
                response_ref,
                str(raw.get("response_stage", "in_play")),
                (
                    int(raw["elapsed_seconds"])
                    if raw.get("elapsed_seconds") is not None else None
                ),
                str(raw.get("instrument_item_id", "")),
                (
                    str(raw["defect_owner"])
                    if raw.get("defect_owner") is not None else None
                ),
            )
            if observation.authority_id not in authority_ids:
                raise ValueError("Play Observation authority is outside this Run")
            if protocol.required_response_stages and not observation.instrument_item_id.strip():
                raise ValueError("Play Observation requires one frozen rubric item")
            play_observations.append(observation)
            if raw.get("finding") is not None:
                value = raw["finding"]
                if (
                    protocol.defect_owner_taxonomy
                    and observation.defect_owner not in protocol.defect_owner_taxonomy
                ):
                    raise ValueError("Playtest Finding requires one frozen defect owner")
                finding = Finding(
                    str(value["requirement_code"]),
                    str(value["severity"]),
                    str(value["resource_path"]),
                    str(value["locus"]),
                    str(value["quote"]),
                    str(value["message"]),
                )
                finding_values.append((index, observation.authority_id, finding))
        observed_categories = {item.category for item in play_observations}
        if not set(protocol.required_observation_categories) <= observed_categories:
            raise ValueError("Playtest Run does not cover every frozen observation category")
        observed_stages = {item.response_stage for item in play_observations}
        if not set(protocol.required_response_stages) <= observed_stages:
            raise ValueError("Playtest Run does not cover every frozen response stage")
        for participant in participants:
            participant_stages = {
                item.response_stage for item in play_observations
                if item.authority_id == participant.authority_id
            }
            if not set(protocol.individual_response_stages) <= participant_stages:
                raise ValueError("every participant requires the frozen individual responses")
        if protocol.require_facilitator_phase_observations:
            observed_phases = {
                item.phase_id for item in play_observations
                if item.authority_id == facilitator.authority_id
                and item.response_stage == "in_play"
                and item.elapsed_seconds is not None
                and item.elapsed_seconds >= 0
            }
            if not phase_ids <= observed_phases:
                raise ValueError("facilitator requires a timestamped observation in every played Phase")
        hard_gates = dict(binding.hard_gate_results)
        expected_scores = {
            item.dimension_id for item in self.experiment.instrument.dimensions
        }
        if (
            set(scores) != expected_scores
            or any(
                isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 100
                for item in scores.values()
            )
        ):
            raise ValueError("Playtest scores must cover the frozen 0-100 Instrument")
        synthetic = Evaluation(
            "playtest",
            binding.candidate_id,
            protocol.instrument_id,
            "blind",
            (),
            (),
            scores,
            (),
            hard_gates,
            "pending",
        )
        outcome = (
            "pass"
            if evaluation_passes(self.experiment.instrument, synthetic)
            else "fail"
        )
        run = PlaytestRun(
            protocol.protocol_id,
            run_key,
            binding.release_id,
            binding.physical_export_id,
            session_ref,
            production_ref,
            tuple(item.authority_id for item in participants),
            facilitator.authority_id,
            tuple(item.authority_id for item in observers),
            tuple(consents),
            tuple(play_observations),
            scores,
            tuple(item.finding_id for _, _, item in finding_values),
            hard_gates,
            outcome,
        )
        unique_findings = {
            finding.finding_id: (index, authority_id, finding)
            for index, authority_id, finding in finding_values
        }
        self.ledger.preflight(
            (*authorities, *(item[2] for item in unique_findings.values()), run)
        )
        for response, consent in zip(
            (consent_responses[item.authority_id] for item in authorities),
            consents,
            strict=True,
        ):
            if self.store.put_json(response) != consent.response_ref:
                raise RuntimeError("consent content identity changed after preflight")
        if self.store.put_bytes(session_bytes) != session_ref:
            raise RuntimeError("Session content identity changed after preflight")
        if self.store.put_json(production_receipt) != production_ref:
            raise RuntimeError("production content identity changed after preflight")
        for raw, observation in zip(observations, play_observations, strict=True):
            if self.store.put_json(raw) != observation.response_ref:
                raise RuntimeError("observation content identity changed after preflight")
        for authority in authorities:
            self.ledger.register(
                authority,
                actor="human:playtest-operator",
                idempotency_key=f"playtest-authority-{authority.authority_id}",
            )
        existing_finding_ids = {
            item.finding_id for item in self.ledger.snapshot()["findings"]
        }
        for index, authority_id, finding in unique_findings.values():
            if finding.finding_id not in existing_finding_ids:
                self.ledger.register(
                    finding,
                    actor=f"human:{authority_id}",
                    idempotency_key=f"playtest-finding-{idempotency_key}-{index}",
                )
        return self.ledger.register(
            run,
            actor="human:playtest-facilitator",
            idempotency_key=idempotency_key,
        ).value

    def translate_requirements(
        self,
        *,
        run_id: str,
        translator: PlaytestTranslator,
    ) -> tuple[Requirement, ...]:
        """Translate quoted play Findings to answer-safe builder Requirements."""
        run = self.ledger.get("playtest_run", run_id).value
        finding_by_id = {
            item.finding_id: item for item in self.ledger.snapshot()["findings"]
        }
        findings = tuple(finding_by_id[item] for item in run.finding_ids)
        requirements = translator(run, findings)
        for requirement in requirements:
            if not requirement.source_finding_ids or not set(
                requirement.source_finding_ids
            ) <= set(run.finding_ids):
                raise ValueError("Playtest Requirement must cite this Run's Findings")
            existing = {
                item.requirement_id
                for item in self.ledger.snapshot()["requirements"]
            }
            if requirement.requirement_id not in existing:
                self.ledger.register(
                    requirement,
                    actor="human:playtest-operator",
                    idempotency_key=f"playtest-requirement-{requirement.requirement_id}",
                )
        return requirements

    def compare_with_model(
        self,
        *,
        protocol_id: str,
        model_evaluation_id: str,
        playtest_run_ids: tuple[str, ...],
    ) -> EvidenceComparison:
        """Persist deterministic divergence without treating model scores as human play."""
        comparison = self._build_comparison(
            protocol_id=protocol_id,
            model_evaluation_id=model_evaluation_id,
            playtest_run_ids=playtest_run_ids,
        )
        return self.ledger.register(
            comparison,
            actor="system:evidence-comparison",
            idempotency_key=f"evidence-comparison-{comparison.comparison_id}",
        ).value

    def _build_comparison(
        self,
        *,
        protocol_id: str,
        model_evaluation_id: str,
        playtest_run_ids: tuple[str, ...],
    ) -> EvidenceComparison:
        """Materialize the exact comparison without mutating the Experiment."""
        if not playtest_run_ids:
            raise ValueError("Evidence Comparison requires at least one Playtest Run")
        protocol = self.ledger.get("playtest_protocol", protocol_id).value
        binding = self.ledger.get("trial_binding", protocol.binding_id).value
        evaluation = self.ledger.get("evaluation", model_evaluation_id).value
        runs = tuple(
            self.ledger.get("playtest_run", item).value for item in playtest_run_ids
        )
        dimensions = {}
        for dimension in self.experiment.instrument.dimensions:
            human_median = median(
                item.scores[dimension.dimension_id] for item in runs
            )
            model_score = evaluation.scores[dimension.dimension_id]
            dimensions[dimension.dimension_id] = {
                "model": model_score,
                "human_median": human_median,
                "delta": human_median - model_score,
            }
        conclusion = (
            "divergent"
            if any(
                abs(item["delta"]) > protocol.model_human_delta_tolerance
                for item in dimensions.values()
            )
            else "aligned"
        )
        comparison = EvidenceComparison(
            protocol.protocol_id,
            binding.candidate_id,
            protocol.instrument_id,
            evaluation.evaluation_id,
            playtest_run_ids,
            dimensions,
            conclusion,
        )
        return comparison

    @staticmethod
    def _build_accepted_standing(
        comparison: EvidenceComparison,
        reviewer: Authority,
        statement: str,
    ) -> StandingAttestation:
        if not statement.strip():
            raise ValueError("Standing review requires a nonempty human statement")
        return StandingAttestation(
            comparison.candidate_id,
            "accepted",
            (comparison.model_evaluation_id,),
            (
                "fresh-human-play",
                "model-human-comparison",
                "independent-standing-review",
            ),
            reviewer.authority_id,
            statement,
            comparison.playtest_run_ids,
            comparison.comparison_id,
        )

    def _reviewer_is_new(self, reviewer: Authority) -> bool:
        existing = {
            item.authority_id: item for item in self.ledger.snapshot()["authorities"]
        }
        if reviewer.authority_id in existing:
            if existing[reviewer.authority_id] != reviewer:
                raise ValueError(
                    "Standing reviewer identity conflicts with an existing Authority"
                )
            return False
        return True

    def issue_accepted_standing(
        self,
        *,
        comparison_id: str,
        reviewer: Authority,
        statement: str,
    ) -> StandingAttestation:
        """Issue accepted Standing only through independent human review."""
        reviewer_is_new = self._reviewer_is_new(reviewer)
        comparison = self.ledger.get("evidence_comparison", comparison_id).value
        standing = self._build_accepted_standing(comparison, reviewer, statement)
        self.ledger.preflight((reviewer, standing))
        if reviewer_is_new:
            self.ledger.register(
                reviewer,
                actor="human:playtest-operator",
                idempotency_key=f"standing-reviewer-{reviewer.authority_id}",
            )
        return self.ledger.register(
            standing,
            actor=f"human:{reviewer.principal}",
            idempotency_key=f"accepted-standing-{standing.attestation_id}",
        ).value

    def finalize_accepted_standing(
        self,
        *,
        protocol_id: str,
        model_evaluation_id: str,
        playtest_run_ids: tuple[str, ...],
        reviewer: Authority,
        statement: str,
    ) -> tuple[EvidenceComparison, StandingAttestation]:
        """Preflight and persist comparison plus independent accepted Standing."""
        reviewer_is_new = self._reviewer_is_new(reviewer)
        comparison = self._build_comparison(
            protocol_id=protocol_id,
            model_evaluation_id=model_evaluation_id,
            playtest_run_ids=playtest_run_ids,
        )
        standing = self._build_accepted_standing(comparison, reviewer, statement)
        self.ledger.preflight((reviewer, comparison, standing))
        if reviewer_is_new:
            self.ledger.register(
                reviewer,
                actor="human:playtest-operator",
                idempotency_key=f"standing-reviewer-{reviewer.authority_id}",
            )
        persisted_comparison = self.ledger.register(
            comparison,
            actor="system:evidence-comparison",
            idempotency_key=f"evidence-comparison-{comparison.comparison_id}",
        ).value
        persisted_standing = self.ledger.register(
            standing,
            actor=f"human:{reviewer.principal}",
            idempotency_key=f"accepted-standing-{standing.attestation_id}",
        ).value
        return persisted_comparison, persisted_standing
