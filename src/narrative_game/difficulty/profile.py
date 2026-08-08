"""Seven-dimensional Difficulty Profiles with explicit uncertainty."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from statistics import median
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


DIFFICULTY_DIMENSIONS = (
    "episode-validity",
    "resolution-reliability",
    "progress-and-effort",
    "proof-robustness",
    "coordination-quality",
    "recovery-dependence",
    "sensitivity-and-brittleness",
)


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class MetricValue:
    dimension: str
    metric: str
    kind: str
    value: float

    def __post_init__(self) -> None:
        if self.dimension not in DIFFICULTY_DIMENSIONS:
            raise ValueError(f"unknown Difficulty Profile dimension: {self.dimension}")
        if self.kind not in {"binary", "count", "continuous"}:
            raise ValueError(f"unknown metric kind: {self.kind}")
        if self.kind == "binary" and self.value not in {0, 1, 0.0, 1.0}:
            raise ValueError("binary metric values must be zero or one")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "metric": self.metric,
            "kind": self.kind,
            "value": self.value,
        }


@dataclass(frozen=True)
class EpisodeProfileObservation:
    assignment_id: str
    episode_ref: str | None
    status: str
    stratum: str
    correlation_group: str
    metrics: tuple[MetricValue, ...]

    def __post_init__(self) -> None:
        if self.status not in {"verified", "invalid", "partial", "missing"}:
            raise ValueError(f"unknown Episode profile status: {self.status}")
        if self.status == "verified" and self.episode_ref is None:
            raise ValueError("verified Episode observation requires evidence")
        if self.status != "verified" and self.metrics:
            raise ValueError("invalid, partial, and missing Episodes do not enter difficulty metrics")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "episode_ref": self.episode_ref,
            "status": self.status,
            "stratum": self.stratum,
            "correlation_group": self.correlation_group,
            "metrics": [item.to_mapping() for item in self.metrics],
        }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _wilson(successes: int, count: int) -> tuple[float, float]:
    z = 1.959963984540054
    proportion = successes / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    half = z * math.sqrt(
        proportion * (1 - proportion) / count + z * z / (4 * count * count)
    ) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def _bootstrap_median(
    observations: tuple[tuple[str, float], ...], *, repetitions: int = 400
) -> tuple[float, float]:
    strata: dict[str, list[float]] = {}
    for stratum, value in observations:
        strata.setdefault(stratum, []).append(value)
    estimates = []
    for repetition in range(repetitions):
        sample = []
        for stratum, values in sorted(strata.items()):
            for draw in range(len(values)):
                digest = digest_json(
                    {"repetition": repetition, "stratum": stratum, "draw": draw}
                )
                index = int(digest[-16:], 16) % len(values)
                sample.append(values[index])
        estimates.append(float(median(sample)))
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


@dataclass(frozen=True)
class MetricUncertainty:
    dimension: str
    metric: str
    kind: str
    numerator: float | None
    denominator: int
    point_estimate: float | None
    interquartile_range: tuple[float, float] | None
    interval: tuple[float, float] | None
    interval_method: str
    observations: tuple[tuple[str, float], ...]
    assignment_ids: tuple[str, ...]
    correlation_groups: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "metric": self.metric,
            "kind": self.kind,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "point_estimate": self.point_estimate,
            "interquartile_range": list(self.interquartile_range) if self.interquartile_range else None,
            "interval": list(self.interval) if self.interval else None,
            "interval_method": self.interval_method,
            "observations": [list(item) for item in self.observations],
            "assignment_ids": list(self.assignment_ids),
            "correlation_groups": list(self.correlation_groups),
        }


@dataclass(frozen=True)
class DifficultyProfile:
    release_id: str
    panel_application_id: str
    analysis_instrument_id: str
    expected_assignment_ids: tuple[str, ...]
    status_counts: Mapping[str, int]
    dimensions: Mapping[str, tuple[MetricUncertainty, ...]]
    schema_version: str = "difficulty-profile.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "status_counts", _copy(self.status_counts))
        if set(self.dimensions) != set(DIFFICULTY_DIMENSIONS):
            raise ValueError("Difficulty Profile must preserve all seven dimensions")

    @property
    def complete(self) -> bool:
        return self.status_counts.get("invalid", 0) == 0 and self.status_counts.get("partial", 0) == 0 and self.status_counts.get("missing", 0) == 0

    @property
    def profile_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "release_id": self.release_id,
            "panel_application_id": self.panel_application_id,
            "analysis_instrument_id": self.analysis_instrument_id,
            "expected_assignment_ids": list(self.expected_assignment_ids),
            "status_counts": dict(sorted(self.status_counts.items())),
            "dimensions": {
                key: [item.to_mapping() for item in self.dimensions[key]]
                for key in DIFFICULTY_DIMENSIONS
            },
            "complete": self.complete,
        }


def derive_difficulty_profile(
    *,
    release_id: str,
    panel_application_id: str,
    analysis_instrument_id: str,
    expected_assignment_ids: tuple[str, ...],
    observations: tuple[EpisodeProfileObservation, ...],
) -> DifficultyProfile:
    observed_ids = [item.assignment_id for item in observations]
    if len(observed_ids) != len(set(observed_ids)):
        raise ValueError("Difficulty Profile observations must name assignments once")
    unexpected = sorted(set(observed_ids) - set(expected_assignment_ids))
    if unexpected:
        raise ValueError("Difficulty Profile includes unexpected assignments: " + ", ".join(unexpected))
    by_id = {item.assignment_id: item for item in observations}
    completed = tuple(
        by_id.get(
            assignment_id,
            EpisodeProfileObservation(assignment_id, None, "missing", "unobserved", assignment_id, ()),
        )
        for assignment_id in expected_assignment_ids
    )
    status_counts = {
        status: sum(item.status == status for item in completed)
        for status in ("verified", "invalid", "partial", "missing")
    }
    metric_rows: dict[tuple[str, str, str], list[tuple[EpisodeProfileObservation, MetricValue]]] = {}
    for observation in completed:
        for metric in observation.metrics:
            metric_rows.setdefault((metric.dimension, metric.metric, metric.kind), []).append((observation, metric))
    dimensions: dict[str, list[MetricUncertainty]] = {item: [] for item in DIFFICULTY_DIMENSIONS}
    for (dimension, metric_name, kind), rows in sorted(metric_rows.items()):
        values = [float(metric.value) for _, metric in rows]
        assignments = tuple(observation.assignment_id for observation, _ in rows)
        correlation = tuple(observation.correlation_group for observation, _ in rows)
        observations_with_strata = tuple(
            (observation.stratum, float(metric.value)) for observation, metric in rows
        )
        if kind == "binary":
            numerator = float(sum(values))
            estimate = numerator / len(values)
            interquartile_range = None
            interval = _wilson(int(numerator), len(values))
            method = "wilson-95"
        else:
            numerator = None
            estimate = float(median(values))
            interquartile_range = (_percentile(values, 0.25), _percentile(values, 0.75))
            interval = _bootstrap_median(observations_with_strata) if len(values) >= 8 else None
            method = "stratified-bootstrap-median-95" if interval else "insufficient-n<8"
        dimensions[dimension].append(
            MetricUncertainty(
                dimension,
                metric_name,
                kind,
                numerator,
                len(values),
                estimate,
                interquartile_range,
                interval,
                method,
                observations_with_strata,
                assignments,
                correlation,
            )
        )
    return DifficultyProfile(
        release_id,
        panel_application_id,
        analysis_instrument_id,
        expected_assignment_ids,
        status_counts,
        {key: tuple(value) for key, value in dimensions.items()},
    )


@dataclass(frozen=True)
class TargetBand:
    dimension: str
    metric: str
    lower: float
    upper: float
    gating: bool = True

    def __post_init__(self) -> None:
        if self.dimension not in DIFFICULTY_DIMENSIONS or self.lower > self.upper:
            raise ValueError("invalid Difficulty Target band")


@dataclass(frozen=True)
class DifficultyTargetContract:
    profile_id: str
    version: str
    panel_id: str
    analysis_instrument_id: str
    required_assignment_count: int
    bands: tuple[TargetBand, ...]
    permitted_tradeoffs: tuple[tuple[str, str], ...] = ()
    calibration_receipt_ref: str | None = None
    schema_version: str = "difficulty-target-contract.1"

    @property
    def contract_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "version": self.version,
            "panel_id": self.panel_id,
            "analysis_instrument_id": self.analysis_instrument_id,
            "required_assignment_count": self.required_assignment_count,
            "bands": [item.__dict__ for item in self.bands],
            "permitted_tradeoffs": [list(item) for item in self.permitted_tradeoffs],
            "calibration_receipt_ref": self.calibration_receipt_ref,
        }


@dataclass(frozen=True)
class ProfileClassification:
    classification: str
    responsible_metrics: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TargetDominanceDecision:
    outcome: str
    improved_metrics: tuple[str, ...]
    regressed_metrics: tuple[str, ...]
    reasons: tuple[str, ...]


def _distance_to_band(value: float, band: TargetBand) -> float:
    if value < band.lower:
        return band.lower - value
    if value > band.upper:
        return value - band.upper
    return 0.0


def _distance_range(metric: MetricUncertainty, band: TargetBand) -> tuple[float, float] | None:
    """Return the possible target-distance range supported by a metric interval."""
    if metric.interval is None:
        return None
    low, high = metric.interval
    distances = [_distance_to_band(low, band), _distance_to_band(high, band)]
    if low <= band.upper and high >= band.lower:
        distances.append(0.0)
    return min(distances), max(distances)


def decide_target_dominance(
    baseline: DifficultyProfile,
    child: DifficultyProfile,
    contract: DifficultyTargetContract,
    *,
    repair_targets: tuple[str, ...],
    new_severe_failure_class: bool = False,
) -> TargetDominanceDecision:
    """Select only a non-scalar child that improves a declared target without regression."""
    if not baseline.complete or not child.complete:
        return TargetDominanceDecision(
            "indeterminate", (), (), ("matched Profiles are incomplete",)
        )
    baseline_metrics = {
        f"{item.dimension}.{item.metric}": item
        for values in baseline.dimensions.values()
        for item in values
    }
    child_metrics = {
        f"{item.dimension}.{item.metric}": item
        for values in child.dimensions.values()
        for item in values
    }
    improved = []
    regressed = []
    tradeoffs = {tuple(item) for item in contract.permitted_tradeoffs}
    for band in contract.bands:
        name = f"{band.dimension}.{band.metric}"
        before = baseline_metrics.get(name)
        after = child_metrics.get(name)
        if before is None or after is None or before.point_estimate is None or after.point_estimate is None:
            return TargetDominanceDecision(
                "indeterminate", tuple(improved), tuple(regressed), (f"missing matched metric: {name}",)
            )
        if (
            before.assignment_ids != after.assignment_ids
            or before.correlation_groups != after.correlation_groups
        ):
            return TargetDominanceDecision(
                "indeterminate",
                tuple(improved),
                tuple(regressed),
                (f"unpaired uncertainty evidence: {name}",),
            )
        before_distance = _distance_range(before, band)
        after_distance = _distance_range(after, band)
        if before_distance is None or after_distance is None:
            return TargetDominanceDecision(
                "indeterminate",
                tuple(improved),
                tuple(regressed),
                (f"unsupported uncertainty for target comparison: {name}",),
            )
        if after_distance[1] < before_distance[0]:
            improved.append(name)
        elif after_distance[0] > before_distance[1]:
            regressed.append(name)
        elif after.point_estimate != before.point_estimate:
            return TargetDominanceDecision(
                "indeterminate",
                tuple(improved),
                tuple(regressed),
                (f"paired uncertainty does not resolve target movement: {name}",),
            )
    unpermitted = [
        name
        for name in regressed
        if not any((improved_name, name) in tradeoffs for improved_name in improved)
    ]
    if new_severe_failure_class:
        return TargetDominanceDecision(
            "baseline-retained", tuple(improved), tuple(regressed), ("child introduces a severe promoted Failure Class",)
        )
    if unpermitted:
        return TargetDominanceDecision(
            "indeterminate", tuple(improved), tuple(regressed), ("an undeclared target trade-off regressed",)
        )
    if not set(repair_targets) & set(improved):
        return TargetDominanceDecision(
            "baseline-retained", tuple(improved), tuple(regressed), ("no declared repair target improved",)
        )
    return TargetDominanceDecision(
        "child-dominates", tuple(improved), tuple(regressed), ("declared repair target improved without unpermitted regression",)
    )


def classify_profile(
    profile: DifficultyProfile, contract: DifficultyTargetContract
) -> ProfileClassification:
    if (
        not profile.complete
        or len(profile.expected_assignment_ids) < contract.required_assignment_count
        or contract.calibration_receipt_ref is None
    ):
        return ProfileClassification(
            "indeterminate",
            (),
            ("coverage, sample size, or Calibration evidence is incomplete",),
        )
    indexed = {
        (metric.dimension, metric.metric): metric
        for values in profile.dimensions.values()
        for metric in values
    }
    responsible = []
    provisional = False
    too_easy = False
    too_hard = False
    for band in contract.bands:
        if not band.gating:
            continue
        metric = indexed.get((band.dimension, band.metric))
        name = f"{band.dimension}.{band.metric}"
        if metric is None or metric.point_estimate is None or metric.interval is None:
            responsible.append(name)
            provisional = True
            continue
        low, high = metric.interval
        if low > band.upper:
            too_easy = True
            responsible.append(name)
        elif high < band.lower:
            too_hard = True
            responsible.append(name)
        elif band.lower <= low and high <= band.upper:
            continue
        elif band.lower <= metric.point_estimate <= band.upper:
            provisional = True
            responsible.append(name)
        else:
            responsible.append(name)
            return ProfileClassification("indeterminate", tuple(responsible), ("uncertainty crosses a target boundary",))
    if too_easy and too_hard:
        return ProfileClassification("brittle", tuple(responsible), ("required slices miss opposite target boundaries",))
    if too_easy:
        return ProfileClassification("too-easy", tuple(responsible), ("interval lies above target band",))
    if too_hard:
        return ProfileClassification("too-hard", tuple(responsible), ("interval lies below target band",))
    if provisional:
        return ProfileClassification("provisionally-target-band", tuple(responsible), ("point estimates are plausible but uncertainty is unresolved",))
    return ProfileClassification("supported-target-band", (), ("every gating interval lies inside its frozen band",))
