"""Provider-neutral policy runner for one multi-agent episode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .environment import MultiAgentEpisode
from .model import EpisodeArchive, PolicyCallReceipt, PolicyCallUsage, ToolCall


@dataclass(frozen=True)
class PolicyDecision:
    call: ToolCall
    receipt: PolicyCallReceipt | None = None
    usage: PolicyCallUsage | None = None
    reasoning_summary: str | None = None


class ArenaPolicy(Protocol):
    """A model/provider adapter with one permanently isolated policy context."""

    def decide(self, observation: Mapping[str, Any]) -> PolicyDecision:
        """Choose exactly one tool call and return its exact token receipt."""


class MultiAgentArenaRunner:
    """Drive isolated policies through the episode's AEC schedule."""

    def run(
        self,
        episode: MultiAgentEpisode,
        policies: Mapping[str, ArenaPolicy],
    ) -> EpisodeArchive:
        required = set(episode.credentials)
        if set(policies) != required:
            raise ValueError("Runner requires exactly one Policy adapter per arena Actor")
        while not episode.done:
            actor_id = episode.active_actor_id
            if actor_id is None:  # pragma: no cover - guarded by episode.done.
                break
            credential = episode.credentials[actor_id]
            observation = episode.observe(credential)
            decision = policies[actor_id].decide(observation)
            episode.step(
                credential,
                decision.call,
                policy_receipt=decision.receipt,
                policy_usage=decision.usage,
                reasoning_summary=decision.reasoning_summary,
            )
        return episode.archive()


class AsyncArenaPolicy(Protocol):
    """An asynchronous provider adapter with one isolated policy context."""

    async def decide(self, observation: Mapping[str, Any]) -> PolicyDecision:
        """Choose exactly one tool call from a role-authorized observation."""


class AsyncMultiAgentArenaRunner:
    """Asynchronous AEC runner used by provider-backed Harbor agents."""

    async def run(
        self,
        episode: MultiAgentEpisode,
        policies: Mapping[str, AsyncArenaPolicy],
    ) -> EpisodeArchive:
        required = set(episode.credentials)
        if set(policies) != required:
            raise ValueError("Runner requires exactly one Policy adapter per arena Actor")
        while not episode.done:
            actor_id = episode.active_actor_id
            if actor_id is None:  # pragma: no cover - guarded by episode.done.
                break
            credential = episode.credentials[actor_id]
            observation = episode.observe(credential)
            decision = await policies[actor_id].decide(observation)
            episode.step(
                credential,
                decision.call,
                policy_receipt=decision.receipt,
                policy_usage=decision.usage,
                reasoning_summary=decision.reasoning_summary,
            )
        return episode.archive()
