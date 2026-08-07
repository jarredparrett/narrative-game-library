"""Optional Harbor ``BaseAgent`` integration for multi-policy arena trials.

Install the ``harbor`` extra before importing this module. The concrete
:class:`HarborMultiAgentArenaAgent` uses Harbor's LiteLLM boundary to create one
isolated provider session per arena role while the library retains control of
authorization, scheduling, replay, and reward.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.llms.base import BaseLLM
from harbor.llms.lite_llm import LiteLLM
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import (
    Agent as AtifAgent,
    FinalMetrics as AtifFinalMetrics,
    Metrics as AtifMetrics,
    Observation as AtifObservation,
    ObservationResult as AtifObservationResult,
    Step as AtifStep,
    ToolCall as AtifToolCall,
    Trajectory as AtifTrajectory,
)
from pydantic import BaseModel, Field

from narrative_game.compiler import load_release
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.simulation import (
    AsyncArenaPolicy,
    AsyncMultiAgentArenaRunner,
    EpisodeArchive,
    EpisodeConfig,
    MultiAgentEpisode,
    PolicyCallReceipt,
    PolicyCallUsage,
    PolicyDecision,
    PolicyIdentity,
    PolicyLineup,
    RewardReport,
    SeatAssignment,
    ToolCall,
    evaluate_episode,
)
from narrative_game.simulation.policy_prompt import (
    TOOL_ARGUMENT_CONTRACTS as _TOOL_ARGUMENT_CONTRACTS,
    model_observation as _model_observation,
    policy_guidance as _policy_guidance,
)

from .harbor import write_trial_artifacts


def _atif_tool_definitions(archive: EpisodeArchive) -> list[dict[str, object]]:
    """Describe the exact arena tools exercised by this episode."""
    names = sorted(
        {
            step.call.tool
            for trajectory in archive.trajectories
            for step in trajectory.steps
        }
    )
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Narrative arena action: {name}",
                "parameters": {"type": "object", "additionalProperties": True},
            },
        }
        for name in names
    ]


def _atif_message(role: str, tool: str, arguments: Mapping[str, object]) -> str:
    text = arguments.get("text")
    if isinstance(text, str) and text.strip():
        return f"{role}: {text.strip()}"
    return f"{role} invoked {tool}."


def _atif_step(trajectory, step, *, step_id: int) -> AtifStep:
    """Translate one role-local arena action without exposing another role's view."""
    receipt = step.policy_receipt
    usage = step.policy_usage
    metrics = None
    if receipt is not None or usage is not None:
        extra = {}
        if receipt is not None:
            extra = {
                "receipt_id": receipt.receipt_id,
                "mask_ids": list(receipt.mask_ids),
            }
        if usage is not None and usage.response_id is not None:
            extra["response_id"] = usage.response_id
        metrics = AtifMetrics(
            prompt_tokens=(
                usage.prompt_tokens if usage is not None else len(receipt.input_token_ids)
            ),
            completion_tokens=(
                usage.completion_tokens
                if usage is not None
                else len(receipt.output_token_ids)
            ),
            cached_tokens=usage.cached_tokens if usage is not None else None,
            cost_usd=usage.cost_usd if usage is not None else None,
            prompt_token_ids=list(receipt.input_token_ids) if receipt is not None else None,
            completion_token_ids=(
                list(receipt.output_token_ids) if receipt is not None else None
            ),
            logprobs=list(receipt.logprobs) or None if receipt is not None else None,
            extra=extra or None,
        )
    observation_summary = {
        "accepted": step.result.accepted,
        "public_reason": step.result.public_reason,
        "content": step.result.content,
        "active_actor_id": step.observation.get("active_actor_id"),
        "legal_tools": step.observation.get("legal_tools", []),
        "visible_dialogue_count": len(step.observation.get("dialogue", [])),
    }
    return AtifStep(
        step_id=step_id,
        source="agent",
        model_name=(usage.model_name if usage and usage.model_name else trajectory.policy.model),
        message=_atif_message(trajectory.role, step.call.tool, step.call.arguments),
        reasoning_content=step.reasoning_summary,
        tool_calls=[
            AtifToolCall(
                tool_call_id=step.call.call_id,
                function_name=step.call.tool,
                arguments=dict(step.call.arguments),
            )
        ],
        observation=AtifObservation(
            results=[
                AtifObservationResult(
                    source_call_id=step.call.call_id,
                    content=canonical_json(observation_summary).decode("utf-8"),
                )
            ]
        ),
        metrics=metrics,
        llm_call_count=(
            1 if receipt is not None or usage is not None or step.reasoning_summary else 0
        ),
        extra={
            "actor_id": trajectory.actor_id,
            "role": trajectory.role,
            "turn": step.turn,
            "arena_sequence": step.arena_sequence,
            "session_sequence": step.session_sequence,
            "observation_hash": step.observation_hash,
            "accepted": step.result.accepted,
        },
    )


def _atif_final_metrics(steps: list[AtifStep]) -> AtifFinalMetrics:
    metrics = [step.metrics for step in steps if step.metrics is not None]
    return AtifFinalMetrics(
        total_prompt_tokens=sum(item.prompt_tokens or 0 for item in metrics),
        total_completion_tokens=sum(item.completion_tokens or 0 for item in metrics),
        total_cached_tokens=sum(item.cached_tokens or 0 for item in metrics),
        total_cost_usd=sum(item.cost_usd or 0.0 for item in metrics),
        total_steps=len(steps),
    )


def episode_to_atif(
    archive: EpisodeArchive,
    *,
    reward: RewardReport | None = None,
    instruction: str = "Run one complete role-isolated narrative-game episode.",
) -> AtifTrajectory:
    """Create one native ATIF-v1.7 trace with embedded per-role trajectories.

    The root preserves global AEC ordering for the Harbor Viewer. Embedded
    trajectories preserve policy identity and role-local credit assignment.
    """
    tool_definitions = _atif_tool_definitions(archive)
    role_trajectories = sorted(archive.trajectories, key=lambda item: item.actor_id)
    actor_by_id = {item.actor_id: item for item in role_trajectories}
    ordered_actions = sorted(
        (
            (step.arena_sequence, trajectory, step)
            for trajectory in role_trajectories
            for step in trajectory.steps
        ),
        key=lambda item: (item[0], item[1].actor_id),
    )
    root_steps = [AtifStep(step_id=1, source="user", message=instruction)]
    root_steps.extend(
        _atif_step(trajectory, step, step_id=index)
        for index, (_, trajectory, step) in enumerate(ordered_actions, start=2)
    )
    embedded = []
    for trajectory in role_trajectories:
        steps = [
            _atif_step(trajectory, step, step_id=index)
            for index, step in enumerate(trajectory.steps, start=1)
        ]
        if not steps:
            steps = [
                AtifStep(
                    step_id=1,
                    source="system",
                    message="This role received no scheduled turn before episode termination.",
                    extra={"actor_id": trajectory.actor_id, "role": trajectory.role},
                )
            ]
        embedded.append(
            AtifTrajectory(
                session_id=archive.episode_id,
                trajectory_id=f"role:{trajectory.actor_id}",
                agent=AtifAgent(
                    name=trajectory.policy.agent_id,
                    version="1.0.0",
                    model_name=trajectory.policy.model,
                    tool_definitions=tool_definitions,
                    extra={
                        "actor_id": trajectory.actor_id,
                        "role": trajectory.role,
                        "policy_id": trajectory.policy.policy_id,
                        "provider": trajectory.policy.provider,
                        "context_id": trajectory.policy.context_id,
                        "trainable": trajectory.policy.trainable,
                    },
                ),
                steps=steps,
                final_metrics=_atif_final_metrics(steps),
                extra={
                    "episode_id": archive.episode_id,
                    "release_id": archive.release_id,
                    "actor_id": trajectory.actor_id,
                    "role": trajectory.role,
                },
            )
        )
    reward_mapping = reward.to_mapping() if reward is not None else None
    return AtifTrajectory(
        session_id=archive.episode_id,
        trajectory_id=f"arena:{archive.episode_id}",
        agent=AtifAgent(
            name="narrative-multi-agent-arena",
            version="1.0.0",
            tool_definitions=tool_definitions,
            extra={
                "scheduler": archive.config.scheduler_version,
                "reward_version": archive.config.reward_version,
            },
        ),
        steps=root_steps,
        notes=(
            "Global AEC order is shown in the root trace. Each embedded trajectory "
            "contains only the actions and observations of one isolated role."
        ),
        final_metrics=_atif_final_metrics(root_steps),
        extra={
            "episode_id": archive.episode_id,
            "release_id": archive.release_id,
            "episode_seed": archive.episode_seed,
            "termination_reason": archive.termination_reason,
            "terminal_state_hash": archive.terminal_state_hash,
            "trace_head": archive.trace_head,
            "violations": list(archive.violations),
            "reward": reward_mapping,
            "actor_ids": sorted(actor_by_id),
        },
        subagent_trajectories=embedded,
    )


def write_atif_trajectory(
    archive: EpisodeArchive,
    destination: str | Path,
    *,
    reward: RewardReport | None = None,
    instruction: str = "Run one complete role-isolated narrative-game episode.",
) -> Path:
    """Write the Harbor Viewer contract at ``agent/trajectory.json``."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    trajectory = episode_to_atif(archive, reward=reward, instruction=instruction)
    destination.write_text(
        json.dumps(trajectory.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


class ArenaModelDecision(BaseModel):
    """Structured provider response for one authorized arena turn."""

    reasoning_summary: str = Field(min_length=1, max_length=2000)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any]


def _bool_value(value: bool | str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"unsupported boolean value: {value!r}")


def _role_models(value: str | Mapping[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    parsed = json.loads(value) if isinstance(value, str) else dict(value)
    if not isinstance(parsed, dict):
        raise ValueError("role_models_json must name a JSON object")
    return {str(key): str(item) for key, item in parsed.items()}


class HarborModelArenaPolicy:
    """One stateful Harbor LLM session permanently bound to one arena role."""

    def __init__(
        self,
        *,
        identity: PolicyIdentity,
        role: str,
        instruction: str,
        llm: BaseLLM,
        logging_root: Path,
        use_responses_api: bool,
    ) -> None:
        self.identity = identity
        self.role = role
        self._llm = llm
        self._history: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"You are the isolated {role} policy in a facilitated narrative game. "
                    "Use only facts, evidence, state, and dialogue in your authorized "
                    "observation. Never claim access to another role's private material. "
                    "Choose exactly one legal tool each turn. Preserve uncertainty, distinguish "
                    "observation from inference, and keep play engaging and evidence-grounded. "
                    "Return a concise user-visible reasoning_summary, not private chain-of-thought. "
                    f"The Harbor task instruction is: {instruction}"
                ),
            }
        ]
        self._logging_root = logging_root
        self._logging_root.mkdir(parents=True, exist_ok=True)
        self._use_responses_api = use_responses_api
        self._previous_response_id: str | None = None
        self._last_dialogue_sequence = -1
        self._prior_action_count = 0
        self._turn = 0

    async def decide(self, observation: Mapping[str, Any]) -> PolicyDecision:
        self._turn += 1
        legal_tools = [str(item) for item in observation["legal_tools"]]
        include_static = self._turn == 1 or (
            self._use_responses_api and self._previous_response_id is None
        )
        prompt = canonical_json(
            {
                "authorized_observation": _model_observation(
                    observation,
                    include_static=include_static,
                    dialogue_after=self._last_dialogue_sequence,
                    actions_after=self._prior_action_count,
                ),
                "legal_tools": legal_tools,
                "argument_contracts": {
                    tool: _TOOL_ARGUMENT_CONTRACTS.get(tool, {}) for tool in legal_tools
                },
                "output_contract": {
                    "reasoning_summary": "concise decision rationale",
                    "tool": "one exact legal_tools value",
                    "arguments": "object matching that tool's argument contract",
                },
                "policy_guidance": _policy_guidance(self.role, observation),
            }
        ).decode("utf-8")
        call_kwargs: dict[str, Any] = (
            {"max_output_tokens": 1600}
            if self._use_responses_api
            else {"max_tokens": 1600}
        )
        if self._use_responses_api and self._previous_response_id is not None:
            call_kwargs["previous_response_id"] = self._previous_response_id
        response = await self._llm.call(
            prompt,
            message_history=self._history,
            response_format=ArenaModelDecision,
            logging_path=self._logging_root / f"turn-{self._turn:03d}.json",
            **call_kwargs,
        )
        parsed = ArenaModelDecision.model_validate_json(response.content)
        if self._use_responses_api:
            self._previous_response_id = response.response_id
        else:
            self._history.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response.content},
                ]
            )
        dialogue = observation.get("dialogue", [])
        self._last_dialogue_sequence = max(
            [self._last_dialogue_sequence]
            + [int(item.get("sequence", -1)) for item in dialogue]
        )
        self._prior_action_count = len(observation.get("own_prior_actions", []))
        call_id = "model-" + digest_json(
            {
                "context_id": self.identity.context_id,
                "turn": self._turn,
                "response": response.content,
            }
        ).split(":", 1)[1][:24]
        receipt = None
        if response.prompt_token_ids is not None and response.completion_token_ids is not None:
            logprobs = tuple(response.logprobs or ())
            if logprobs and len(logprobs) != len(response.completion_token_ids):
                logprobs = ()
            receipt = PolicyCallReceipt(
                response.response_id or call_id,
                tuple(response.prompt_token_ids),
                tuple(response.completion_token_ids),
                tuple(
                    [0] * len(response.prompt_token_ids)
                    + [1] * len(response.completion_token_ids)
                ),
                logprobs,
            )
        if self.identity.trainable and receipt is None:
            raise RuntimeError(
                f"trainable policy {self.identity.policy_id} lacks provider token IDs"
            )
        usage = None
        if response.usage is not None:
            usage = PolicyCallUsage(
                int(response.usage.prompt_tokens),
                int(response.usage.completion_tokens),
                int(response.usage.cache_tokens),
                float(response.usage.cost_usd),
                response.model_name or self.identity.model,
                response.response_id,
            )
        return PolicyDecision(
            ToolCall(call_id, parsed.tool, parsed.arguments),
            receipt,
            usage,
            parsed.reasoning_summary.strip(),
        )


class HarborMultiAgentArenaAgent(BaseAgent):
    """Concrete Harbor agent running one isolated model context per game role."""

    SUPPORTS_ATIF = True

    def __init__(
        self,
        *args,
        player_model_name: str | None = None,
        host_model_name: str | None = None,
        role_models_json: str | Mapping[str, str] | None = None,
        episode_seed: int | str = 0,
        reasoning_effort: str = "high",
        use_responses_api: bool | str = True,
        trainable: bool | str = False,
        api_base: str | None = None,
        temperature: float | str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        default_model = player_model_name or self.model_name or "openai/gpt-5.6-sol"
        self._player_model_name = default_model
        self._host_model_name = host_model_name or default_model
        self._role_models = _role_models(role_models_json)
        self._episode_seed = int(episode_seed)
        self._reasoning_effort = reasoning_effort
        self._use_responses_api = _bool_value(use_responses_api)
        self._trainable = _bool_value(trainable)
        self._api_base = api_base
        self._temperature = float(temperature) if temperature is not None else None

    @staticmethod
    def name() -> str:
        return "narrative-multi-agent-arena"

    def version(self) -> str:
        return "1.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        result = await environment.exec("test -f /opt/narrative/release.zip")
        if result.return_code != 0:
            raise RuntimeError("Harbor task does not contain a frozen Game Release")

    def _model_for_role(self, role: str) -> str:
        return self._role_models.get(
            role,
            self._host_model_name if role == "host" else self._player_model_name,
        )

    def _identity(self, release_id: str, role: str) -> PolicyIdentity:
        model = self._model_for_role(role)
        material = {
            "release_id": release_id,
            "episode_seed": self._episode_seed,
            "role": role,
            "model": model,
        }
        suffix = digest_json(material).split(":", 1)[1][:20]
        provider = model.split("/", 1)[0] if "/" in model else "litellm"
        return PolicyIdentity(
            f"policy-{suffix}",
            provider,
            model,
            f"harbor-agent-{role}",
            f"harbor-context-{suffix}",
            self._trainable,
        )

    def trial_lineup(
        self,
        instruction: str,
        release_id: str,
        seat_ids: tuple[str, ...],
    ) -> PolicyLineup:
        del instruction
        return PolicyLineup(
            tuple(
                SeatAssignment(seat_id, self._identity(release_id, f"seat:{seat_id}"))
                for seat_id in sorted(seat_ids)
            ),
            self._identity(release_id, "host"),
        )

    def trial_seed(self, instruction: str, release_id: str) -> int:
        del instruction, release_id
        return self._episode_seed

    def _create_llm(self, identity: PolicyIdentity) -> BaseLLM:
        return LiteLLM(
            identity.model,
            temperature=self._temperature,
            api_base=self._api_base,
            session_id=identity.context_id,
            collect_rollout_details=identity.trainable,
            reasoning_effort=self._reasoning_effort,
            use_responses_api=self._use_responses_api,
        )

    async def build_trial_policies(
        self,
        *,
        instruction: str,
        release_id: str,
        episode_seed: int,
        lineup: PolicyLineup,
    ) -> Mapping[str, AsyncArenaPolicy]:
        del release_id, episode_seed
        policies: dict[str, AsyncArenaPolicy] = {}
        for assignment in lineup.seats:
            actor_id = f"seat:{assignment.seat_id}:{assignment.policy.policy_id}"
            policies[actor_id] = HarborModelArenaPolicy(
                identity=assignment.policy,
                role=f"seat:{assignment.seat_id}",
                instruction=instruction,
                llm=self._create_llm(assignment.policy),
                logging_root=self.logs_dir / "provider" / assignment.seat_id,
                use_responses_api=self._use_responses_api,
            )
        actor_id = f"host:{lineup.host.policy_id}"
        policies[actor_id] = HarborModelArenaPolicy(
            identity=lineup.host,
            role="host",
            instruction=instruction,
            llm=self._create_llm(lineup.host),
            logging_root=self.logs_dir / "provider" / "host",
            use_responses_api=self._use_responses_api,
        )
        return policies

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="narrative-harbor-") as temporary:
            temporary_root = Path(temporary)
            release_path = temporary_root / "release.zip"
            config_path = temporary_root / "environment.json"
            await environment.download_file("/opt/narrative/release.zip", release_path)
            await environment.download_file("/opt/narrative/environment.json", config_path)
            release = load_release(release_path.read_bytes())
            environment_config = json.loads(config_path.read_bytes())
            if environment_config["release_id"] != release.release_id:
                raise ValueError("Harbor environment names another Game Release")
            config = EpisodeConfig.from_mapping(environment_config["episode_config"])
            game = json.loads(release.file("trusted/game.json").data)
            seat_ids = tuple(str(item["id"]) for item in game["kernel"]["seats"])
            lineup = self.trial_lineup(instruction, release.release_id, seat_ids)
            episode_seed = self.trial_seed(instruction, release.release_id)
            episode = MultiAgentEpisode.reset(
                release,
                episode_seed=episode_seed,
                lineup=lineup,
                config=config,
            )
            policies = await self.build_trial_policies(
                instruction=instruction,
                release_id=release.release_id,
                episode_seed=episode_seed,
                lineup=lineup,
            )
            archive = await AsyncMultiAgentArenaRunner().run(episode, policies)
            artifact_root = temporary_root / "artifacts"
            write_trial_artifacts(release, archive, artifact_root)
            await environment.upload_dir(artifact_root, "/logs/artifacts")
            report = evaluate_episode(release, archive)
            write_atif_trajectory(
                archive,
                self.logs_dir / "trajectory.json",
                reward=report,
                instruction=instruction,
            )
            rollout_details = []
            for trajectory in archive.trajectories:
                if not trajectory.policy.trainable:
                    continue
                receipts = [step.policy_receipt for step in trajectory.steps]
                if not receipts or any(item is None for item in receipts):
                    raise RuntimeError(
                        f"trainable trajectory lacks receipts: {trajectory.actor_id}"
                    )
                resolved = [item for item in receipts if item is not None]
                rollout_details.append(
                    {
                        "prompt_token_ids": [list(item.input_token_ids) for item in resolved],
                        "completion_token_ids": [
                            list(item.output_token_ids) for item in resolved
                        ],
                        "logprobs": [list(item.logprobs) for item in resolved],
                        "extra": {
                            "actor_id": [trajectory.actor_id for _ in resolved],
                            "role": [trajectory.role for _ in resolved],
                            "episode_id": [archive.episode_id for _ in resolved],
                        },
                    }
                )
            context.rollout_details = rollout_details or None
            usages = [
                step.policy_usage
                for trajectory in archive.trajectories
                for step in trajectory.steps
                if step.policy_usage is not None
            ]
            context.n_input_tokens = sum(item.prompt_tokens for item in usages)
            context.n_output_tokens = sum(item.completion_tokens for item in usages)
            context.n_cache_tokens = sum(item.cached_tokens for item in usages)
            context.cost_usd = sum(item.cost_usd for item in usages)
            context.metadata = {
                "episode_id": archive.episode_id,
                "release_id": archive.release_id,
                "reward": report.to_mapping(),
                "trajectory_actor_ids": [item.actor_id for item in archive.trajectories],
                "role_models": {
                    item.role: item.policy.model for item in archive.trajectories
                },
                "trainable": self._trainable,
            }
