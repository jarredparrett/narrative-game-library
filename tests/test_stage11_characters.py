"""Stage 11 capability proof for deep dossiers and phase-aware Characters."""

from dataclasses import replace
from io import BytesIO
import json

from pypdf import PdfReader

from narrative_game.compiler import BundledFile, GameRelease, reference_component_lock
from narrative_game.compiler.projections import host_projection, seat_projection
from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.examples import (
    winter_observatory_game,
    winter_observatory_parent_game,
)
from narrative_game.narrative import (
    ReferencedText, render_dossier_markdown, validate_character_program,
)
from narrative_game.physical import render_dossier_pdf
from narrative_game.stage11_character_fixture import run
from narrative_game.runtime import (
    Actor, ActorBinding, AuthorizationContext, SessionCommand, ViewerGrant,
    apply_command, create_session, replay, seat_snapshot,
)


def _release(game) -> GameRelease:
    files = [BundledFile("trusted/game.json", "application/json", canonical_json(game.to_mapping()), "trusted")]
    for seat in game.kernel.seats:
        files.append(BundledFile(
            f"projections/seats/{seat.id}.json", "application/json",
            canonical_json(seat_projection(game, seat.id)), f"seat:{seat.id}",
        ))
    files.append(BundledFile(
        "projections/host.json", "application/json",
        canonical_json(host_projection(game)), "trusted-host",
    ))
    materials = [
        {"resource_id": item.id, "media_type": item.media_type, "content_hash": item.content_hash}
        for item in game.kernel.resources
    ]
    return GameRelease(
        "release:winter-characters", "candidate:winter-characters",
        {"component_lock": reference_component_lock(), "materials": materials},
        tuple(files), b"fixture", digest_bytes(b"fixture"),
    )


def _command(history, release, identifier, action, payload):
    return SessionCommand(identifier, history.session_id, release.release_id, history.sequence, action, payload)


def test_six_dossiers_are_complete_canonical_and_render_three_to_five_pages():
    """stage11.dossiers: every Winter role has a deterministic layered print Dossier."""
    parent = winter_observatory_parent_game()
    assert parent.content_hash == (
        "sha256:967f7873e0119dfba85d2c50b55ee5345b7385a0629e66a658dbcc5df2736a4a"
    )
    game = winter_observatory_game()
    assert validate_character_program(game, game.character_program) == ()
    assert len(game.character_program.dossiers) == 6
    for dossier in game.character_program.dossiers:
        markdown = render_dossier_markdown(game, dossier)
        resource = next(item for item in game.kernel.resources if item.id == dossier.resource_id)
        assert resource.content_hash == digest_bytes(markdown)
        assert markdown.startswith(b"# ")
        assert markdown.index(b"Quick start") < markdown.index(b"Deep play")
        assert b"The host has a recovery path if this window is missed." not in markdown
        assert markdown == render_dossier_markdown(game, dossier)
        pdf = render_dossier_pdf(game, dossier)
        assert pdf == render_dossier_pdf(game, dossier)
        reader = PdfReader(BytesIO(pdf))
        assert 3 <= len(reader.pages) <= 5
        extracted = "".join(page.extract_text() or "" for page in reader.pages)
        assert "####" not in extracted
        assert not {"\u2013", "\u2014", "\u2011"} & set(extracted)
        assert dossier.quick_start.opening_belief_proposition_ids[0] not in extracted


def test_seat_projection_has_deep_play_but_never_host_or_other_seat_truth():
    """stage11.dossier-secrecy: serialization excludes host solution and other Dossiers."""
    game = winter_observatory_game()
    projection = seat_projection(game, "eleanor-vale")
    encoded = json.dumps(projection)
    assert projection["dossier"]["quick_start"]
    assert projection["dossier"]["deep_play"]["relationships"]
    for proposition_id in game.character_program.host_only_proposition_ids:
        assert proposition_id not in encoded
    assert "winter-observatory:felix-mercer:dossier" not in encoded
    assert "second-route-recovery" not in encoded


def test_validator_blocks_leakage_unreachable_secrets_and_dead_end_arcs():
    """stage11.character-gates: impossible or unsafe play states fail before release."""
    game = winter_observatory_game()
    program = game.character_program
    dossier = program.dossiers[0]

    leaked_quick = replace(
        dossier.quick_start,
        private_truth=ReferencedText("I know the killer's meeting.", ("mercer-met-vale",)),
    )
    leaked = replace(dossier, quick_start=leaked_quick)
    findings = validate_character_program(game, replace(program, dossiers=(leaked, *program.dossiers[1:])))
    assert any(item.code == "character.unauthorized-knowledge" for item in findings)

    unreachable = replace(dossier, reveal_paths=())
    findings = validate_character_program(game, replace(program, dossiers=(unreachable, *program.dossiers[1:])))
    assert any(item.code == "character.unreachable-revelation" for item in findings)

    opening = dossier.phase_arcs[0]
    move_kind = {item.move_id: item.kind for item in dossier.moves}
    dead = replace(opening, move_ids=tuple(item for item in opening.move_ids if move_kind[item] != "fallback"))
    dead_dossier = replace(dossier, phase_arcs=(dead, *dossier.phase_arcs[1:]))
    findings = validate_character_program(game, replace(program, dossiers=(dead_dossier, *program.dossiers[1:])))
    assert any(item.code == "character.dead-end-state" for item in findings)


def test_agentic_cast_uses_same_authority_and_persists_human_direction():
    """stage11.character-agency: model Actors remain bounded and human direction replays."""
    game = winter_observatory_game()
    release = _release(game)
    bindings = tuple(
        ActorBinding(f"binding:{seat.id}", Actor(f"agent:{seat.id}", "model", seat.label), seat.id, 1)
        for seat in game.kernel.seats
    )
    history = create_session(
        release=release, session_id="winter-agentic", mode="simulation",
        bindings=bindings, viewers=(ViewerGrant("host", "host"),),
    )
    host = AuthorizationContext("viewer", "host")
    history = apply_command(release, history, _command(history, release, "open", "open-session", {}), host).history
    eleanor = next(item for item in game.character_program.dossiers if item.seat_id == "eleanor-vale")
    auth = AuthorizationContext("actor", "agent:eleanor-vale", "binding:eleanor-vale")
    move_id = eleanor.phase_arcs[0].move_ids[0]
    result = apply_command(
        release, history,
        _command(history, release, "direction", "update-character-state", {
            "move_id": move_id,
            "objective_id": eleanor.quick_start.immediate_objective_ids[0],
            "objective_status": "advanced",
            "belief_proposition_id": eleanor.quick_start.opening_belief_proposition_ids[0],
            "belief_stance": "uncertain",
            "human_direction": "Protect Ruth's agency; ask before disclosing her history.",
        }), auth,
    )
    assert result.receipt.accepted
    state = replay(release, result.history)["character_states"]["eleanor-vale"]
    assert state["chosen_moves"][0]["move_id"] == move_id
    assert state["belief_stances"]["vale-staged-disappearance"] == "uncertain"
    assert state["human_direction"][0]["direction"].startswith("Protect Ruth")
    snapshot = seat_snapshot(release, result.history, auth)
    assert snapshot["character_state"] == state
    assert "update-character-state" in snapshot["allowed_actions"]


def test_current_phase_rejects_future_moves():
    """stage11.phase-agency: an agent cannot take a Move from a future Phase."""
    game = winter_observatory_game(); release = _release(game)
    bindings = tuple(
        ActorBinding(f"b:{s.id}", Actor(f"a:{s.id}", "model", s.label), s.id, 1)
        for s in game.kernel.seats
    )
    history = create_session(release=release, session_id="phase-boundary", mode="simulation", bindings=bindings, viewers=(ViewerGrant("host", "host"),))
    history = apply_command(release, history, _command(history, release, "open", "open-session", {}), AuthorizationContext("viewer", "host")).history
    dossier = game.character_program.dossiers[0]
    future_move = dossier.phase_arcs[-1].move_ids[0]
    rejected = apply_command(
        release, history,
        _command(history, release, "future", "update-character-state", {"move_id": future_move}),
        AuthorizationContext("actor", f"a:{dossier.seat_id}", f"b:{dossier.seat_id}"),
    )
    assert not rejected.receipt.accepted
    assert rejected.receipt.trusted_reason == "Move is unavailable in the current Phase"


def test_worked_character_export_is_byte_identical(tmp_path):
    """stage11.character-example: the review package is reproducible and hash-bearing."""
    first = run(tmp_path / "first")
    second = run(tmp_path / "second")
    assert first == second
    first_files = {
        item.relative_to(tmp_path / "first"): item.read_bytes()
        for item in sorted((tmp_path / "first").rglob("*")) if item.is_file()
    }
    second_files = {
        item.relative_to(tmp_path / "second"): item.read_bytes()
        for item in sorted((tmp_path / "second").rglob("*")) if item.is_file()
    }
    assert first_files == second_files
