# Recursive generation may redesign its framework under sealed governance

- Status: accepted
- Date: 2026-08-08

## Context

Failure-driven generation must be able to do more than mutate a fixed scenario
template. Difficult or novel failures may expose a missing abstraction, tool,
adapter, algorithm, prompt strategy, domain model, or generation architecture.
Agents therefore need authority to research the problem and fundamentally alter
generation code. Giving those same agents authority over the cases and
instrument that judge their changes would turn recursion into self-grading and
make apparent improvement scientifically ambiguous.

## Decision

Each recursive campaign freezes a Generation Intent: the triggering Failure
Class, coverage gap, plateau, or research hypothesis; desired capability;
target Difficulty Profile; integrity constraints; comparison rule; stopping
rule; and resource budgets. The method remains open. Agents may conduct new
research and replace any part of the generative framework. Material research is
preserved in a Research Receipt, and material machinery changes become an
immutable Generative Framework Revision rather than an in-place edit.

Generated Challenge Cases must pass structural compilation, coherence,
authorization, reachability, two independent agentic solution demonstrations,
oracle validation, an isolated leakage and shortcut review, a matched
non-manifesting control, and difficulty and novelty measurement. An unresolved
hard feasibility or leakage finding quarantines the case outside every
evaluation suite.

Development, generated-challenge, and sealed-standing Suite Bindings are
one-way and immutable. A development or generated case can never become sealed.
A distinct Sealed Suite Curator creates withheld cases from hidden seeds or
source materials. Each framework-promotion attempt consumes a fresh sealed
cohort and receives only its frozen aggregate decision receipt. Exposure retires
a sealed case to development use permanently.

A Framework Target Contract compares a Revision with its parent. Feasibility,
solvability, authorization, leakage resistance, artifact realism, and narrative
quality are non-compensable integrity gates. Improvement must address the named
coverage target while improving accepted-case yield or efficiency, structural
diversity, and target-band difficulty without crossing the solvability band.
The agents that research, design, or implement a Revision cannot review it.
Only a deterministic, append-only Framework Transition installs an independently
accepted content-addressed Revision for future campaigns.

## Consequences

The outer loop can recursively expand its own capabilities rather than merely
tune parameters. Research and architectural change remain traceable, failed
approaches remain reproducible, and experiments can resume after bounded stops.
The additional independent solver, adversarial review, curator, and single-use
cohort work is intentional: generated volume establishes neither validity nor
standing, and a sealed result cannot become a reusable optimization gradient.

## Evidence

- `docs/research/agent-failure-scaling.md` defines the three-suite scaling model
  and the initial Challenge Case contract.
- ADR 0008 limits recursive Failure Atlas authority and preserves historical
  experiment identity.
- Anthropic's Bloom describes researcher-specified behaviors and generated
  evaluation suites: <https://www.anthropic.com/research/bloom>.
- METR's Task Standard motivates portable, versioned evaluation tasks:
  <https://metr.org/blog/2024-02-29-metr-task-standard/>.
- PlanBench demonstrates formally modeled, automatically validated generated
  planning variants: <https://arxiv.org/abs/2206.10498>.
- Inspect preserves complete evaluation logs for reproducible offline analysis:
  <https://inspect.aisi.org.uk/eval-logs.html>.
