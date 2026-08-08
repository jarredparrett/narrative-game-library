# Operator Evidence Monitor v1

This is the implementation-ready information and trust contract for monitoring
a running Generation Campaign and Difficulty Experiment. The Monitor is a
rebuildable Evidence Projection, not canonical state, a scheduler, or a control
plane.

The retained UI prototype is branch `codex/operator-monitor-prototype` at
commit `fbc395e`. It compares three layouts over one projection fixture and
demonstrates current, stale, incomplete, and corrupt states.

## Design decision

The Monitor is one read-only surface with three complementary views:

1. **Overview — Evidence Spine.** Default landing view. It answers whether the
   Projection is trustworthy, what Evidence Work Package is current, what is
   next, what claim each package can decide, what budget remains, and where the
   evidence lineage ends.
2. **Coverage — Coverage Plot.** Dedicated statistical view. It presents every
   required, valid, invalid, missing, and replacement assignment; target bands;
   Uncertainty Envelopes; Budget Envelopes; and the Scheduling Receipt that
   selected the next work.
3. **Incident — Incident Workbench.** One-Incident diagnostic view. It presents
   the Incident Brief, Trace Lens, independent Attributions and disagreement,
   causal candidates, counterevidence, next discriminating probe, and exact
   lineage.

The views share one immutable projection object and exact Evidence Object
references. They disagree about hierarchy, not facts. Overview never attempts
to fit the full coverage matrix or causal bench into its primary scan path.

## One job

Within ten seconds, an operator should be able to answer:

1. Can this Projection be trusted for the claim shown?
2. What complete Evidence Work Package is executing now, and what claim can it
   decide?
3. What work is legally eligible next, and why did the Scheduling Transition
   choose it?
4. What coverage, uncertainty, or budget debt prevents a decision?
5. Which Incidents and causal probes are active?
6. Which Claim Manifest and receipts support every visible conclusion?

The Monitor does not answer “what should I approve?” or provide a button that
can change evidence.

## Projection identity

Every rendered view exposes these fields before derived content:

| Field | Contract |
|---|---|
| `projection_schema` | Independently versioned Monitor projection schema. |
| `projection_ref` | Content hash of canonical projection bytes. |
| `workspace_id` | Exact operator-owned Workspace. |
| `checkpoint_ref` | Coherent Workspace Checkpoint used for derivation. |
| `derivation_contract_ref` | Exact deterministic projection builder and schema identities. |
| `authorized_journal_heads` | Heads bound by the Checkpoint, never a loose set of latest files. |
| `freshness` | `current`, `stale`, or `invalid` under Projection Freshness. |
| `reproducibility_status` | `complete`, `degraded`, `externally-dependent`, `unsupported`, or `corrupt`. |
| `verification_receipt_ref` | Offline verification result and exact failures. |
| `claim_manifest_refs` | Claims whose status appears in the Projection. |

A render path, wall-clock timestamp, browser session, or polling sequence is not
identity. Rebuilding the same projection from the same Checkpoint and derivation
contract must produce byte-identical canonical projection data.

## Trust header

Every view begins with a non-dismissible trust header above campaign content.
It states:

- Projection Freshness and Reproducibility Status;
- projection and authorized Workspace Checkpoints;
- verified Journal head count or exact verification failure;
- the Claim Manifest status applicable to the page; and
- `read only — no transition authority`.

Color, icon, or animation never carries the status alone. The exact state is
available to assistive technology and remains visible while scrolling.

### State behavior

Freshness and evidence completeness are separate axes.

| State | Meaning | Required presentation |
|---|---|---|
| Current and complete | Projection Checkpoint is the authorized head and the displayed Claim Manifest closure is complete | Show conclusions with exact manifest and receipt links. Still show that the Monitor has no authority. |
| Current but incomplete | Checkpoint is current, but required assignments, replacements, receipts, or evidence are missing | Keep partial evidence visible; show denominators, exact debt, stop state, and eligible next work. Standing and selection remain `indeterminate`. |
| Stale | A source Journal advanced beyond the Projection Checkpoint | Preserve the old view as explicitly historical context. Show both Checkpoints and the advanced Journals. Never describe the view as current or silently mix new objects into it. |
| Invalid/corrupt | Derivation, hash chain, object closure, schema, or Claim Manifest verification failed | Remove derived decision content. Show the failure receipt, affected claim, last independently verifiable Checkpoint when known, and direction to the authoritative Workspace verifier. |

An incomplete Projection may be current. A stale Projection may have been
complete at its own Checkpoint. `corrupt` is a Reproducibility Status and maps to
`invalid` Projection Freshness; it is not a stronger shade of stale.

## Live means checkpointed

“Live” means the page may receive newly verified Projection snapshots as
Workspace Checkpoints advance. It never streams unverified Journal fragments
into authoritative-looking state.

- A new snapshot replaces the old one atomically and names its Checkpoint.
- Logical order follows Journal sequence and causal references, not arrival or
  browser time.
- In-flight work appears only after an authorized Scheduling Transition.
- Progress is derived from receipted obligations such as `4/5 spans expanded`
  or `21/24 valid assignments`; it is never an invented percentage, spinner, or
  model self-report.
- Provider, process, or agent completion is not Episode validity. Verification
  and Analysis Receipt status remain explicit.
- If connectivity stops, the last snapshot becomes historical rather than
  pretending to remain live.

## Overview contract

The Evidence Spine orders completed, active, queued, blocked, and ineligible
stages by causal evidence order:

```text
Workspace Checkpoint
  -> standing and diagnostic Episodes
  -> Discovery Sweeps and Incidents
  -> independent Attributions
  -> Counterfactual Packages
  -> Difficulty Profile and target comparison
  -> Challenge or framework Admission
  -> Independent Review
  -> authorized Transition
```

The Spine ends with a visible authority boundary. The Monitor may show an
authorized transition recorded in a Scheduling Receipt; it may not invoke it.

The default view contains:

- current phase and Diagnostic Stop State;
- current Evidence Work Package, claim, minimum sufficient evidence, observed
  completion, forecast cost, Budget Envelope, and receipt;
- next eligible packages in Scheduling Priority order with selection and
  deferral reasons;
- summary required/valid/invalid/missing assignment counts;
- protected Budget Envelopes and reservation state;
- target intervals and status, never an overall difficulty scalar;
- active Incident count and unresolved Attribution disagreement;
- recent Scheduling, verification, analysis, and invalidation receipts;
- Claim Manifest closure and freshness; and
- opaque Sealed Scheduling Handles.

## Coverage contract

The Coverage view preserves population and uncertainty honestly:

- Standing and diagnostic populations are visibly separate.
- Every Coverage Cell reports required, valid, invalid, missing, replacement,
  and correlation-group counts.
- Invalid Episodes remain visible but never count as agent failures or completed
  assignments.
- Replacement Chains show consumed and remaining assignments without hiding the
  invalid attempt.
- Binary metrics show point value and 95% Wilson interval; continuous/count
  metrics show median, interquartile range, and eligible stratified bootstrap
  interval. Insufficient samples state `insufficient` rather than drawing a
  precise band.
- Target bands come from the pinned Difficulty Target Contract. Candidate data
  never redraws its own target.
- Every displayed comparison names exact Panel, Instrument, Release, sampling
  plan, match grade, and completeness.
- Matched-control behavior and non-target gate movement remain adjacent to the
  targeted dimension.

The Scheduling board shows the frozen Priority Vector lexicographically. It
does not collapse coverage debt, causal discrimination, uncertainty, risk,
novelty, and cost into one utility number.

## Incident contract

The Incident Workbench uses the existing analysis vocabulary:

- Incident Brief for expected-versus-observed facts and status;
- Trace Lens for cited spans, Verification Status, and context;
- two separately labeled Causal Hypothesis Sets;
- Attribution Agreement and disagreement without averaging;
- evidence, counterevidence, alternatives, confidence bands, and owning-layer
  status;
- Counterfactual Plan, fixed invariants, next discriminating Evidence Work
  Package, and protected budget; and
- exact Incident-to-claim lineage.

An active Incident is analysis, not an alert that authorizes a repair. Proposed,
experimental, promoted, repair-required, refuted, and unresolved states remain
distinct. Actor blame language is excluded.

## Budget and scheduling contract

Budget Envelopes are shown independently for Standing, invalid replacements,
diagnostics, counterfactuals, promoted-class regression, sealed checks, and
authorized contingency. Each reports reserved, actual, forecast, remaining,
and exhausted amounts in its declared units.

The current and next work views bind one Scheduling Receipt containing:

- evidence snapshot and Scheduling Analysis;
- Cost Model and forecast interval;
- every eligible alternative and Priority Vector;
- selected, deferred, and rejected packages with reasons;
- protected and remaining Budget Envelopes;
- resulting Diagnostic Stop State; and
- exact next eligible actions.

The Monitor cannot reorder the queue, substitute an assignment, borrow from a
protected envelope, launch a Package, or recalibrate the Cost Model.

## Claim and lineage contract

Every conclusion—“current work,” “coverage debt,” “supported Incident,”
“target-band,” “invalid Episode,” or “next action”—links to one Claim Manifest
or Scheduling Receipt. The operator can navigate to:

- exact Evidence Object identity and schema;
- typed Lineage Edges;
- authorization Journal event and Checkpoint;
- verification result;
- upstream and downstream evidence closure; and
- preserved refuting, invalid, rejected, or incomplete objects.

Navigation is inspection only. Copying a reference or opening a Trace Lens does
not create an Evidence Event.

## Sealed boundary

Only the following Sealed Scheduling Handle fields may appear:

- opaque handle identity;
- declared cost or reserved Budget Envelope;
- eligibility and consumption state;
- predeclared promotion gate; and
- final aggregate decision receipt when authorized for that view.

The Monitor never exposes membership, case count when it could identify cases,
case content, seeds, source material, oracle, interim progress, per-case result,
or case-level finding. It cannot reorder, stop, retry, or expand a Sealed Cohort.

## Inspection surface, not control plane

Allowed affordances are limited to:

- navigate among Overview, Coverage, and Incident views;
- filter or group already-projected evidence without changing canonical order;
- inspect an exact Evidence Object, receipt, Claim Manifest, or Lineage Edge;
- expand a permitted Trace Lens; and
- copy a stable content reference.

The Monitor has no `approve`, `reject`, `run`, `retry`, `rebuild`, `resume`,
`cancel`, `promote`, `select`, `transition`, `reallocate`, `edit`, or `delete`
command. If a future product adds an operator control plane, it is a separate
authority surface that submits typed commands and independently refreshes this
Monitor after their authorized effects enter a Journal.

## Update and failure behavior

Projection rebuilding follows these rules:

1. Verify all source Journal heads and referenced object closure.
2. Construct against one coherent Workspace Checkpoint.
3. Derive the complete canonical projection object without network access.
4. Verify every visible claim reference and sealed-field policy.
5. Atomically publish JSON for tools and accessible HTML/Markdown for people.
6. Compare the bound Checkpoint with the current authorized head before serving
   `current`.

If rebuilding fails, retain the previous Projection as historical evidence and
publish a separate failure receipt. Never partially overwrite a current
Projection or infer status from file modification time.

## Prototype outcome

The prototype resolved the hierarchy this way:

- **Evidence Spine won the default overview** because it keeps trust, current
  work, next work, and authority boundary in one scan path.
- **Coverage Plot remains a dedicated view** because assignment debt and
  intervals need table and band density that would overwhelm the overview.
- **Incident Workbench remains a detail view** because competing Attributions
  and causal probes need more space than an Incident card.

Visual QA also established two fail-closed behaviors:

- stale warnings span the full layout rather than displacing or clipping the
  historical view; and
- corrupt state removes derived decision content instead of merely tinting it.

## Required implementation fixtures

The implementation handoff must include capability tests for:

1. current complete Projection with verified Claim Manifest closure;
2. current incomplete Projection with exact denominators and indeterminate
   Standing;
3. stale Projection showing both Checkpoints without mixed evidence;
4. corrupt Projection suppressing derived conclusions;
5. current and next Evidence Work Packages tied to one Scheduling Receipt;
6. protected Budget Envelopes with no forbidden reallocation;
7. valid, invalid, missing, and replacement coverage kept separate;
8. insufficient uncertainty refusing a precise target conclusion;
9. active Incident with isolated Attribution disagreement and next probe;
10. every conclusion resolving to a Claim Manifest or Scheduling Receipt;
11. sealed projection containing only allowlisted opaque fields;
12. absence of every mutation or transition command;
13. deterministic offline rebuild and byte identity across processes;
14. accessible keyboard navigation, visible focus, status text independent of
    color, reduced-motion support, and responsive geometry; and
15. deletion and regeneration of the Projection without loss of canonical
    evidence or change to a claim.

The implementation may extend existing `generation-status`, `active-experiment`,
and `current-standing` derivations, but none of those current projections alone
satisfies this contract: they do not yet bind the complete trust, coverage,
uncertainty, Incident, scheduling, claim, and sealed-handle view required here.
