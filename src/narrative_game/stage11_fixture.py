"""Stage 11 worked reference experience over one exact game package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from narrative_game.compiler import (
    GameRelease,
    compile_candidate,
    freeze_candidate,
    reference_component_lock,
)
from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.examples import vanished_ledger_blueprint
from narrative_game.experience import (
    dispatch_session_intent,
    host_projection,
    maker_projection,
    player_projection,
    print_projection,
    render_reference_html,
)
from narrative_game.physical import PhysicalExport, export_physical
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    SessionHistory,
    ViewerGrant,
    create_session,
)


@dataclass(frozen=True)
class Stage11Result:
    release: GameRelease
    physical: PhysicalExport
    session: SessionHistory
    output_root: Path
    summary: dict


def _package():
    blueprint = vanished_ledger_blueprint()
    frozen = freeze_candidate(
        game=blueprint.materialize_game(),
        materials=blueprint.material_inputs(),
        seed=blueprint.seed,
        component_lock=reference_component_lock(),
        compilation_options={
            "locale": "en-US",
            "presentation": "hybrid",
            "physical_provenance": "fictional-game-material",
            "displayed_claims": [item.to_mapping() for item in blueprint.displayed_claims],
        },
    )
    if frozen.candidate is None:
        raise ValueError("Stage 11 Blueprint did not freeze")
    compiled = compile_candidate(frozen.candidate)
    if compiled.release is None:
        raise ValueError("Stage 11 Candidate did not compile")
    return blueprint, compiled.release, export_physical(compiled.release)


def run(root: str | Path) -> Stage11Result:
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Stage 11 output root must be empty: {root}")
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    blueprint, release, physical = _package()
    host_auth = AuthorizationContext("viewer", "host-viewer")
    avery_auth = AuthorizationContext("actor", "avery-actor", "avery-binding")
    blake_auth = AuthorizationContext("actor", "blake-actor", "blake-binding")
    history = create_session(
        release=release,
        session_id="vanished-ledger-reference",
        mode="live",
        bindings=(
            ActorBinding("avery-binding", Actor("avery-actor", "human", "Avery Player"), "avery", 1),
            ActorBinding("blake-binding", Actor("blake-actor", "human", "Blake Player"), "blake", 1),
        ),
        viewers=(ViewerGrant("host-viewer", "host"),),
    )
    created_host = host_projection(release, physical, history, host_auth)
    history = dispatch_session_intent(
        release,
        history,
        host_auth,
        created_host,
        action_id="open-session",
        payload={},
        command_id="reference-open",
    ).history
    opening_avery = player_projection(release, history, avery_auth)
    history = dispatch_session_intent(
        release,
        history,
        avery_auth,
        opening_avery,
        action_id="request-hint",
        payload={"request": "How does the key notation connect to the payment?"},
        command_id="reference-hint-request",
    ).history
    maker, tutorial = maker_projection(
        blueprint,
        release,
        physical,
        lineage={
            "proposals": 0,
            "playtest_runs": 0,
            "standing": "development_only",
        },
    )
    projections = {
        "maker": maker,
        "host": host_projection(release, physical, history, host_auth),
        "player-avery": player_projection(release, history, avery_auth),
        "player-blake": player_projection(release, history, blake_auth),
        "print": print_projection(release, physical),
    }
    for name, projection in projections.items():
        (output / f"{name}.html").write_bytes(render_reference_html(projection))
        (output / f"{name}.json").write_bytes(canonical_json(projection.to_mapping()))
    (output / "tutorial.json").write_bytes(canonical_json(tutorial.to_mapping()))
    (output / "game-release.zip").write_bytes(release.bundle_bytes)
    (output / "physical-package.zip").write_bytes(physical.archive_bytes)
    (output / "session-history.json").write_bytes(history.to_bytes())
    summary = {
        "schema_version": "0.11",
        "release_id": release.release_id,
        "physical_export_id": physical.export_id,
        "session_id": history.session_id,
        "session_revision": history.sequence,
        "tutorial_id": tutorial.tutorial_id,
        "projections": {
            name: {
                "projection_id": projection.projection_id,
                "html_hash": digest_bytes((output / f"{name}.html").read_bytes()),
            }
            for name, projection in sorted(projections.items())
        },
    }
    (output / "stage11-result.json").write_bytes(canonical_json(summary))
    return Stage11Result(release, physical, history, output, summary)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args(argv)
    result = run(args.output_root)
    print(canonical_json(result.summary).decode("utf-8"))


if __name__ == "__main__":  # pragma: no cover
    main()
