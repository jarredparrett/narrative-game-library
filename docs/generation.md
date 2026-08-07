# Agentic game generation

Version 0.19 adds a resumable path from a `CreativeBrief` to a measured game.
The path is human-triggered and can run without human approval gates; human
feedback remains optional first-order evidence after generation.

## Process

1. Freeze a `CreativeBrief`, `GenerationPlan`, quality Instrument, model-role
   assignments, budgets, stop policy, and optional `ArtifactPlan`.
2. Invoke the assigned creator through a typed `build` Task. The response must
   be one complete canonical `GameBlueprint`; invalid output is receipted and
   rejected rather than repaired silently.
3. Invoke the independently assigned reviewer through a typed `review` Task.
   The reviewer cannot share the builder's Authority, receipted agent identity,
   or context identity.
4. Apply an approved Proposal to the development Draft.
5. If the Blueprint plans realism-sensitive documents, bind one exact accepted
   Verismill `ArtifactSuite`. Every suite member keeps its own Experiment,
   rubric, approval, blind measurement, standing, and Artifact Attestation.
6. Compile the complete Candidate and run a fresh blind game-quality panel.
7. Translate quoted Findings into answer-safe Requirements, propose and review
   a child, rebuild affected artifacts, remeasure, and select under the frozen
   rule.
8. Stop when a Candidate passes or a frozen call, token, invalid-output, or
   round limit is reached.

`GenerationCoordinator.run()` performs that sequence. Every effect uses stable
idempotency keys, so `GenerationCoordinator.open(path).run(...)` resumes rather
than duplicating completed calls.

## Model replacement

`ModelRoleAssignment` freezes the provider, requested model, actual agent
identity, and isolated context identity for each base authority. A Plan has one
builder, one independent reviewer, and one or more judges, and it rejects reuse
of any Authority, agent identity, or context identity. Drivers are supplied by
the host application and may use different providers. Blind judge Authorities
are derived freshly for each round while retaining and verifying the Plan's
receipted agent, context, provider, and requested model.

Every `DriverOutput` used by generation must include non-negative token usage
as either `total_tokens` or both `input_tokens` and `output_tokens`. The
persisted `ModelReceipt` records provider, requested and resolved model, actual
agent and context identities, prompt, context, tool contract, exact inputs,
outputs, seed, evidence class, and usage.

## Artifact boundary

An `ArtifactSpecification` names the Resource, Verismill/Mattermill document
class, seed, output media type, canonical Proposition and Event references,
pins, canon, accessibility requirements, and permitted audiences. Before it can
enter an `ArtifactPlan`, `bind_artifact_specification(blueprint, spec)` derives
an Artifact Truth Binding over the exact pins/canon plus the referenced
Proposition meanings, truth assignments, and Event projections. Editing any of
those world facts or request values makes the Blueprint invalid until the
artifact intent is deliberately rebound and its suite is requalified.

`VerismillArtifactSuiteImporter` consumes only Verismill's public
`ArtifactSuite` surface. It imports a suite that was already forged, measured,
and attested; it never creates or revises an Experiment and never claims to
remeasure standing. It rejects an unverified or unattested suite, extra or
missing members, stale Blueprint truth bindings, mismatched
class/seed/pins/canon, unaccepted member standing, or a suite whose
qualification is not release-ready. The compiler replaces the editable
rich-text source with the accepted artifact bytes and preserves the member and
suite attestations. Artifact-visible claims trace through exact request pins
and fact references. `VerismillArtifactSuiteMaterializer` remains a compatibility
name for the same import-only adapter.

The game score and artifact realism scores are never averaged. A game can be
good while an artifact remains unaccepted, but that combination cannot compile
through the release-ready generation path.

## Monitoring and replay

The Workspace journals and object store are authoritative. The coordinator
also rewrites two disposable projections after every transition:

- `generation-status.json` for tools and dashboards;
- `generation-status.md` for people.

They report the current phase, development Draft, selected Candidate, active
target, used and remaining model calls/tokens/rounds, artifact completion,
stop reason, journal heads, and legal next actions. Deleting either projection
loses no experiment state; opening or advancing the coordinator recreates it.

Use `Experiment.verify()` to validate the Workspace, climb, standing, and
efficiency hash chains. Export the Workspace archive when a portable rerun or
audit bundle is required.

## Evidence limits

A passing generated Candidate is development evidence, not automatically
public-release standing. Machine-qualified standing still requires the
independent corroboration defined by the frozen Instrument and release policy.
Human-play standing remains a distinct optional evidence class and can never be
inferred from model simulation or document realism.
