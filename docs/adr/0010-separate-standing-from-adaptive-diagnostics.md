# Separate frozen Standing samples from adaptive diagnostic scheduling

- Status: accepted
- Date: 2026-08-08

## Context

Full fixed-panel Episodes and their independent analyses are expensive. Running
every possible assignment, contrast, and replication wastes time and model
budget, while selecting runs after seeing outcomes can bias the measured
Difficulty Profile, leak sealed material, or change the population represented
by Standing. Semantic estimates of novelty and causal discrimination also
require agentic judgment that a static scheduler cannot derive reliably.

## Decision

One precommitted Standing Sampling Plan fixes the estimand, assignment matrix,
strata, seeds, quotas, maximum sample size, invalid-replacement chains, and stop
rule. Only its assignments enter the current Difficulty Profile and Standing.
Outcome-adaptive work lives in a separate Diagnostic Sampling Queue and may
inform only analysis or a newly frozen experiment series.

An isolated Scheduling Analyst proposes semantic information value from a
bounded evidence snapshot. A deterministic Scheduling Transition applies a
frozen lexicographic Priority Vector: mandatory validity and coverage debt,
target-boundary proximity, causal discrimination, uncertainty reduction,
promoted-failure regression risk, structural novelty, then cost and latency.
Lower tiers cannot compensate for higher-tier deficits.

Every action names the claim it can decide and follows the cheapest sufficient
Evidence Cascade. Complete Evidence Work Packages preserve mandatory sweep,
corroboration, matched-control, verification, and receipt obligations. Protected
Budget Envelopes separate Standing, invalid replacements, diagnostics,
counterfactuals, regression, sealed checks, and authorized contingency.
Assignment identities never change for availability or cost.

Novelty is coverage over frozen structural axes, not text variation. Diagnostic
claims predeclare resolved, refuted, invalidated, saturated, and unresolved stop
states. A versioned Cost Model forecasts complete-package calls, tokens, spend,
latency, concurrency, and retry burden; observations calibrate only later
versions. Scheduling Receipts preserve every alternative, priority, reason,
budget, cost, and next action.

Sealed Cohorts appear only as opaque Scheduling Handles and run only at their
predeclared promotion gates. The scheduler cannot inspect cases, react to
interim outcomes, or accept a partial cohort.

## Consequences

Adaptive work can concentrate expense where it most improves diagnosis without
turning discovery into a biased Standing sample. Hard coverage and integrity
obligations remain protected, and operators can reconstruct why each expensive
action ran. This requires separate reporting of primary and diagnostic evidence
and may leave a result honestly insufficient when its frozen budget or
replacement chain is exhausted.

## Evidence

- `docs/research/agent-failure-scaling.md` recommends a cost cascade and sampling
  by novelty, disagreement, uncertainty, boundary proximity, and regression
  risk while preserving independent evaluation axes.
- The Difficulty Profile domain model defines exact Uncertainty Envelopes,
  calibrated Target Contracts, and matched comparisons.
- The Stage 11 efficiency controls already preserve bounded budgets, explicit
  stop state, invalidation, and the next transition.
- tau-bench motivates repeated-trial reliability:
  <https://arxiv.org/abs/2406.12045>.
- AgentBoard motivates progress- and subskill-level evaluation rather than
  terminal outcomes alone: <https://arxiv.org/abs/2401.13178>.
- Inspect metrics preserve explicit grouped reductions:
  <https://inspect.aisi.org.uk/metrics.html>.
