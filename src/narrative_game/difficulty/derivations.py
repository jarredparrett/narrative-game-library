"""Pure derivations from canonical Episodes into bounded difficulty evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json
from narrative_game.simulation import EpisodeArchive, verify_episode

from .contracts import (
    DIFFICULTY_CONTRACT_CATALOG,
    CanonicalEvidenceSpan,
    EpisodeEvidencePackage,
    EvidenceViewManifest,
    EvidenceViewSpan,
    SemanticFixtureExpectation,
    VerificationStatus,
)
from .instrument import DISCOVERY_ALLOW, EvidenceGrant


DISCOVERY_DENIED_FIELDS = (
    "acceptable_proof_path_ids",
    "agent_id",
    "context_id",
    "correct",
    "correct_hypothesis_id",
    "model",
    "model_name",
    "policy_id",
    "proof_path_id",
    "provider",
    "response_id",
    "terminal_state_hash",
    "trusted_reason",
    "truth_model",
)


def build_episode_evidence_package(
    release: GameRelease,
    archive: EpisodeArchive,
) -> EpisodeEvidencePackage:
    """Preserve every canonical Episode surface as an addressable span."""
    spans = [
        CanonicalEvidenceSpan(
            "archive:metadata",
            "archive-metadata",
            0,
            ("verification",),
            {
                "episode_id": archive.episode_id,
                "release_id": archive.release_id,
                "episode_seed": archive.episode_seed,
                "config": archive.config.to_mapping(),
                "lineup": archive.lineup.to_mapping(),
                "version_locks": dict(sorted(archive.version_locks.items())),
                "realized_seat_order": list(archive.realized_seat_order),
                "violations": list(archive.violations),
                "termination_reason": archive.termination_reason,
                "terminal_state_hash": archive.terminal_state_hash,
                "trace_head": archive.trace_head,
            },
        )
    ]
    for event in archive.events:
        spans.append(
            CanonicalEvidenceSpan(
                f"arena:{event.sequence:04d}",
                "arena-event",
                event.sequence,
                event.visibility,
                event.to_mapping(),
            )
        )
    for event in archive.session_history.ordered_events:
        spans.append(
            CanonicalEvidenceSpan(
                f"session:{event.sequence:04d}",
                "session-event",
                event.sequence,
                ("verification",),
                event.to_mapping(),
            )
        )
    for index, receipt in enumerate(archive.session_history.receipts, 1):
        spans.append(
            CanonicalEvidenceSpan(
                f"session-receipt:{index:04d}",
                "session-receipt",
                index,
                ("verification",),
                receipt.to_mapping(),
            )
        )
    for trajectory in sorted(archive.trajectories, key=lambda item: item.actor_id):
        for step in trajectory.steps:
            spans.append(
                CanonicalEvidenceSpan(
                    f"trajectory:{trajectory.actor_id}:{step.turn:04d}",
                    "trajectory-step",
                    step.turn,
                    (trajectory.actor_id,),
                    {
                        "actor_id": trajectory.actor_id,
                        "role": trajectory.role,
                        "policy": trajectory.policy.to_mapping(),
                        "step": step.to_mapping(),
                    },
                )
            )
    findings = verify_episode(release, archive)
    span_ids = tuple(item.span_id for item in spans)
    verification = VerificationStatus(
        "complete-episode-replay",
        "verified" if not findings else "invalid",
        "narrative-episode-verifier.1",
        span_ids,
        tuple(findings),
    )
    return EpisodeEvidencePackage(
        archive.episode_id,
        archive.release_id,
        digest_bytes(archive.to_bytes()),
        DIFFICULTY_CONTRACT_CATALOG.catalog_id,
        tuple(spans),
        verification,
    )


def _redact(
    value: Any,
    *,
    path: str,
    denied: frozenset[str],
    replacements: Mapping[str, str],
) -> tuple[Any, tuple[str, ...]]:
    redacted = []
    if isinstance(value, Mapping):
        result = {}
        for key in sorted(value):
            child_path = f"{path}.{key}" if path else str(key)
            if key in denied:
                redacted.append(child_path)
                continue
            child, child_redactions = _redact(
                value[key], path=child_path, denied=denied, replacements=replacements
            )
            result[key] = child
            redacted.extend(child_redactions)
        return result, tuple(redacted)
    if isinstance(value, (list, tuple)):
        result = []
        for index, item in enumerate(value):
            child, child_redactions = _redact(
                item,
                path=f"{path}[{index}]",
                denied=denied,
                replacements=replacements,
            )
            result.append(child)
            redacted.extend(child_redactions)
        return result, tuple(redacted)
    if isinstance(value, str) and value in replacements:
        return replacements[value], (path,)
    return value, ()


def _participant_replacements(package: EpisodeEvidencePackage) -> dict[str, str]:
    metadata = next(
        span.content for span in package.spans if span.source_kind == "archive-metadata"
    )
    lineup = metadata["lineup"]
    replacements = {}
    for index, assignment in enumerate(
        sorted(lineup["seats"], key=lambda item: str(item["seat_id"])), 1
    ):
        policy = assignment["policy"]
        slot = f"participant:seat-{index:03d}"
        replacements[f"seat:{assignment['seat_id']}:{policy['policy_id']}"] = slot
        replacements[str(policy["model"])] = "redacted:model"
        for key in ("policy_id", "agent_id", "context_id"):
            replacements[str(policy[key])] = slot
    host = lineup["host"]
    replacements[f"host:{host['policy_id']}"] = "participant:host"
    replacements[str(host["model"])] = "redacted:model"
    for key in ("policy_id", "agent_id", "context_id"):
        replacements[str(host[key])] = "participant:host"
    return replacements


def build_discovery_view(package: EpisodeEvidencePackage) -> EvidenceViewManifest:
    """Project replay evidence without canonical truth or fixture answers."""
    denied = frozenset(DISCOVERY_DENIED_FIELDS)
    replacements = _participant_replacements(package)
    spans = []
    for source in package.spans:
        content, redacted = _redact(
            source.content,
            path="",
            denied=denied,
            replacements=replacements,
        )
        spans.append(EvidenceViewSpan(source.span_id, content, redacted))
    return EvidenceViewManifest(
        "difficulty-d0.discovery-preflight.1",
        package.package_id,
        tuple(spans),
        DISCOVERY_DENIED_FIELDS,
    )


def _contains(value: Any, required: Any) -> bool:
    if isinstance(required, Mapping):
        return isinstance(value, Mapping) and all(
            key in value and _contains(value[key], child)
            for key, child in required.items()
        )
    if isinstance(required, (list, tuple)):
        return isinstance(value, (list, tuple)) and all(
            any(_contains(candidate, item) for candidate in value) for item in required
        )
    return value == required


def expectation_is_satisfied(
    package: EpisodeEvidencePackage,
    expectation: SemanticFixtureExpectation,
) -> bool:
    """Evaluate a fixture oracle outside every answer-safe Evidence View."""
    return any(
        span.source_kind == expectation.source_kind
        and span.content.get("event_type") == expectation.event_type
        and _contains(span.content, expectation.required_content)
        for span in package.spans
    )


@dataclass(frozen=True)
class FactualGraphs:
    """Deterministic structural graphs derived before any agent sees an Episode."""

    episode_package_ref: str
    actor_action_resource: tuple[Mapping[str, Any], ...]
    knowledge_state: tuple[Mapping[str, Any], ...]
    milestone_obligation: tuple[Mapping[str, Any], ...]
    claimed_vs_verified: tuple[Mapping[str, Any], ...]
    schema_version: str = "factual-graphs.1"

    @property
    def graphs_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_package_ref": self.episode_package_ref,
            "actor_action_resource": [dict(item) for item in self.actor_action_resource],
            "knowledge_state": [dict(item) for item in self.knowledge_state],
            "milestone_obligation": [dict(item) for item in self.milestone_obligation],
            "claimed_vs_verified": [dict(item) for item in self.claimed_vs_verified],
        }


def _public_content(value: Mapping[str, Any]) -> dict[str, Any]:
    content, _ = _redact(
        value,
        path="",
        denied=frozenset(DISCOVERY_DENIED_FIELDS),
        replacements={},
    )
    return json.loads(canonical_json(content))


def derive_factual_graphs(package: EpisodeEvidencePackage) -> FactualGraphs:
    """Derive fact-only adjacency lists without causal or correctness judgments."""
    actor_action_resource = []
    knowledge_state = []
    milestone_obligation = []
    claimed_vs_verified = []
    for span in sorted(package.spans, key=lambda item: item.span_id):
        content = _public_content(span.content)
        actor = content.get("actor_id") or content.get("actor")
        event_type = content.get("event_type") or content.get("kind")
        payload = content.get("payload") if isinstance(content.get("payload"), Mapping) else {}
        tool = content.get("tool_call") if isinstance(content.get("tool_call"), Mapping) else {}
        resource = (
            payload.get("resource_id")
            or tool.get("arguments", {}).get("resource_id")
            if isinstance(tool.get("arguments"), Mapping)
            else payload.get("resource_id")
        )
        actor_action_resource.append(
            {
                "span_ref": span.span_id,
                "actor": actor,
                "action": event_type or tool.get("name"),
                "resource": resource,
            }
        )
        if event_type in {"evidence-inspected", "evidence-shared", "resource-disclosed"}:
            knowledge_state.append(
                {"span_ref": span.span_id, "actor": actor, "event": event_type, "resource": resource}
            )
        if event_type in {"phase-advanced", "resolution-submitted", "session-ended"}:
            milestone_obligation.append(
                {"span_ref": span.span_id, "event": event_type, "payload": dict(payload)}
            )
        if event_type in {"message", "said", "broadcast", "resolution-submitted"}:
            claimed_vs_verified.append(
                {
                    "span_ref": span.span_id,
                    "claim": payload.get("text") or payload.get("explanation"),
                    "verification_status": package.verification.status,
                }
            )
    return FactualGraphs(
        package.package_id,
        tuple(actor_action_resource),
        tuple(knowledge_state),
        tuple(milestone_obligation),
        tuple(claimed_vs_verified),
    )


def derive_discovery_materials(
    package: EpisodeEvidencePackage,
) -> tuple[Mapping[str, EvidenceGrant], Mapping[str, Mapping[str, Any]]]:
    """Return content-addressed category grants and their materialized objects."""
    view = build_discovery_view(package)
    graphs = derive_factual_graphs(package)
    span_ids = tuple(item.source_span_id for item in view.spans)
    objects: dict[str, Mapping[str, Any]] = {}
    grants: dict[str, EvidenceGrant] = {}
    for category in DISCOVERY_ALLOW:
        value: Mapping[str, Any]
        if category == "assigned_factual_graphs":
            value = graphs.to_mapping()
        else:
            value = {
                "schema_version": "analysis-material.1",
                "category": category,
                "episode_package_ref": package.package_id,
                "discovery_view_ref": view.manifest_id,
                "spans": [item.to_mapping() for item in view.spans],
            }
        object_ref = digest_json(value)
        objects[object_ref] = value
        grants[category] = EvidenceGrant(category, object_ref, span_ids)
    return grants, objects
