# Frozen Analysis Instrument v1

This is the normative, implementation-ready definition of the first Analysis
Instrument for Facilitated Investigation Episodes. It instantiates the authority
and evidence boundaries decided by the agentic difficulty map. It specifies an
analysis instrument, not the runtime that will execute it.

The retained throwaway prototype is branch `codex/analysis-instrument-prototype`
at commit `95a8d84`. Its nine interactive cases established that this contract
can mechanically reject the intended contamination and independence failures.

## Identity and composition

The Instrument Definition is content-addressed over all of the following:

- schema `analysis-instrument.1` and Instrument version `1.0.0`;
- requested model roster and exact sampling settings;
- global and authority Prompt Contract bytes;
- Evidence View allow and deny contracts;
- analysis tool contract;
- structured output schemas;
- retry and partial-completion rules;
- principal-conflict graph;
- Published Failure Atlas reference;
- deterministic eligibility rules and fixture identities.

An Instrument Application freezes the provider-resolved model identity and
principal/context identity for every assignment. If a requested model resolves
differently, the result is a different Application. It cannot enter an exact
matched comparison with the earlier Application.

## Model roster

| Model slot | Provider and endpoint | Requested model | Reasoning | Output limit | Sampling |
|---|---|---|---|---:|---|
| `deep` | OpenAI Responses | `gpt-5.6-sol` | `high` | 12,000 tokens | omit temperature, top-p, and unsupported seed |
| `diverse` | OpenAI Responses | `gpt-5.6-terra` | `high` | 10,000 tokens | omit temperature, top-p, and unsupported seed |

Omission is a frozen setting, not permission to add a parameter later. Every
Analysis Receipt records requested and resolved model, endpoint, reasoning
effort, all submitted sampling parameters, usage, and provider response ID.

Model diversity is recorded but is not principal independence. The two
Attribution Analysts use different model slots and separate principals,
contexts, prompts, inputs, and receipts. Any shared provider dependency remains
visible.

## Assignment roster

The six Analysis Authorities expand to twelve independently occupied
assignments. Incident Assembly is a sub-assignment of Incident Discoverer but
uses a sixth discovery principal that sees only frozen sweep outputs.

| Authority | Assignment | Model | Evidence View | Output |
|---|---|---|---|---|
| Incident Discoverer | outcome and progress sweep | diverse | discovery | Discovery Sweep |
| Incident Discoverer | knowledge and claim-support sweep | diverse | discovery | Discovery Sweep |
| Incident Discoverer | coordination and work-allocation sweep | diverse | discovery | Discovery Sweep |
| Incident Discoverer | host intervention and dependence sweep | diverse | discovery | Discovery Sweep |
| Incident Discoverer | runtime, authorization, and evaluator-integrity sweep | diverse | discovery | Discovery Sweep |
| Incident Discoverer | incident assembler | deep | frozen discovery outputs | Incident Assembly |
| Semantic Interpreter | semantic interpreter | deep | interpretation | Semantic Interpretation |
| Attribution Analyst | attribution A | deep | attribution | Causal Hypothesis Set |
| Attribution Analyst | attribution B | diverse | attribution | Causal Hypothesis Set |
| Atlas Curator | Atlas curator | deep | curation | Atlas Revision Proposal |
| Challenge Designer | Challenge designer | deep | challenge | Challenge Case Proposal |
| Independent Reviewer | independent reviewer | deep | review | Independent Review |

Every assignment uses a distinct principal and isolated context within one
Analysis Lineage. A separately requested targeted corroboration sweep receives a
fresh discovery principal and the bounded claim, not the first sweep rationale.

## Global prompt contract

The following text prefixes every authority prompt verbatim:

> You occupy exactly one named Analysis Authority. Use only the supplied
> Evidence View. Return only the named structured output. Every factual claim
> must cite supplied evidence. Preserve counterevidence, alternatives,
> confidence, omissions, and runtime limitations. Do not infer comparison side,
> desired outcome, hidden truth, or prior conclusions. Do not claim transition
> authority. Never provide or request private chain-of-thought; provide concise
> evidence-backed rationale fields only.

The remainder of a Prompt Contract is, in order: the exact authority instruction
below, serialized Evidence View manifest, tool contract, output schema, and
upstream receipt manifest. The hash covers the complete composed bytes.

## Authority prompt contracts

### Outcome and progress discovery

Traverse outcome, milestones, stalls, abandoned work, unsupported terminal
claims, and counterevidence across the complete Episode. Propose
expected-versus-observed gaps only. Do not assign cause or an Atlas class.

### Knowledge and claim-support discovery

Traverse inspection, disclosure, sharing, claim support, corroboration, and
evidence lineage across the complete Episode. Propose gaps only. Do not judge
hidden truth or cause.

### Coordination and work-allocation discovery

Traverse communication, handoffs, duplication, disagreement, work allocation,
and distinct Seat contributions. Preserve locally plausible actions and propose
system-level gaps without blame.

### Host intervention and dependence discovery

Traverse hints, interventions, synthesis, confession, fallback, recovery timing,
and counterfactual dependence on the host. State observed dependence without
assigning ownership.

### Runtime, authorization, and evaluator-integrity discovery

Traverse rejected tools, timeouts, malformed output, authorization, exposure,
verification gaps, and evaluator consistency. Separate runtime,
evidence-quality, and reported-outcome gaps without cause claims.

### Incident Assembly

Group frozen Signals only when they share one expected milestone, required
transition, terminal claim, or linked obligation and an overlapping window or
factual-graph edge. Preserve exclusions and disagreement. Do not invent,
suppress, classify, or attribute.

### Semantic Interpretation

Translate the frozen Incident into precise game-domain meaning: Actors, Phases,
public obligations, observed transitions, missing transitions, and consequence.
State what happened and what remains uncertain. Never state why.

### Causal Attribution

Produce a multi-label Causal Hypothesis Set across Actor, interaction, Seat,
host, game, runtime, provider, and evaluator layers. For every factor state its
causal role, evidence, counterevidence, alternatives, confidence band, and one
falsifiable counterfactual prediction. Do not assign blame or inspect another
Attribution.

### Atlas Curation

Propose an append-only Atlas revision with exact class definitions, inclusions,
exclusions, adjacent distinctions, counterexamples, evidence stage, detector or
rubric, fixtures, migrations, and unresolved evidence. Do not promote, edit
history, or inspect sealed contents.

### Challenge Design

Propose one answer-safe Challenge Case from the supplied promoted class and
Generation Intent. State the generating mutation, protected invariants, initial
state, legal actions, terminal requirements, oracle, expected manifestation,
matched control, target profile, and admission plan. Do not certify it.

### Independent Review

Return accept or reject for the exact frozen proposal. Evaluate every declared
gate and disagreement against cited evidence and receipts. Do not edit the
proposal, waive a failed gate, infer desired comparison side, or manufacture
missing evidence.

## Evidence Views

### Discovery

Allowed: Episode structure; anonymized participants; Phases and milestones;
verified actions; authorized observations; tool results; messages and
visibility; state transitions; supplied timing observations; terminal state;
derived outcome, integrity, and execution facts; verification coverage; the
assigned factual graphs; and frozen lens patterns.

Denied: canonical world truth, Proof Paths, comparison side, aggregate scores,
Failure Atlas labels, provider/model names, and every other analysis output.

The Incident Assembler receives only complete frozen Sweep outputs, their
Coverage, and targeted-sweep receipts. It does not regain the underlying broad
trace view by default.

### Interpretation

Adds the frozen Incident, public role/Phase/action definitions, Evidence and
authorization definitions, and canonical meanings of observed state
transitions. Canonical world truth, Proof Paths, comparison side, Atlas labels,
and causal Attributions remain denied.

### Attribution

Allowed only after discovery and interpretation freeze: the Incident,
Interpretation, canonical Episode evidence, canonical world truth, valid Proof
Paths, terminal requirements, role prompts, tool contracts, host policy,
runtime-error receipts, and anonymized policy occupancy.

Denied: comparison side, aggregate scores, Atlas labels, provider/model names,
and the other Attribution output.

### Curation

Allowed: reviewed Incident packages, both frozen Attributions and their
disagreement, supporting/refuting/unresolved evidence, counterexamples, current
Published Atlas, approved Research Receipts, and any required opaque sealed
non-regression receipt.

Denied: sealed cases/results, desired Standing outcome, and transition authority.

### Challenge design

Allowed: one promoted Failure Class, de-identified evidence, target Difficulty
Profile, Generation Intent, Development Suite Coverage Cells, and integrity
constraints.

Denied: sealed cases/results, desired Standing outcome, self-validation results,
and transition authority.

### Independent review

Allowed: the frozen proposal, complete underlying evidence, deterministic
verification, independent Attributions and disagreements, controls and
Counterfactuals, all receipts, principal-conflict result, and any required opaque
sealed receipt.

Denied: comparison side, desired Release outcome, proposal-edit capability,
gate-waiver capability, and missing-evidence fabrication.

## Tool contract

Analysis assignments receive only three read/submit capabilities:

1. `evidence.get(ref)` returns an object already admitted to that Evidence View;
2. `evidence.expand(span_ref, before, after)` expands a bounded neighborhood
   while preserving visibility and recording Sweep Coverage;
3. `analysis.submit(schema, value)` freezes one structured output attempt.

No assignment receives shell, network, repository, arbitrary filesystem,
provider-administration, transition, or unlogged messaging tools. Approved
Research Receipts are objects in the Curator view, not live web access.

## Structured output schemas

All outputs include `status`, exact upstream refs, cited span refs, and an
`analysis_receipt_ref`. Unknown fields are rejected in v1.

### Discovery Sweep v1

Required: status (`complete`, `partial`, `invalid`), lens, Sweep Coverage,
Signals, counterevidence, omissions, continuation cursor, receipt. Each Signal
requires expected constraint, observed gap, span refs, Verification Status,
Actors, Episode window, known-pattern or novel identity, alternatives, and
confidence band. Only `partial` may carry a continuation cursor; only `complete`
may emit an empty Signals list as a no-finding result.

### Incident Assembly v1

Required: status, included and excluded Signal refs, grouping obligation,
factual-graph connection, preserved disagreement, optional targeted-sweep
request, and receipt. Every included Signal must exist and be frozen.

### Semantic Interpretation v1

Required: status, Incident ref, domain statement, Actors, Phases, public
obligations, observed transitions, missing or uncertain transitions,
consequence, span refs, and receipt. Causal-layer fields are forbidden.

### Causal Hypothesis Set v1

Required: status, Incident ref, factors, interactions, alternatives, overall
uncertainty, and receipt. Every factor requires layer, factor, causal role
(`necessary`, `sufficient`, `contributing`, `amplifying`, `recovery`, or
`confounding`), evidence, counterevidence, confidence band, and falsifiable
counterfactual prediction.

### Atlas Revision Proposal v1

Required: status, parent Atlas ref, class changes, evidence refs, detector or
rubric, positive fixtures, non-manifesting controls, migration, unresolved
evidence, and receipt.

### Challenge Case Proposal v1

Required: status, Failure Class and Generation Intent refs, exact mutation,
protected invariants, initial state, legal actions, terminal requirements,
oracle, expected manifestation, non-manifesting control, target profile,
Admission plan, and receipt.

### Independent Review v1

Required: status, proposal ref, gate-by-gate results, disagreements, missing
evidence, decision (`accept` or `reject`), reasons, and receipt. An acceptance
with any failed or missing gate is schema-ineligible.

### Analysis Receipt v1

Required: Authority, assignment, principal, provider, requested and resolved
model, endpoint, reasoning effort, submitted sampling settings, Instrument,
Prompt Contract, input and Evidence View refs, Exposure Ledger, structured and
raw output refs, trace citations, alternatives, confidence, upstream receipts,
runtime status, errors, usage, principal-conflict result, and attempt number.

## Retry and completion policy

- At most two transport retries repeat identical request bytes and Evidence View.
- One schema-repair attempt may receive only deterministic validation diagnostics
  and the prior raw output.
- Every attempt, including malformed and failed attempts, has a receipt.
- Semantic retry, majority retry, and best-of-N selection are forbidden.
- Exhaustion returns `incomplete`; it never becomes a no-finding or rejection.
- Partial Sweeps retain a continuation cursor but cannot corroborate an Incident.
- A retry that changes model, prompt, view, tool, or upstream evidence is a new
  Instrument Application or analysis lineage, not a retry.

## Principal conflicts

Within one Analysis Lineage:

- no Episode Actor may occupy an analysis assignment over that Episode;
- five sweep principals and the assembler principal are distinct;
- Discoverer, Interpreter, attribution A, attribution B, Curator, Challenge
  Designer, validators, proposal contributors, and Reviewer obey the conflict
  graph established in the domain model;
- attribution A and B freeze without communication or cross-exposure;
- the Reviewer shares no principal with any contributor to the package.

The deterministic coordinator verifies these facts. Passing proves eligibility,
not semantic truth.

## Required eligibility fixtures

The implementation handoff must preserve the prototype's nine cases:

1. one complete reference lineage is eligible;
2. canonical truth leaked into a discovery view is rejected;
3. Reviewer/contributor principal reuse is rejected;
4. cross-exposure between Attribution passes is rejected;
5. a partial Sweep cannot claim no finding or corroboration;
6. semantic or best-of retry is rejected;
7. an incomplete Analysis Receipt is rejected;
8. a Reviewer that edits a proposal is rejected; and
9. an Episode Actor analyzing the same Episode is rejected.

The missing-rescue false pass and passing failed-handoff Episodes remain the
first semantic fixtures. They must produce complete receipts and preserve
disagreement; this specification does not preordain their causal conclusion.

## Version boundary

Changing a requested or resolved model policy, prompt byte, Evidence View,
tool, schema, retry rule, conflict edge, Atlas version, or eligibility fixture
creates a new Instrument Definition or Application as applicable. Historical
outputs and Difficulty Profiles remain pinned to their exact Instrument.
