"""Stage 7 baseline measurement consumes real driver output, never constants."""

from __future__ import annotations

from narrative_game.climb import DriverOutput
from narrative_game.contracts import canonical_json
from narrative_game.stage7_experiment import measure_prepared_baseline, prepare_baseline


class BaselineJudgeDriver:
    def __init__(self):
        self.calls = 0

    def invoke(self, invocation):
        self.calls += 1
        parsed = {
            "scores": {
                "investigative_coherence": 73,
                "deduction_quality": 68,
                "character_agency": 76,
                "facilitation_resilience": 71,
                "production_realism": 79,
            },
            "findings": [
                {
                    "requirement_code": "world.opening-information-density",
                    "severity": "major",
                    "resource_path": "trial/materials/avery-dossier",
                    "locus": "opening chronology",
                    "quote": "At 8:40 p.m. the property ledger was on the records-room desk.",
                    "message": "The opening gives one Seat a highly resolving chronology before joint investigation begins.",
                }
            ],
        }
        return DriverOutput(
            "capability-driver",
            "recorded-baseline-judge-v1",
            "capability-fixture",
            canonical_json(parsed),
            parsed,
        )


def test_measurement_records_driver_scores_and_quoted_spans_without_selecting(tmp_path):
    """stage7.real-measurement: scores originate in the exact Driver output."""
    prepared = prepare_baseline(tmp_path / "stage7")
    driver = BaselineJudgeDriver()
    measured = measure_prepared_baseline(
        tmp_path / "stage7", driver, requested_model="configured-baseline-judge"
    )
    assert driver.calls == 1
    assert measured.summary["overall_score"] == 72.4
    assert measured.summary["outcome"] == "fail"
    assert measured.summary["evidence_class"] == "capability-fixture"
    assert len(measured.ledger.snapshot()["findings"]) == 1
    assert len(measured.ledger.snapshot()["evaluations"]) == 1
    assert measured.ledger.snapshot()["selections"] == ()
    assert measured.summary["standing"] is None
    assert measured.ledger.verify()["ok"]
    assert measured.workspace.verify()["ok"]


def test_exact_retry_does_not_call_the_external_driver_twice(tmp_path):
    """stage7.model-driver: completed model occupancy is exactly idempotent."""
    prepare_baseline(tmp_path / "stage7")
    driver = BaselineJudgeDriver()
    first = measure_prepared_baseline(
        tmp_path / "stage7", driver, requested_model="configured-baseline-judge"
    )
    second = measure_prepared_baseline(
        tmp_path / "stage7", driver, requested_model="configured-baseline-judge"
    )
    assert first.summary == second.summary
    assert driver.calls == 1
