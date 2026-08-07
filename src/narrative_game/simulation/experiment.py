"""Deterministic role-rotation plans for multi-agent evaluation jobs."""

from __future__ import annotations

from dataclasses import dataclass

from narrative_game.contracts.canonical import digest_json

from .model import PolicyIdentity, PolicyLineup, SeatAssignment


@dataclass(frozen=True)
class EpisodeAssignment:
    index: int
    episode_seed: int
    lineup: PolicyLineup

    def to_mapping(self) -> dict:
        return {
            "index": self.index,
            "episode_seed": self.episode_seed,
            "lineup": self.lineup.to_mapping(),
        }


@dataclass(frozen=True)
class RoleRotationPlan:
    release_id: str
    assignments: tuple[EpisodeAssignment, ...]

    @property
    def plan_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict:
        return {
            "schema_version": "1.0",
            "release_id": self.release_id,
            "assignments": [item.to_mapping() for item in self.assignments],
        }


def plan_role_rotated_episodes(
    *,
    release_id: str,
    seat_ids: tuple[str, ...],
    player_policy_pool: tuple[PolicyIdentity, ...],
    host_policy: PolicyIdentity,
    episode_count: int = 20,
    seed: int = 0,
) -> RoleRotationPlan:
    """Plan reproducible policy/seat rotations without running or training them."""
    seats = tuple(sorted(seat_ids))
    policies = tuple(sorted(player_policy_pool, key=lambda item: item.policy_id))
    if len(seats) < 2 or len(set(seats)) != len(seats):
        raise ValueError("Role rotation requires at least two unique Seats")
    if len(policies) < len(seats):
        raise ValueError("Policy pool must contain at least one isolated Policy per Seat")
    if episode_count < 1:
        raise ValueError("episode_count must be positive")
    assignments = []
    for index in range(episode_count):
        offset = index % len(policies)
        selected = tuple(policies[(offset + item) % len(policies)] for item in range(len(seats)))
        assignments.append(
            EpisodeAssignment(
                index,
                seed + index,
                PolicyLineup(
                    tuple(
                        SeatAssignment(seat_id, selected[(position + index) % len(selected)])
                        for position, seat_id in enumerate(seats)
                    ),
                    host_policy,
                ),
            )
        )
    return RoleRotationPlan(release_id, tuple(assignments))
