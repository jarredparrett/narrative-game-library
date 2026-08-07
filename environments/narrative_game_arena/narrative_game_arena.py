"""Publishable Prime Hub package for the first narrative multi-agent episode."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Iterable

import verifiers.v1 as vf
from pydantic import Field, model_validator

from narrative_game.compiler import load_release
from narrative_game.simulation import EpisodeConfig
from narrative_game_prime.environment import (
    NarrativeGameEnv,
    NarrativeGameTask,
    NarrativeGameTaskData,
)


class NarrativeGameArenaTasksetConfig(vf.TasksetConfig):
    """Hosted task seeds; the immutable Release ships inside this package."""

    episode_seeds: list[int] = Field(default_factory=lambda: [91])
    episode_config: dict[str, Any] = Field(
        default_factory=lambda: EpisodeConfig(max_steps=12).to_mapping()
    )

    @model_validator(mode="after")
    def _valid_episode(self) -> "NarrativeGameArenaTasksetConfig":
        if not self.episode_seeds:
            raise ValueError("episode_seeds must contain at least one deterministic seed")
        EpisodeConfig.from_mapping(self.episode_config)
        return self


class NarrativeGameArenaTaskset(
    vf.Taskset[NarrativeGameTask, NarrativeGameArenaTasksetConfig]
):
    """Yield portable tasks from the package's exact frozen Release bytes."""

    def load(self) -> Iterable[NarrativeGameTask]:
        encoded = Path(__file__).with_name("micro-release.b64").read_text(encoding="ascii").strip()
        bundle = base64.b64decode(encoded, validate=True)
        release = load_release(bundle)
        for index, seed in enumerate(self.config.episode_seeds):
            yield NarrativeGameTask(
                NarrativeGameTaskData(
                    idx=index,
                    name=f"Prime multi-agent smoke seed {seed}",
                    description="One host and two isolated player interactions.",
                    prompt=None,
                    release_base64=base64.b64encode(bundle).decode("ascii"),
                    release_id=release.release_id,
                    episode_seed=int(seed),
                    episode_config=dict(self.config.episode_config),
                )
            )


__all__ = ["NarrativeGameArenaTaskset", "NarrativeGameEnv"]
