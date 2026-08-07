"""Optional Harbor task, artifact, and trainer-rollout boundary.

This module deliberately does not import Harbor.  A Harbor ``BaseAgent`` can
compose ``MultiAgentArenaRunner`` with provider-specific policy adapters while
this boundary keeps the task and verifier products stable and offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
import json
from pathlib import Path
import re
from typing import Any, Mapping

from narrative_game.compiler import GameRelease, load_release
from narrative_game.contracts.canonical import canonical_json
from narrative_game.simulation import EpisodeArchive, EpisodeConfig, evaluate_episode


PACKAGE_VERSION = version("narrative-game-library")


@dataclass(frozen=True)
class TrainerRollout:
    actor_id: str
    policy_id: str
    role: str
    reward: float
    input_token_ids: tuple[int, ...]
    output_token_ids: tuple[int, ...]
    mask_ids: tuple[int, ...]
    logprobs: tuple[float, ...]
    episode_id: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "policy_id": self.policy_id,
            "role": self.role,
            "reward": self.reward,
            "input_token_ids": list(self.input_token_ids),
            "output_token_ids": list(self.output_token_ids),
            "mask_ids": list(self.mask_ids),
            "logprobs": list(self.logprobs),
            "episode_id": self.episode_id,
        }


def expand_trainable_rollouts(
    release: GameRelease, archive: EpisodeArchive
) -> tuple[TrainerRollout, ...]:
    """Expand one team trial into one token-attributed rollout per trainable role."""
    report = evaluate_episode(release, archive)
    rollouts = []
    for trajectory in sorted(archive.trajectories, key=lambda item: item.actor_id):
        if not trajectory.policy.trainable:
            continue
        receipts = [item.policy_receipt for item in trajectory.steps]
        if not receipts or any(item is None for item in receipts):
            raise ValueError(f"trainable trajectory lacks token attribution: {trajectory.actor_id}")
        resolved = [item for item in receipts if item is not None]
        rollouts.append(
            TrainerRollout(
                trajectory.actor_id,
                trajectory.policy.policy_id,
                trajectory.role,
                report.aggregate,
                tuple(token for receipt in resolved for token in receipt.input_token_ids),
                tuple(token for receipt in resolved for token in receipt.output_token_ids),
                tuple(token for receipt in resolved for token in receipt.mask_ids),
                tuple(value for receipt in resolved for value in receipt.logprobs),
                archive.episode_id,
            )
        )
    return tuple(rollouts)


def _safe_actor_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)


def write_trial_artifacts(
    release: GameRelease,
    archive: EpisodeArchive,
    root: str | Path,
) -> Mapping[str, str]:
    """Write the exact files Harbor collects from ``/logs/artifacts``."""
    root = Path(root)
    trajectories = root / "trajectories"
    trajectories.mkdir(parents=True, exist_ok=True)
    report = evaluate_episode(release, archive)
    paths: dict[str, Path] = {
        "episode": root / "episode.json",
        "session": root / "session-history.json",
        "reward": root / "reward.json",
        "reward_details": root / "reward-details.json",
        "rollouts": root / "trainer-rollouts.json",
        "release_attestation": root / "release-attestation.json",
    }
    paths["episode"].write_bytes(archive.to_bytes())
    paths["session"].write_bytes(archive.session_history.to_bytes())
    reward_values = {
        "reward": report.aggregate,
        **report.team,
        **{f"diagnostic_{key}": value for key, value in report.diagnostics.items()},
    }
    paths["reward"].write_bytes(canonical_json(reward_values))
    paths["reward_details"].write_bytes(canonical_json(report.to_mapping()))
    paths["rollouts"].write_bytes(
        canonical_json(
            [item.to_mapping() for item in expand_trainable_rollouts(release, archive)]
        )
    )
    paths["release_attestation"].write_bytes(
        canonical_json(
            {
                "release_id": release.release_id,
                "candidate_id": release.candidate_id,
                "bundle_hash": release.bundle_hash,
                "component_lock": release.manifest["component_lock"],
            }
        )
    )
    for trajectory in archive.trajectories:
        path = trajectories / f"{_safe_actor_id(trajectory.actor_id)}.json"
        path.write_bytes(canonical_json(trajectory.to_mapping()))
    return {key: str(path) for key, path in sorted(paths.items())}


@dataclass(frozen=True)
class HarborTaskExporter:
    """Materialize one frozen Release as a Harbor task directory."""

    task_name: str
    description: str
    package_requirement: str = f"narrative-game-library=={PACKAGE_VERSION}"

    def export(
        self,
        release: GameRelease,
        destination: str | Path,
        *,
        config: EpisodeConfig = EpisodeConfig(),
    ) -> Path:
        destination = Path(destination)
        environment_root = destination / "environment"
        environment_root.mkdir(parents=True, exist_ok=True)
        (destination / "tests").mkdir(parents=True, exist_ok=True)
        (environment_root / "release.zip").write_bytes(release.bundle_bytes)
        (environment_root / "environment.json").write_bytes(
            canonical_json(
                {
                    "release_id": release.release_id,
                    "bundle_hash": release.bundle_hash,
                    "episode_config": config.to_mapping(),
                }
            )
        )
        (destination / "instruction.md").write_text(
            "# Multi-agent narrative episode\n\n"
            "Run one complete role-isolated episode against `/opt/narrative/release.zip`. "
            "Publish the canonical Episode Archive at `/logs/artifacts/episode.json`.\n",
            encoding="utf-8",
        )
        task_toml = f'''schema_version = "1.3"

[task]
name = {json.dumps(self.task_name)}
description = {json.dumps(self.description)}
authors = [{{ name = "Jarred Parrett" }}]
keywords = ["multi-agent", "narrative", "rl", "role-isolation"]

[metadata]
release_id = {json.dumps(release.release_id)}
arena_version = "1.0.0"

[agent]
timeout_sec = 3600.0

[verifier]
timeout_sec = 300.0

[environment]
build_timeout_sec = 900.0
'''
        (destination / "task.toml").write_text(task_toml, encoding="utf-8")
        dockerfile = f'''FROM python:3.11-slim
RUN python -m pip install --no-cache-dir {json.dumps(self.package_requirement)}
COPY release.zip /opt/narrative/release.zip
COPY environment.json /opt/narrative/environment.json
WORKDIR /app
'''
        (environment_root / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        test_script = '''#!/bin/sh
set -eu
mkdir -p /logs/verifier
python -m narrative_game.adapters.harbor \\
  --release /opt/narrative/release.zip \\
  --episode /logs/artifacts/episode.json \\
  --output /logs/verifier
'''
        test_path = destination / "tests" / "test.sh"
        test_path.write_text(test_script, encoding="utf-8")
        test_path.chmod(0o755)
        return destination


def verify_artifact_files(
    release_path: str | Path,
    episode_path: str | Path,
    output: str | Path,
) -> int:
    release = load_release(Path(release_path).read_bytes())
    archive = EpisodeArchive.from_bytes(Path(episode_path).read_bytes())
    report = evaluate_episode(release, archive)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "reward.json").write_bytes(
        canonical_json(
            {
                "reward": report.aggregate,
                **report.team,
                **{
                    f"diagnostic_{key}": value
                    for key, value in report.diagnostics.items()
                },
            }
        )
    )
    (output / "reward-details.json").write_bytes(canonical_json(report.to_mapping()))
    return 0 if all(item.passed for item in report.hard_gates) else 1


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Verify one Harbor arena Episode Archive")
    parser.add_argument("--release", required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(verify_artifact_files(args.release, args.episode, args.output))


if __name__ == "__main__":  # pragma: no cover
    main()
