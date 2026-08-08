# Persist agentic difficulty evidence as content-addressed lineage

- Status: accepted
- Date: 2026-08-08

## Context

Difficulty, causal attribution, Failure Atlas, challenge generation, scheduling,
and Standing claims cross many independent agent authorities and may be reviewed
long after their original providers or repository checkout disappear. A folder
of latest reports cannot prove which exact Releases, Episodes, prompts,
instruments, analyses, rejections, and transitions supported a claim. A single
workspace blob would be portable but would erase independent identity and make
incremental verification or deduplication impractical.

## Decision

### Authority model

All authoritative material is an immutable typed Evidence Object addressed by
the hash of its canonical bytes. Separate append-only hash-chained Journals
record lineage, operations and scheduling, climb and analysis, qualification,
and access and exposure. Events authorize and relate objects; they do not embed
mutable copies. Typed Lineage Edges preserve identity, evidentiary, derivation,
experimental, authority, version, suite, and selection relationships.

A Workspace Checkpoint pins the exact verified heads of every Journal. A Claim
Manifest binds one reportable claim to a Checkpoint, its complete transitive
object graph, schema identities, and required verifiers. Monitoring files,
indexes, reports, and current-standing views are rebuildable Evidence
Projections and declare the Checkpoint from which they were derived.

The minimum catalog retains all authority-boundary inputs and outputs, including
frozen contracts; assignments and canonical Episode Archives; prompts, model and
tool receipts, verification, and runtime outcomes; Evidence Views, Sweeps,
Signals, Incidents, hypotheses, Attributions, Counterfactuals, Profiles, Atlas
and Challenge objects, and Scheduling Receipts; plus Reviews, Transitions,
Selections, Standing Attestations, and Claim Manifests. Rejected, refuted,
invalid, and incomplete evidence is retained.

### User-space layout

The default Workspace lives beneath the operating system application-data root,
with precedence for an explicit path and then a dedicated configuration
override. A repository-local ignored Workspace is opt-in. The logical layout is:

```text
<user-data-root>/
  workspaces/<workspace-id>/
    workspace.json
    objects/sha256/<prefix>/<remainder>
    journals/
      lineage.jsonl
      operational.jsonl
      analysis.jsonl
      qualification.jsonl
      access.jsonl
    checkpoints/<checkpoint-ref>.json
    projections/
  exports/
  cache/
```

Credentials remain in a separate secret authority and never enter objects,
journals, exports, or projections. Paths are locators rather than identities.

### Portability and verification

A deterministic Workspace Archive carries a complete Workspace closure. A
deterministic Claim Capsule carries one Claim Manifest closure, required Journal
inclusion proofs, schemas, and verifier artifacts. Imports verify in quarantine,
deduplicate objects by hash, preserve source Journal identities, and append an
Import Receipt rather than splicing independent event histories.

Re-verification deterministically replays recorded evidence and is mandatory.
Re-execution through stochastic or retired providers is best-effort and is not
claimed as replay. Exact external bytes needed by a qualifying claim are sealed
into the graph; URLs, provider IDs, and paths are provenance only. Hidden model
reasoning is neither required nor reconstructed.

Every Standing, Atlas promotion, framework promotion, and release Claim Capsule
contains a content-addressed Verifier Bundle: entry points, exact library
artifacts, dependency lock, supported runtime, and integrity hashes sufficient
for offline verification.

### Schemas and migration

Each object kind versions its schema, canonicalization, producer, and verifier
contract independently from package, Journal, archive, and Projection formats.
Breaking interpretation changes advance the object schema major version;
compatible additions advance the minor version.

Objects and Journals never migrate in place. A deterministic Migration Receipt
binds old and new objects, migrator identity, warnings, and information loss.
Lossless format conversion may preserve claim meaning. Semantic reinterpretation
creates a new independently reviewed analysis or claim lineage. Unknown schemas
remain preservable and exportable even when the current library cannot interpret
them.

### Retention and status

Objects reachable from a Journal or Claim Manifest are durable and never
automatically collected. Only caches, locks, partial downloads, and unsealed
intermediates may expire automatically. Explicit pruning requires a verified
replacement archive and writes an Evidence Tombstone naming removed hashes,
reason, archive identity, and affected claims. Consumed sealed cases remain
durable with changed access state.

Claim reproducibility is `complete`, `degraded`, `externally-dependent`,
`unsupported`, or `corrupt`. Only `complete` may support offline-verifiable
Standing. Missing required evidence immediately downgrades the claim rather than
becoming a warning.

Journal sequence, hashes, causal references, and Checkpoints establish order.
Wall-clock values are optional caller-supplied Time Observations with explicit
clock source and uncertainty; the library never samples time implicitly to
create evidence identity.

## Consequences

Every important conclusion can be shared and re-verified without the original
repository checkout, provider, absolute paths, or mutable dashboard. Operators
retain ownership of untracked experiment state, and independent workspaces can
exchange claims without corrupting causal history. Storage grows monotonically
until the operator archives and explicitly prunes it, and qualifying claims pay
the cost of bundling their exact verifier runtime. Those costs are accepted in
exchange for durable, inspectable hill-climbing lineage.

## Evidence

- The existing Workspace object store, hash-chained Journals, archive importer,
  and rebuildable Standing projection establish the implementation direction.
- `EpisodeArchive` is the canonical persisted multi-agent execution record.
- `docs/research/agent-failure-scaling.md` identifies the full evidence and
  Failure Atlas graph that must survive.
- Inspect evaluation logs preserve task status, samples, transcripts, errors,
  results, metrics, and metadata: <https://inspect.aisi.org.uk/eval-logs.html>.
- METR Task Standard motivates portable, semantically versioned tasks:
  <https://metr.org/blog/2024-02-29-metr-task-standard/>.
- Vivaria preserves run requests, responses, actions, observations, tags, and
  results for trajectory analysis: <https://vivaria.metr.org/>.
