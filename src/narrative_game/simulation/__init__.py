"""Deterministic multi-agent simulation environment and verification."""

from .environment import ArenaCredential, MultiAgentEpisode
from .experiment import EpisodeAssignment, RoleRotationPlan, plan_role_rotated_episodes
from .model import (
    EpisodeArchive,
    EpisodeConfig,
    GateResult,
    PolicyCallReceipt,
    PolicyCallUsage,
    PolicyIdentity,
    PolicyLineup,
    PolicyTrajectory,
    RewardReport,
    SeatAssignment,
    ToolCall,
    ToolResult,
)
from .verification import evaluate_episode, verify_episode
from .runner import (
    ArenaPolicy,
    AsyncArenaPolicy,
    AsyncMultiAgentArenaRunner,
    MultiAgentArenaRunner,
    PolicyDecision,
)

__all__ = [
    "ArenaCredential",
    "ArenaPolicy",
    "AsyncArenaPolicy",
    "AsyncMultiAgentArenaRunner",
    "EpisodeArchive",
    "EpisodeAssignment",
    "EpisodeConfig",
    "GateResult",
    "MultiAgentEpisode",
    "MultiAgentArenaRunner",
    "PolicyCallReceipt",
    "PolicyCallUsage",
    "PolicyDecision",
    "PolicyIdentity",
    "PolicyLineup",
    "PolicyTrajectory",
    "RewardReport",
    "RoleRotationPlan",
    "SeatAssignment",
    "ToolCall",
    "ToolResult",
    "evaluate_episode",
    "plan_role_rotated_episodes",
    "verify_episode",
]
