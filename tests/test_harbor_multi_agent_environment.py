"""Capability tests for the Harbor-facing multi-agent RL environment."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

from narrative_game.adapters.harbor import (
    HarborTaskExporter,
    expand_trainable_rollouts,
    verify_artifact_files,
    write_trial_artifacts,
)
from narrative_game.compiler import compile_candidate
from narrative_game.contracts.canonical import canonical_json
from narrative_game.simulation import (
    EpisodeArchive,
    EpisodeConfig,
    MultiAgentEpisode,
    PolicyCallReceipt,
    PolicyCallUsage,
    PolicyIdentity,
    PolicyLineup,
    SeatAssignment,
    ToolCall,
    evaluate_episode,
    plan_role_rotated_episodes,
    verify_episode,
)
from narrative_game.runtime import replay
from narrative_game.stage3_fixture import build_micro_candidate


FIXTURE = Path(__file__).parents[1] / "fixtures" / "micro-game" / "game.json"


def release():
    result = compile_candidate(build_micro_candidate(FIXTURE.read_bytes()))
    assert result.release is not None
    return result.release


def lineup() -> PolicyLineup:
    return PolicyLineup(
        (
            SeatAssignment(
                "avery", PolicyIdentity("policy-avery", "fixture", "model-a", "agent-a", "context-a")
            ),
            SeatAssignment(
                "blake", PolicyIdentity("policy-blake", "fixture", "model-b", "agent-b", "context-b")
            ),
        ),
        PolicyIdentity("policy-host", "fixture", "host-model", "host-agent", "host-context"),
    )


def receipt(label: str) -> PolicyCallReceipt:
    number = sum(label.encode("utf-8"))
    return PolicyCallReceipt(f"tokens-{label}", (number,), (number + 1,), (0, 1), (-0.25,))


def usage(label: str) -> PolicyCallUsage:
    number = len(label)
    return PolicyCallUsage(number, 2, 1, 0.001, "fixture/model", f"response-{label}")


def complete_episode(
    *,
    changed_line: str = "I found the register entry.",
    reward_version: str = "narrative-multi-agent-reward-v3",
    hypothesis_id: str = "inside-job",
):
    game_release = release()
    episode = MultiAgentEpisode.reset(
        game_release,
        episode_seed=91,
        lineup=lineup(),
        config=EpisodeConfig(max_steps=20, reward_version=reward_version),
    )
    credentials = episode.credentials
    host = episode.active_actor_id
    assert host is not None and host.startswith("host:")
    episode.step(
        credentials[host],
        ToolCall("call-open", "open_session", {}),
        policy_receipt=receipt("open"),
    )
    first = episode.active_actor_id
    assert first is not None
    episode.step(
        credentials[first],
        ToolCall("call-first-opening", "inspect_evidence", {"resource_id": "key-register"}),
        policy_receipt=receipt("first-opening"),
        policy_usage=usage("first-opening"),
        reasoning_summary="Share the strongest role-visible record first.",
    )
    second = episode.active_actor_id
    assert second is not None
    episode.step(
        credentials[second],
        ToolCall("call-second-opening", "inspect_evidence", {"resource_id": "closing-interview"}),
        policy_receipt=receipt("second-opening"),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall("call-phase", "advance_phase", {"phase_id": "resolution"}),
        policy_receipt=receipt("phase"),
    )
    first = episode.active_actor_id
    assert first is not None
    episode.step(
        credentials[first],
        ToolCall("call-first-resolution", "request_evidence", {"resource_id": "cash-receipt"}),
        policy_receipt=receipt("first-resolution"),
    )
    second = episode.active_actor_id
    assert second is not None
    episode.step(
        credentials[second],
        ToolCall("call-second-request", "request_evidence", {"resource_id": "camera-log"}),
        policy_receipt=receipt("second-request"),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(
            "call-disclose-receipt",
            "disclose_resource",
            {
                "resource_id": "cash-receipt",
                "audience_seat_ids": ["avery"],
                "evidence_grade": "runtime-enforced",
            },
        ),
        policy_receipt=receipt("disclose-receipt"),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall("call-inspect-receipt", "inspect_evidence", {"resource_id": "cash-receipt"}),
        policy_receipt=receipt("inspect-receipt"),
    )
    assert episode.active_actor_id == second
    episode.step(
        credentials[second],
        ToolCall(
            "call-share-interview",
            "share_evidence",
            {"resource_id": "closing-interview", "finding": changed_line},
        ),
        policy_receipt=receipt("share-interview"),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(
            "call-disclose-camera",
            "disclose_resource",
            {
                "resource_id": "camera-log",
                "audience_seat_ids": ["blake"],
                "evidence_grade": "runtime-enforced",
            },
        ),
        policy_receipt=receipt("disclose-camera"),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            "call-share-receipt",
            "share_evidence",
            {"resource_id": "cash-receipt", "finding": "The payment was undeclared."},
        ),
        policy_receipt=receipt("share-receipt"),
    )
    assert episode.active_actor_id == second
    episode.step(
        credentials[second],
        ToolCall("call-inspect-camera", "inspect_evidence", {"resource_id": "camera-log"}),
        policy_receipt=receipt("inspect-camera"),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall("call-host-summary", "broadcast", {"text": "Submit only from inspected records."}),
        policy_receipt=receipt("host-summary"),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            "call-resolution",
            "submit_resolution",
            {
                "hypothesis_id": hypothesis_id,
                "evidence_resource_ids": ["key-register", "cash-receipt"],
                "explanation": "The key and payment records independently agree.",
            },
        ),
        policy_receipt=receipt("resolution"),
    )
    assert episode.done
    return game_release, episode.archive()


def test_reset_binds_isolated_roles_and_seeded_schedule_without_truth_leakage():
    """harbor-rl.reset-isolation: reset returns only role-authorized projections."""
    game_release = release()
    episode = MultiAgentEpisode.reset(game_release, episode_seed=91, lineup=lineup())
    observations = {
        actor_id: episode.observe(credential)
        for actor_id, credential in episode.credentials.items()
        if actor_id.startswith("seat:")
    }
    assert len(observations) == 2
    for actor_id, observation in observations.items():
        seat_id = actor_id.split(":", 2)[1]
        assert observation["game"]["seat"]["id"] == seat_id
        serialized = json.dumps(observation)
        assert '"truth_model"' not in serialized
        assert '"correct_hypothesis_id"' not in serialized
        assert observation["legal_tools"] == []
        requestable = {
            item["resource_id"] for item in observation["requestable_resources"]
        }
        assert "key-register" in requestable
        assert ("cash-receipt" in requestable) == (seat_id == "avery")
        assert ("camera-log" in requestable) == (seat_id == "blake")
    assert episode.realized_seat_order == MultiAgentEpisode.reset(
        game_release, episode_seed=91, lineup=lineup()
    ).realized_seat_order


def test_model_host_receives_facilitator_controls_without_answer_graph():
    """arena.facilitator-blindness: a model host can facilitate but cannot leak truth."""
    game_release = release()
    episode = MultiAgentEpisode.reset(game_release, episode_seed=91, lineup=lineup())
    host_id = next(item for item in episode.credentials if item.startswith("host:"))
    observation = episode.observe(episode.credentials[host_id])
    serialized = json.dumps(observation)
    assert '"truth_model"' not in serialized
    assert '"correct_hypothesis_id"' not in serialized
    assert '"acceptable_proof_path_ids"' not in serialized
    assert '"hypotheses"' not in serialized
    assert '"proof_paths"' not in serialized
    assert '"character_states"' not in serialized
    assert '"private_notes"' not in serialized
    facilitator = observation["game"]["game"]["game"]["narrative"]
    assert facilitator["phases"] and facilitator["reveals"]
    assert facilitator["interventions"]


def test_unauthorized_evidence_attempt_terminates_and_hard_zeros_reward():
    """harbor-rl.hard-authorization: a cross-seat read is rejected and scores zero."""
    game_release = release()
    episode = MultiAgentEpisode.reset(game_release, episode_seed=91, lineup=lineup())
    host = episode.active_actor_id
    assert host is not None
    episode.step(episode.credentials[host], ToolCall("open", "open_session", {}), policy_receipt=receipt("o"))
    actor = episode.active_actor_id
    assert actor is not None
    seat_id = actor.split(":", 2)[1]
    forbidden = "camera-log" if seat_id == "avery" else "cash-receipt"
    result = episode.step(
        episode.credentials[actor],
        ToolCall("cross-seat-read", "inspect_evidence", {"resource_id": forbidden}),
        policy_receipt=receipt("bad"),
    )
    archive = episode.archive()
    report = evaluate_episode(game_release, archive)
    assert not result.accepted
    assert archive.termination_reason == "authorization_failure"
    assert archive.violations == ("authorization_boundary",)
    assert report.aggregate == 0.0
    assert not next(item for item in report.hard_gates if item.code == "authorization_integrity").passed


def test_resolution_phase_exposes_choices_without_the_answer_key():
    """harbor-rl.resolution-menu: exact submission IDs are visible without correctness markers."""
    game_release = release()
    episode = MultiAgentEpisode.reset(game_release, episode_seed=91, lineup=lineup())
    host = episode.active_actor_id
    assert host is not None
    episode.step(episode.credentials[host], ToolCall("open", "open_session", {}))
    for index in range(2):
        actor = episode.active_actor_id
        assert actor is not None
        episode.step(
            episode.credentials[actor],
            ToolCall(f"say-{index}", "say", {"text": "One bounded observation."}),
        )
    assert episode.active_actor_id == host
    episode.step(
        episode.credentials[host],
        ToolCall("phase", "advance_phase", {"phase_id": "resolution"}),
    )
    actor = episode.active_actor_id
    assert actor is not None
    observation = episode.observe(episode.credentials[actor])
    options = observation["game"]["candidate_theories"]
    assert {item["id"] for item in options} == {
        "inside-job",
        "outsider-entry",
    }
    assert "correct_hypothesis_id" not in json.dumps(observation)
    assert "proof_paths" not in json.dumps(observation)


def test_correct_answer_without_acquired_evidence_is_rejected_and_cannot_score():
    """arena.epistemic-lineage: knowing the answer key cannot bypass discovery."""
    game_release = release()
    episode = MultiAgentEpisode.reset(
        game_release,
        episode_seed=91,
        lineup=lineup(),
        config=EpisodeConfig(max_steps=12),
    )
    credentials = episode.credentials
    host = episode.active_actor_id
    assert host is not None
    episode.step(credentials[host], ToolCall("open", "open_session", {}))
    for index in range(2):
        actor = episode.active_actor_id
        assert actor is not None
        episode.step(
            credentials[actor],
            ToolCall(f"say-{index}", "say", {"text": "No record was inspected."}),
        )
    episode.step(
        credentials[host],
        ToolCall("phase", "advance_phase", {"phase_id": "resolution"}),
    )
    actor = episode.active_actor_id
    assert actor is not None
    rejected = episode.step(
        credentials[actor],
        ToolCall(
            "leaked-answer",
            "submit_resolution",
            {
                "hypothesis_id": "inside-job",
                "evidence_resource_ids": ["key-register", "cash-receipt"],
                "explanation": "I know the answer but did not acquire its records.",
            },
        ),
    )
    assert not rejected.accepted
    assert rejected.content["error"] == "insufficient_acquired_evidence"
    assert not episode.done
    assert replay(game_release, episode.history)["submissions"] == []


def test_complete_episode_replays_exactly_and_emits_binary_reward_plus_diagnostics():
    """harbor-rl.replay-reward: verified outcome and integrity produce one shared reward."""
    game_release, archive = complete_episode()
    restored = EpisodeArchive.from_bytes(archive.to_bytes())
    report = evaluate_episode(game_release, restored)
    assert restored == archive
    assert verify_episode(game_release, restored) == ()
    assert all(item.passed for item in report.hard_gates)
    assert report.team == {"integrity": 1.0, "outcome": 1.0}
    assert report.diagnostics == {
        "balanced_participation": 1.0,
        "correct_resolution": 1.0,
        "information_exchange": 1.0,
        "low_recovery_dependence": 1.0,
        "pacing_completion": 1.0,
        "proof_path_coverage": 1.0,
        "token_attribution": 1.0,
        "tool_efficiency": 0.30000000000000004,
    }
    assert report.aggregate == 1.0


def test_incorrect_outcome_scores_zero_without_becoming_an_integrity_failure():
    """harbor-rl.binary-reward: an intact incorrect episode has integrity one and outcome zero."""
    game_release, archive = complete_episode(
        hypothesis_id="outsider-entry",
    )
    report = evaluate_episode(game_release, archive)
    assert report.team == {"integrity": 1.0, "outcome": 0.0}
    assert report.aggregate == 0.0
    assert next(item for item in report.hard_gates if item.code == "trace_valid").passed
    assert not next(item for item in report.hard_gates if item.code == "outcome").passed


def test_reward_v1_archives_keep_their_original_aggregate_semantics():
    """harbor-rl.reward-versioning: v2 does not reinterpret persisted v1 episodes."""
    game_release, archive = complete_episode(
        reward_version="narrative-multi-agent-reward-v1"
    )
    report = evaluate_episode(game_release, archive)
    assert report.team == report.diagnostics
    assert report.aggregate == 0.9125
    assert any(item.code == "proof_bearing_resolution" for item in report.hard_gates)


def test_edited_arena_trace_fails_replay_and_cannot_retain_reward():
    """harbor-rl.trace-tamper: edited dialogue invalidates the trace and aggregate reward."""
    game_release, archive = complete_episode()
    event = archive.events[2]
    tampered = replace(
        archive,
        events=(
            *archive.events[:2],
            replace(event, payload={**event.payload, "forged": True}),
            *archive.events[3:],
        ),
    )
    findings = verify_episode(game_release, tampered)
    report = evaluate_episode(game_release, tampered)
    assert any("arena event hash mismatch" in item for item in findings)
    assert report.aggregate == 0.0
    assert not next(item for item in report.hard_gates if item.code == "trace_valid").passed


def test_each_trainable_role_has_a_separate_token_attributed_rollout():
    """harbor-rl.credit-assignment: one team trial expands to isolated policy rollouts."""
    game_release, archive = complete_episode()
    rollouts = expand_trainable_rollouts(game_release, archive)
    assert len(rollouts) == 3
    assert len({item.actor_id for item in rollouts}) == 3
    assert len({item.policy_id for item in rollouts}) == 3
    assert all(item.input_token_ids and item.output_token_ids and item.mask_ids for item in rollouts)
    assert all(item.episode_id == archive.episode_id for item in rollouts)
    assert all(item.reward == 1.0 for item in rollouts)


def test_harbor_task_and_trial_artifacts_are_complete_and_offline_verifiable(tmp_path):
    """harbor-rl.packaging: frozen task and collected artifacts use Harbor conventions."""
    game_release, archive = complete_episode()
    task = HarborTaskExporter("narrative/sybils-cave", "Frozen multi-agent game episode")
    task_root = task.export(game_release, tmp_path / "task")
    artifacts = write_trial_artifacts(game_release, archive, tmp_path / "logs" / "artifacts")
    assert (task_root / "environment" / "release.zip").read_bytes() == game_release.bundle_bytes
    assert 'schema_version = "1.3"' in (task_root / "task.toml").read_text()
    assert "/logs/artifacts/episode.json" in (task_root / "tests" / "test.sh").read_text()
    assert set(artifacts) == {
        "episode", "release_attestation", "reward", "reward_details", "rollouts", "session"
    }
    reward = json.loads(Path(artifacts["reward"]).read_bytes())
    assert reward["reward"] == 1.0
    assert reward["integrity"] == 1.0
    assert reward["outcome"] == 1.0
    assert reward["diagnostic_tool_efficiency"] == 0.30000000000000004
    assert len(list((tmp_path / "logs" / "artifacts" / "trajectories").glob("*.json"))) == 3
    verifier_root = tmp_path / "logs" / "verifier"
    assert verify_artifact_files(
        task_root / "environment" / "release.zip", artifacts["episode"], verifier_root
    ) == 0
    assert json.loads((verifier_root / "reward.json").read_bytes())["reward"] == 1.0


def test_policy_behavior_can_change_without_changing_release_or_reward_contract():
    """harbor-rl.policy-variable: policy behavior varies independently of environment semantics."""
    release_a, archive_a = complete_episode(changed_line="The register is decisive.")
    release_b, archive_b = complete_episode(changed_line="The interview is more persuasive.")
    assert release_a.release_id == release_b.release_id
    assert archive_a.episode_id == archive_b.episode_id
    assert archive_a.version_locks == archive_b.version_locks
    assert archive_a.config.reward_version == archive_b.config.reward_version
    assert archive_a.to_bytes() != archive_b.to_bytes()
    assert evaluate_episode(release_a, archive_a).aggregate == evaluate_episode(
        release_b, archive_b
    ).aggregate


def test_twenty_episode_plan_rotates_four_roles_across_two_model_families():
    """harbor-rl.falsifying-matrix: 20 trials rotate four Seats across two model families."""
    policies = tuple(
        PolicyIdentity(
            f"policy-{family}-{index}",
            "fixture",
            f"{family}-model",
            f"agent-{family}-{index}",
            f"context-{family}-{index}",
        )
        for family in ("family-a", "family-b")
        for index in range(4)
    )
    plan = plan_role_rotated_episodes(
        release_id="sha256:" + "a" * 64,
        seat_ids=("historian", "conservator", "reporter", "appraiser"),
        player_policy_pool=policies,
        host_policy=PolicyIdentity(
            "deterministic-host", "fixture", "host-v1", "host", "host-context", False
        ),
        episode_count=20,
        seed=4100,
    )
    assert len(plan.assignments) == 20
    assert len({item.episode_seed for item in plan.assignments}) == 20
    for seat_id in ("historian", "conservator", "reporter", "appraiser"):
        models = {
            assignment.policy.model
            for episode in plan.assignments
            for assignment in episode.lineup.seats
            if assignment.seat_id == seat_id
        }
        assert models == {"family-a-model", "family-b-model"}
    assert plan.plan_id == plan_role_rotated_episodes(
        release_id=plan.release_id,
        seat_ids=("historian", "conservator", "reporter", "appraiser"),
        player_policy_pool=policies,
        host_policy=PolicyIdentity(
            "deterministic-host", "fixture", "host-v1", "host", "host-context", False
        ),
        episode_count=20,
        seed=4100,
    ).plan_id


def test_harbor_agent_writes_native_atif_with_global_and_role_local_traces(tmp_path):
    """harbor-rl.atif: Harbor Viewer receives a native chronological multi-agent trace."""
    pytest.importorskip("harbor")
    from harbor.models.trajectories import Trajectory

    from narrative_game.adapters.harbor_agent import write_atif_trajectory

    game_release, archive = complete_episode()
    destination = write_atif_trajectory(
        archive,
        tmp_path / "agent" / "trajectory.json",
        reward=evaluate_episode(game_release, archive),
        instruction="Play the fixture investigation.",
    )
    trajectory = Trajectory.model_validate_json(destination.read_text())
    assert trajectory.schema_version == "ATIF-v1.7"
    assert trajectory.session_id == archive.episode_id
    assert trajectory.steps[0].source == "user"
    assert trajectory.steps[2].reasoning_content == (
        "Share the strongest role-visible record first."
    )
    assert trajectory.steps[2].metrics.prompt_tokens == len("first-opening")
    assert [item.extra["arena_sequence"] for item in trajectory.steps[1:]] == sorted(
        step.arena_sequence
        for role_trajectory in archive.trajectories
        for step in role_trajectory.steps
    )
    assert trajectory.subagent_trajectories is not None
    assert len(trajectory.subagent_trajectories) == len(archive.trajectories)
    assert {item.extra["actor_id"] for item in trajectory.subagent_trajectories} == {
        item.actor_id for item in archive.trajectories
    }


def test_concrete_harbor_agent_builds_deterministic_isolated_role_lineup(tmp_path):
    """harbor-rl.concrete-agent: Harbor can instantiate the arena without a subclass."""
    pytest.importorskip("harbor")
    from narrative_game.adapters.harbor_agent import HarborMultiAgentArenaAgent

    agent = HarborMultiAgentArenaAgent(
        logs_dir=tmp_path,
        model_name="openai/gpt-5.6-terra",
        host_model_name="openai/gpt-5.6-sol",
        role_models_json='{"seat:avery":"openai/gpt-5.6-luna"}',
        episode_seed="71",
        trainable="false",
    )
    game_release = release()
    first = agent.trial_lineup(
        "Play the investigation.", game_release.release_id, ("avery", "blake")
    )
    second = agent.trial_lineup(
        "A changed instruction does not change identity.",
        game_release.release_id,
        ("blake", "avery"),
    )
    assert first == second
    assert first.host.model == "openai/gpt-5.6-sol"
    assert {item.seat_id: item.policy.model for item in first.seats} == {
        "avery": "openai/gpt-5.6-luna",
        "blake": "openai/gpt-5.6-terra",
    }
    contexts = {item.policy.context_id for item in first.seats} | {
        first.host.context_id
    }
    assert len(contexts) == 3
    assert not any(item.policy.trainable for item in first.seats)


def test_harbor_model_policy_records_safe_rationale_usage_and_exact_tokens(tmp_path):
    """harbor-rl.provider-policy: one provider call becomes an auditable policy decision."""
    pytest.importorskip("harbor")
    from harbor.llms.base import LLMResponse
    from harbor.models.metric import UsageInfo

    from narrative_game.adapters.harbor_agent import HarborModelArenaPolicy

    class FakeLLM:
        def __init__(self):
            self.calls = []

        async def call(self, prompt, **kwargs):
            self.calls.append(kwargs)
            assert '"legal_tools":["say"]' in prompt
            assert kwargs["message_history"][0]["role"] == "system"
            return LLMResponse(
                content=json.dumps(
                    {
                        "reasoning_summary": "A public claim advances the investigation.",
                        "tool": "say",
                        "arguments": {"text": "Compare the two records."},
                    }
                ),
                reasoning_content="provider-private-reasoning-must-not-be-recorded",
                model_name="openai/gpt-5.6-sol",
                usage=UsageInfo(
                    prompt_tokens=12,
                    completion_tokens=4,
                    cache_tokens=2,
                    cost_usd=0.02,
                ),
                response_id=f"response-{len(self.calls)}",
                prompt_token_ids=[10, 11],
                completion_token_ids=[20, 21],
                logprobs=[-0.1, -0.2],
            )

    llm = FakeLLM()
    policy = HarborModelArenaPolicy(
        identity=PolicyIdentity(
            "policy-a", "openai", "gpt-5.6-sol", "agent-a", "context-a", True
        ),
        role="seat:avery",
        instruction="Play the investigation.",
        llm=llm,
        logging_root=tmp_path,
        use_responses_api=True,
    )
    decision = asyncio.run(
        policy.decide(
            {
                "actor_id": "seat:avery:policy-a",
                "role": "seat:avery",
                "legal_tools": ["say"],
                "remaining_steps": 8,
                "requestable_resources": [],
                "game": {"resources": []},
                "dialogue": [],
                "own_prior_actions": [],
            }
        )
    )
    assert decision.call.tool == "say"
    assert decision.reasoning_summary == "A public claim advances the investigation."
    assert "provider-private" not in decision.reasoning_summary
    assert decision.usage == PolicyCallUsage(
        12, 4, 2, 0.02, "openai/gpt-5.6-sol", "response-1"
    )
    assert decision.receipt is not None
    assert decision.receipt.output_token_ids == (20, 21)
    asyncio.run(
        policy.decide(
            {
                "actor_id": "seat:avery:policy-a",
                "role": "seat:avery",
                "legal_tools": ["say"],
                "remaining_steps": 7,
                "requestable_resources": [],
                "game": {"resources": []},
                "dialogue": [],
                "own_prior_actions": [],
            }
        )
    )
    assert "previous_response_id" not in llm.calls[0]
    assert llm.calls[1]["previous_response_id"] == "response-1"


def test_concrete_harbor_agent_runs_a_complete_isolated_trial_offline(tmp_path):
    """harbor-rl.agent-run: concrete async orchestration reaches verified termination."""
    pytest.importorskip("harbor")
    from harbor.llms.base import LLMResponse
    from harbor.models.agent.context import AgentContext
    from harbor.models.metric import UsageInfo

    from narrative_game.adapters.harbor_agent import HarborMultiAgentArenaAgent

    game_release = release()
    environment_config = canonical_json(
        {
            "release_id": game_release.release_id,
            "bundle_hash": game_release.bundle_hash,
            "episode_config": EpisodeConfig(max_steps=12).to_mapping(),
        }
    )

    class FakeEnvironment:
        async def download_file(self, remote, local):
            value = (
                game_release.bundle_bytes
                if remote.endswith("release.zip")
                else environment_config
            )
            Path(local).write_bytes(value)

        async def upload_dir(self, source, destination):
            assert destination == "/logs/artifacts"
            target = tmp_path / "collected-artifacts"
            target.mkdir(exist_ok=True)
            for path in Path(source).rglob("*"):
                if path.is_file():
                    output = target / path.relative_to(source)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(path.read_bytes())

    class ScriptedLLM:
        def __init__(self, role):
            self.role = role
            self.calls = 0

        async def call(self, prompt, **kwargs):
            del kwargs
            self.calls += 1
            observation = json.loads(prompt)["authorized_observation"]
            snapshot = observation["game"]
            state = snapshot.get("state", snapshot)
            if self.role == "host":
                if self.calls == 1:
                    tool, arguments = "open_session", {}
                elif self.calls == 2:
                    tool, arguments = "advance_phase", {"phase_id": "resolution"}
                elif self.calls == 3:
                    tool, arguments = "disclose_resource", {
                        "resource_id": "cash-receipt",
                        "audience_seat_ids": ["avery"],
                        "evidence_grade": "runtime-enforced",
                    }
                else:
                    tool, arguments = "disclose_resource", {
                        "resource_id": "camera-log",
                        "audience_seat_ids": ["blake"],
                        "evidence_grade": "runtime-enforced",
                    }
            elif self.role == "avery" and self.calls == 1:
                tool, arguments = "inspect_evidence", {"resource_id": "key-register"}
            elif self.role == "avery" and self.calls == 2:
                tool, arguments = "request_evidence", {"resource_id": "cash-receipt"}
            elif self.role == "avery" and self.calls == 3:
                tool, arguments = "inspect_evidence", {"resource_id": "cash-receipt"}
            elif self.role == "avery":
                tool, arguments = "submit_resolution", {
                    "hypothesis_id": "inside-job",
                    "evidence_resource_ids": ["key-register", "cash-receipt"],
                    "explanation": "The independently inspected key and payment records agree.",
                }
            elif self.calls == 1:
                tool, arguments = "inspect_evidence", {"resource_id": "closing-interview"}
            elif self.calls == 2:
                tool, arguments = "request_evidence", {"resource_id": "camera-log"}
            else:
                tool, arguments = "share_evidence", {
                    "resource_id": "closing-interview",
                    "finding": "The clerk admitted returning after a call.",
                }
            return LLMResponse(
                content=json.dumps(
                    {
                        "reasoning_summary": f"{self.role} selects a legal next action.",
                        "tool": tool,
                        "arguments": arguments,
                    }
                ),
                model_name="fixture/model",
                usage=UsageInfo(
                    prompt_tokens=10,
                    completion_tokens=3,
                    cache_tokens=1,
                    cost_usd=0.001,
                ),
                response_id=f"{self.role}-{self.calls}",
            )

    class FixtureAgent(HarborMultiAgentArenaAgent):
        def _create_llm(self, identity):
            role = "host" if identity.agent_id.endswith("host") else identity.agent_id.removeprefix(
                "harbor-agent-seat:"
            )
            return ScriptedLLM(role)

    agent = FixtureAgent(
        logs_dir=tmp_path / "agent",
        model_name="fixture/model",
        episode_seed=91,
        trainable=False,
    )
    context = AgentContext()
    asyncio.run(agent.run("Play the fixture investigation.", FakeEnvironment(), context))
    archive = EpisodeArchive.from_bytes(
        (tmp_path / "collected-artifacts" / "episode.json").read_bytes()
    )
    assert archive.termination_reason == "accepted_resolution"
    assert verify_episode(game_release, archive) == ()
    assert context.n_input_tokens and context.n_input_tokens > 0
    assert context.n_output_tokens and context.n_output_tokens > 0
    assert context.rollout_details is None
    assert (tmp_path / "agent" / "trajectory.json").is_file()
