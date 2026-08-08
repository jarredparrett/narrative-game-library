"""Truth-blind failure discovery and independently corroborated Incidents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from narrative_game.contracts.canonical import digest_json


DISCOVERY_LENSES = (
    "outcome-and-progress",
    "knowledge-and-claim-support",
    "coordination-communication-and-work-allocation",
    "host-intervention-and-dependence",
    "runtime-authorization-and-evaluator-integrity",
)


@dataclass(frozen=True)
class SweepCoverage:
    required_regions: tuple[str, ...]
    inspected_regions: tuple[str, ...]
    graph_regions: tuple[str, ...]
    expanded_span_ids: tuple[str, ...]
    counterevidence_searches: tuple[str, ...]
    omitted_regions: tuple[str, ...] = ()
    truncated_regions: tuple[str, ...] = ()
    failed_regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.required_regions) != len(set(self.required_regions)):
            raise ValueError("Sweep Coverage required regions must be unique")
        if len(self.inspected_regions) != len(set(self.inspected_regions)):
            raise ValueError("Sweep Coverage inspected regions must be unique")

    @property
    def complete(self) -> bool:
        return (
            set(self.required_regions) <= set(self.inspected_regions)
            and bool(self.counterevidence_searches)
            and not self.omitted_regions
            and not self.truncated_regions
            and not self.failed_regions
        )

    @property
    def coverage_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "required_regions": list(self.required_regions),
            "inspected_regions": list(self.inspected_regions),
            "graph_regions": list(self.graph_regions),
            "expanded_span_ids": list(self.expanded_span_ids),
            "counterevidence_searches": list(self.counterevidence_searches),
            "omitted_regions": list(self.omitted_regions),
            "truncated_regions": list(self.truncated_regions),
            "failed_regions": list(self.failed_regions),
            "complete": self.complete,
        }


@dataclass(frozen=True)
class FailureSignalProposal:
    principal: str
    lens: str
    expected_obligation: str
    observed_gap: str
    span_refs: tuple[str, ...]
    verification_status: str
    actors: tuple[str, ...]
    episode_window: tuple[int, int]
    pattern_identity: str
    novel: bool
    counterevidence_refs: tuple[str, ...]
    alternatives: tuple[str, ...]
    confidence_band: str
    coverage_ref: str
    analysis_receipt_ref: str
    graph_connection: str | None = None

    def __post_init__(self) -> None:
        if self.lens not in DISCOVERY_LENSES:
            raise ValueError("Signal must use a frozen Discovery lens")
        if not self.span_refs:
            raise ValueError("Failure Signal requires exact evidence spans")
        if self.verification_status not in {"verified", "partial", "invalid"}:
            raise ValueError("Signal Verification Status is not recognized")
        if self.episode_window[0] > self.episode_window[1]:
            raise ValueError("Signal Episode window is inverted")
        if self.confidence_band not in {"low", "medium", "high"}:
            raise ValueError("Signal confidence must be a band")

    @property
    def gap_key(self) -> tuple[str, str]:
        return self.expected_obligation.strip().casefold(), self.observed_gap.strip().casefold()

    @property
    def signal_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "principal": self.principal,
            "lens": self.lens,
            "expected_obligation": self.expected_obligation,
            "observed_gap": self.observed_gap,
            "span_refs": list(self.span_refs),
            "verification_status": self.verification_status,
            "actors": list(self.actors),
            "episode_window": list(self.episode_window),
            "pattern_identity": self.pattern_identity,
            "novel": self.novel,
            "counterevidence_refs": list(self.counterevidence_refs),
            "alternatives": list(self.alternatives),
            "confidence_band": self.confidence_band,
            "coverage_ref": self.coverage_ref,
            "analysis_receipt_ref": self.analysis_receipt_ref,
            "graph_connection": self.graph_connection,
        }


@dataclass(frozen=True)
class DiscoverySweep:
    episode_package_ref: str
    principal: str
    lens: str
    status: str
    coverage: SweepCoverage
    signals: tuple[FailureSignalProposal, ...]
    exclusions: tuple[str, ...]
    continuation_cursor: str | None
    analysis_receipt_ref: str
    schema_version: str = "discovery-sweep-result.1"

    def __post_init__(self) -> None:
        if self.lens not in DISCOVERY_LENSES:
            raise ValueError("Discovery Sweep lens is not frozen")
        if self.status not in {"complete", "partial", "invalid"}:
            raise ValueError("Discovery Sweep status is not recognized")
        if self.status == "complete" and (not self.coverage.complete or self.continuation_cursor):
            raise ValueError("complete Sweep requires complete coverage and no cursor")
        if self.status == "partial" and not self.continuation_cursor:
            raise ValueError("partial Sweep requires an exact continuation cursor")
        if self.status != "complete" and not self.signals and self.status != "invalid":
            raise ValueError("only a complete Sweep may report no finding")
        if any(item.principal != self.principal or item.lens != self.lens for item in self.signals):
            raise ValueError("Sweep cannot adopt another principal or lens's Signal")
        if any(item.coverage_ref != self.coverage.coverage_ref for item in self.signals):
            raise ValueError("Signal must bind the Sweep Coverage that produced it")

    @property
    def sweep_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_package_ref": self.episode_package_ref,
            "principal": self.principal,
            "lens": self.lens,
            "status": self.status,
            "coverage": self.coverage.to_mapping(),
            "signals": [item.to_mapping() for item in self.signals],
            "exclusions": list(self.exclusions),
            "continuation_cursor": self.continuation_cursor,
            "analysis_receipt_ref": self.analysis_receipt_ref,
        }


@dataclass(frozen=True)
class IncidentAssembly:
    episode_package_ref: str
    principal: str
    included_signal_refs: tuple[str, ...]
    excluded_signal_refs: tuple[str, ...]
    grouping_obligation: str
    graph_connection: str | None
    preserved_disagreement: tuple[str, ...]
    targeted_sweep_request: str | None
    analysis_receipt_ref: str
    schema_version: str = "incident-assembly-result.1"

    def __post_init__(self) -> None:
        if not self.included_signal_refs:
            raise ValueError("Incident Assembly requires at least one frozen Signal")
        if set(self.included_signal_refs) & set(self.excluded_signal_refs):
            raise ValueError("Incident Assembly cannot include and exclude one Signal")

    @property
    def assembly_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_package_ref": self.episode_package_ref,
            "principal": self.principal,
            "included_signal_refs": list(self.included_signal_refs),
            "excluded_signal_refs": list(self.excluded_signal_refs),
            "grouping_obligation": self.grouping_obligation,
            "graph_connection": self.graph_connection,
            "preserved_disagreement": list(self.preserved_disagreement),
            "targeted_sweep_request": self.targeted_sweep_request,
            "analysis_receipt_ref": self.analysis_receipt_ref,
        }


@dataclass(frozen=True)
class DiscoveryCorroboration:
    assembly_ref: str
    status: str
    corroborating_signal_refs: tuple[str, ...]
    unresolved_signal_refs: tuple[str, ...]
    disagreements: tuple[str, ...]
    reason: str
    schema_version: str = "discovery-corroboration.1"

    @property
    def corroboration_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assembly_ref": self.assembly_ref,
            "status": self.status,
            "corroborating_signal_refs": list(self.corroborating_signal_refs),
            "unresolved_signal_refs": list(self.unresolved_signal_refs),
            "disagreements": list(self.disagreements),
            "reason": self.reason,
        }


def corroborate_incident(
    assembly: IncidentAssembly,
    sweeps: tuple[DiscoverySweep, ...],
    *,
    targeted_sweep: DiscoverySweep | None = None,
) -> DiscoveryCorroboration:
    """Require independent complete convergence without flattening conflict."""
    by_ref = {
        signal.signal_ref: (sweep, signal)
        for sweep in sweeps
        for signal in sweep.signals
    }
    selected = [by_ref[item] for item in assembly.included_signal_refs if item in by_ref]
    missing = tuple(sorted(set(assembly.included_signal_refs) - set(by_ref)))
    disagreements = list(assembly.preserved_disagreement)
    if missing:
        disagreements.append("assembly names unavailable Signal refs: " + ", ".join(missing))
    obligation = assembly.grouping_obligation.strip().casefold()
    if any(signal.expected_obligation.strip().casefold() != obligation for _, signal in selected):
        disagreements.append("Assembly grouped Signals with different obligations")
    for index, (_, left) in enumerate(selected):
        for _, right in selected[index + 1 :]:
            overlaps = max(left.episode_window[0], right.episode_window[0]) <= min(
                left.episode_window[1], right.episode_window[1]
            )
            connected = bool(
                left.graph_connection
                and right.graph_connection
                and left.graph_connection == right.graph_connection
            )
            if not overlaps and not connected:
                disagreements.append("Assembly grouped Signals without an overlapping window or graph connection")
    groups: dict[tuple[str, str], list[tuple[DiscoverySweep, FailureSignalProposal]]] = {}
    for sweep, signal in selected:
        if sweep.status == "complete":
            groups.setdefault(signal.gap_key, []).append((sweep, signal))
    eligible_refs: tuple[str, ...] = ()
    for rows in groups.values():
        principals = {sweep.principal for sweep, _ in rows}
        lenses = {sweep.lens for sweep, _ in rows}
        if len(principals) >= 2 and len(lenses) >= 2:
            eligible_refs = tuple(sorted(signal.signal_ref for _, signal in rows))
            break
    if not eligible_refs and targeted_sweep is not None and targeted_sweep.status == "complete":
        if targeted_sweep.principal not in {sweep.principal for sweep, _ in selected}:
            target_keys = {signal.gap_key for _, signal in selected}
            confirmations = tuple(
                signal.signal_ref for signal in targeted_sweep.signals if signal.gap_key in target_keys
            )
            if confirmations:
                eligible_refs = tuple(sorted({*(signal.signal_ref for _, signal in selected), *confirmations}))
    conflicting_keys = {
        signal.observed_gap.strip().casefold()
        for _, signal in selected
        if signal.expected_obligation.strip().casefold() == assembly.grouping_obligation.strip().casefold()
    }
    if len(conflicting_keys) > 1:
        disagreements.append("independent Sweeps report materially different observed gaps")
        eligible_refs = ()
    unresolved = tuple(sorted(set(assembly.included_signal_refs) - set(eligible_refs)))
    if eligible_refs and not missing and not disagreements:
        return DiscoveryCorroboration(
            assembly.assembly_ref,
            "eligible-for-semantic-interpretation",
            eligible_refs,
            unresolved,
            tuple(disagreements),
            "two independently occupied complete Sweeps corroborate the same gap",
        )
    return DiscoveryCorroboration(
        assembly.assembly_ref,
        "unresolved",
        (),
        unresolved,
        tuple(disagreements),
        "independent complete corroboration is absent or conflicting",
    )
