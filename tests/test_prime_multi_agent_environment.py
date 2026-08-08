"""Capability evidence for the native Prime Verifiers multi-agent adapter."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from types import SimpleNamespace

from narrative_game.compiler import compile_candidate
from narrative_game.simulation import EpisodeArchive, verify_episode
from narrative_game.stage3_fixture import build_micro_candidate
from narrative_game_prime.environment import (
    NarrativeGameEnv,
    NarrativeGameEnvConfig,
    NarrativeGameTaskset,
    NarrativeGameTasksetConfig,
    REWARD_NAME,
    _parse_decision_object,
)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "micro-game" / "game.json"


def test_prime_policy_recovers_one_action_object_from_trailing_model_chatter():
    """prime-rl.action-framing: trailing prose cannot crash or alter the chosen action."""
    value = _parse_decision_object(
        '{"reasoning_summary":"open","tool":"open_session","arguments":{}} trailing text'
    )
    assert value == {
        "reasoning_summary": "open",
        "tool": "open_session",
        "arguments": {},
    }


class _FakeTrace:
    def __init__(self, name: str) -> None:
        self.agent = SimpleNamespace(name=name)
        self.info: dict = {}
        self.rewards: dict[str, float] = {}
        self.metrics: dict[str, float] = {}

    def record_reward(self, name: str, value: float) -> None:
        self.rewards[name] = float(value)

    def record_metric(self, name: str, value: float) -> None:
        self.metrics[name] = float(value)

    def record_metrics(self, values) -> None:
        self.metrics.update({key: float(value) for key, value in values.items()})


class _FakeInteraction:
    def __init__(self, name: str, task, decisions) -> None:
        self.trace = _FakeTrace(name)
        self.task = task
        self.decisions = decisions
        self.messages: list[dict] = []

    async def turn(self, message: str):
        payload = json.loads(message)
        self.messages.append(payload)
        reply = self.decisions(payload["authorized_observation"])
        return SimpleNamespace(terminated=False, last_reply=json.dumps(reply))


class _FakeAgent:
    def __init__(self, name: str, model: str, decisions) -> None:
        self.name = name
        self.config = SimpleNamespace(model=model)
        self.trainable = True
        self.decisions = decisions
        self.traces: list[_FakeTrace] = []
        self.interactions: list[_FakeInteraction] = []

    @asynccontextmanager
    async def interaction(self, task):
        interaction = _FakeInteraction(self.name, task, self.decisions)
        self.interactions.append(interaction)
        try:
            yield interaction
        finally:
            self.traces.append(interaction.trace)


def _decision_policy():
    calls = {"host": 0, "seat:avery": 0, "seat:blake": 0}

    def decide(observation):
        role = observation["role"]
        calls[role] += 1
        turn = calls[role]
        if role == "host" and turn == 1:
            return {"reasoning_summary": "Open play.", "tool": "open_session", "arguments": {}}
        if role == "host" and turn == 2:
            return {
                "reasoning_summary": "Opening exchange is complete.",
                "tool": "advance_phase",
                "arguments": {"phase_id": "resolution"},
            }
        if role == "host" and turn == 3:
            return {
                "reasoning_summary": "Disclose the requested receipt.",
                "tool": "disclose_resource",
                "arguments": {
                    "resource_id": "cash-receipt",
                    "audience_seat_ids": ["avery"],
                    "evidence_grade": "runtime-enforced",
                },
            }
        if role == "host":
            return {
                "reasoning_summary": "Disclose the requested camera record.",
                "tool": "disclose_resource",
                "arguments": {
                    "resource_id": "camera-log",
                    "audience_seat_ids": ["blake"],
                    "evidence_grade": "runtime-enforced",
                },
            }
        if role == "seat:avery" and turn == 1:
            return {"reasoning_summary": "Read the key register.", "tool": "inspect_evidence", "arguments": {"resource_id": "key-register"}}
        if role == "seat:avery" and turn == 2:
            return {"reasoning_summary": "Request the payment record.", "tool": "request_evidence", "arguments": {"resource_id": "cash-receipt"}}
        if role == "seat:avery" and turn == 3:
            return {"reasoning_summary": "Read the disclosed receipt.", "tool": "inspect_evidence", "arguments": {"resource_id": "cash-receipt"}}
        if role == "seat:avery":
            return {
                "reasoning_summary": "The two acquired records establish the theory.",
                "tool": "submit_resolution",
                "arguments": {
                    "hypothesis_id": "inside-job",
                    "evidence_resource_ids": ["key-register", "cash-receipt"],
                    "explanation": "The key register and payment receipt independently agree.",
                },
            }
        if turn == 1:
            return {"reasoning_summary": "Read the interview.", "tool": "inspect_evidence", "arguments": {"resource_id": "closing-interview"}}
        if turn == 2:
            return {"reasoning_summary": "Request the camera record.", "tool": "request_evidence", "arguments": {"resource_id": "camera-log"}}
        return {
            "reasoning_summary": "Share the inspected interview with the team.",
            "tool": "share_evidence",
            "arguments": {
                "resource_id": "closing-interview",
                "finding": "The clerk admitted returning after a call.",
            },
        }

    return decide


def test_prime_runs_one_isolated_interaction_per_role_and_scores_canonical_outcome(tmp_path):
    """prime-rl.multi-agent: host plus N isolated Seats produce one verified team reward."""
    result = compile_candidate(build_micro_candidate(FIXTURE.read_bytes()))
    assert result.release is not None
    release_path = tmp_path / "release.zip"
    release_path.write_bytes(result.release.bundle_bytes)
    taskset = NarrativeGameTaskset(
        NarrativeGameTasksetConfig(
            id="narrative_game_prime",
            release_paths=[release_path],
            episode_seeds=[91],
            episode_config={
                "max_steps": 12,
                "allow_private_messages": True,
                "scheduler_version": "aec-seeded-v1",
                "tool_schema_version": "narrative-arena-tools-v2",
                "reward_version": "narrative-multi-agent-reward-v3",
            },
        )
    )
    task = next(iter(taskset))
    decisions = _decision_policy()
    agents = SimpleNamespace(
        host=_FakeAgent("host", "openai/gpt-test-host", decisions),
        player=_FakeAgent("player", "openai/gpt-test-player", decisions),
    )
    env = NarrativeGameEnv.__new__(NarrativeGameEnv)
    env.config = NarrativeGameEnvConfig(
        id="narrative_game_prime",
        taskset=taskset.config,
        train_host=False,
        train_players=True,
    )

    async def exercise():
        await env.setup(agents)
        await env.run(task, agents)
        traces = [*agents.host.traces, *agents.player.traces]
        episode = SimpleNamespace(traces=traces)
        await env.finalize(task, episode)
        return traces

    traces = asyncio.run(exercise())
    assert len(agents.host.interactions) == 1
    assert len(agents.player.interactions) == 2
    assert agents.host.trainable is False
    assert agents.player.trainable is True
    assert {trace.info["narrative_role"] for trace in traces} == {
        "host",
        "seat:avery",
        "seat:blake",
    }
    assert len({trace.info["narrative_actor_id"] for trace in traces}) == 3
    interactions_by_role = {
        interaction.task.data.role: interaction
        for interaction in [*agents.host.interactions, *agents.player.interactions]
    }
    avery_prompt = interactions_by_role["seat:avery"].task.data.system_prompt
    blake_prompt = interactions_by_role["seat:blake"].task.data.system_prompt
    host_prompt = interactions_by_role["host"].task.data.system_prompt
    assert "You are Avery Shaw (character avery-shaw). Stay in character." in avery_prompt
    assert "Blake Rowan" not in avery_prompt
    assert "You are Blake Rowan (character blake-rowan). Stay in character." in blake_prompt
    assert "Avery Shaw" not in blake_prompt
    assert "You are the facilitator, not a player character." in host_prompt
    for prompt in (avery_prompt, blake_prompt, host_prompt):
        assert "truth_model" not in prompt
        assert "correct_hypothesis_id" not in prompt
        assert "inside-job" not in prompt
    host_trace = agents.host.traces[0]
    archive = EpisodeArchive.from_bytes(
        __import__("base64").b64decode(host_trace.info["narrative_episode_archive_base64"])
    )
    assert verify_episode(result.release, archive) == ()
    assert archive.termination_reason == "accepted_resolution"
    assert all(trace.rewards[REWARD_NAME] == 1.0 for trace in traces)
    assert all(trace.metrics["integrity"] == 1.0 for trace in traces)
    assert all(trace.metrics["outcome"] == 1.0 for trace in traces)
    for interaction in agents.player.interactions:
        for message in interaction.messages:
            serialized = json.dumps(message)
            assert '"truth_model"' not in serialized
            assert '"correct_hypothesis_id"' not in serialized
