"""Stage 11 preparation proof for the six-player human boundary."""

import json

from narrative_game.examples import winter_observatory_game
from narrative_game.playtest import PlayObservation, PlaytestProtocol
from narrative_game.stage11_playtest_fixture import (
    DEFECT_OWNERS, RESPONSE_STAGES, RUBRIC, _forms,
    winter_playtest_instrument,
)


def protocol(instrument, binding_id="binding:exact", name="Winter six-player"):
    return PlaytestProtocol(
        name, "1.0.0", binding_id,
        instrument.instrument_id, "playtest-consent-v1", 2, 6,
        tuple(item[0] for item in RUBRIC), True, 10,
        RESPONSE_STAGES, ("pre_game", "post_game"), True, DEFECT_OWNERS,
    )


def test_human_instrument_freezes_every_issue_17_dimension_and_gate():
    """stage11.human-rubric: dossier experience is frozen before recruitment."""
    instrument = winter_playtest_instrument()
    assert tuple(item.dimension_id for item in instrument.dimensions) == tuple(
        item[0] for item in RUBRIC
    )
    assert instrument.hard_gate_codes == (
        "package.verify", "dossier.depth", "access.separation"
    )
    assert instrument.blind_protocol["selection_evidence_classes"] == [
        "fresh-human-play"
    ]
    assert instrument.instrument_id == (
        "instrument:22df667df25d2399cdaaca4faaecacf691d6cb398c42e0db7bd36315b7d9b850"
    )


def test_response_contract_preserves_stage_timestamp_rubric_and_defect_owner():
    """stage11.human-trace: attributable human observations round-trip exactly."""
    observation = PlayObservation(
        "participant-1", "participant", "reunion", "role_onboarding",
        "I knew what to do.", "First move was stated without help.",
        "sha256:" + "1" * 64, "pre_game", 93, "role_onboarding.timer", "dossier",
    )
    assert PlayObservation.from_mapping(observation.to_mapping()) == observation


def test_review_forms_cover_six_roles_every_phase_and_every_rubric_item():
    """stage11.human-kit: preparation is complete but contains no invented responses."""
    game = winter_observatory_game(); instrument = winter_playtest_instrument()
    first = _forms(game, instrument, protocol(instrument), "sha256:" + "a" * 64, "sha256:" + "b" * 64)
    second = _forms(game, instrument, protocol(instrument), "sha256:" + "a" * 64, "sha256:" + "b" * 64)
    assert first == second
    roster = first["forms/roster.csv"].decode().splitlines()
    host = first["forms/facilitator-observations.csv"].decode().splitlines()
    post = json.loads(first["forms/post-game.json"])
    assert len(roster) == 7
    assert len(host) == len(game.phases) + 1
    assert {item["id"] for item in post["items"]} == {item[0] for item in RUBRIC}
    assert all(item["quote"] == "required" for item in post["items"])
    assert b"awaiting" not in first["forms/consent-v1.md"].lower()
    manifest = json.loads(first["recording-manifest.example.json"])
    assert len(manifest["participants"]) == 6
    assert manifest["protocol_id"] == protocol(instrument).protocol_id
    exact = protocol(
        instrument,
        "trial-binding:65e47d9374516334318f835c0659f09ece70b699ce5181e05796721f6c05f15d",
        "Winter Observatory six-player dossier validation",
    )
    assert exact.protocol_id == (
        "playtest-protocol:1bd2ef9487895b3453de0ffe0aeb91ea2e6e66a1ba9b84ea3ea7ba8266c3ea0f"
    )
    assert set(manifest["scores"]) == {item[0] for item in RUBRIC}
    session_plan = json.loads(first["session-plan.example.json"])
    assert len(session_plan["bindings"]) == 6
    assert session_plan["commands"][0]["action"] == "open-session"
    assert session_plan["commands"][-1]["action"] == "record-resolution"
    submit_index = next(
        index for index, item in enumerate(session_plan["commands"])
        if item["action"] == "submit-resolution"
    )
    assert session_plan["commands"][submit_index - 1]["payload"]["phase_id"] == (
        game.resolution.phase_id
    )
