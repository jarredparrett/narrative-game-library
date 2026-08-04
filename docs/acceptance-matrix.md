# Acceptance matrix

Every accepted requirement links its source decision to an owning package,
fixture, capability test, and evidence. Agents may assemble this evidence; a
human Stage Reviewer decides whether the gate is accepted.

## Stage 0 — dependency-boundary spike

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Verismill integration boundary](https://github.com/jarredparrett/verismill-lean/issues/6) | `stage0.public-forge` | `adapters.verismill` | Stage 0 deed | `test_public_artifact_forge_is_seeded_verified_and_offline` | exact Artifact Result and Attestation | accepted 2026-08-04 |
| [Compilation determinism](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage0.cross-process` | `contracts.canonical` | Stage 0 deed | `test_stage0_fixture_is_byte_identical_across_processes` | matching artifact, manifest, request, and attestation hashes | accepted 2026-08-04 |
| [Package architecture](https://github.com/jarredparrett/verismill-lean/issues/7) | `stage0.import-boundary` | repository | adapter source | `test_verismill_adapter_has_no_private_or_mattermill_imports` | AST import audit | accepted 2026-08-04 |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage0.clean-build` | repository | locked environment | CI plus isolated offline run | source/wheel build and frozen-lock installation | accepted 2026-08-04 |

Human Stage Review: accepted by the repository owner after the public Python
3.11/3.13 CI run and isolated offline verification passed.

## Stage 1 — Workspace and lineage spine

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.object-integrity` | `workspace.store` | Micro Workspace | `test_content_addressed_store_detects_tampering_and_deduplicates` | object digest verification | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.lineage` | `workspace` | branched Micro Workspace | `test_draft_transitions_are_idempotent_branchable_and_human_readable` | Draft, branch, merge, Candidate, report | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.optimistic-concurrency` | `workspace` | stale Draft Head | `test_stale_writes_are_rejected_and_audited` | explicit conflict and audit Event | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.idempotency` | `workspace.journal` | repeated operation | `test_idempotency_key_cannot_name_different_content` | exact retry or conflict | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.atomic-transition` | `workspace` | simulated projection crash | `test_crash_after_journal_commit_leaves_reconstructable_state` | journal-driven recovery | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.portability` | `workspace` | deterministic archive | `test_index_rebuild_and_archive_import_are_path_independent` | byte-identical archives and verified import | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.concurrent-writers` | `workspace` | competing Writers | `test_competing_writers_produce_one_winner` | one accepted and one audited rejection | accepted 2026-08-04 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage1.journal-integrity` | `workspace.journal` | edited journal | `test_journal_tampering_is_detected` | failed hash-chain verification | accepted 2026-08-04 |

Human Stage Review: accepted by the repository owner after the Stage 1 tree
passed the public Python 3.11/3.13 CI run.

## Stage 2 — pure Kernel and Facilitated Investigation

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage2.valid-fixture` | `narrative` | Micro Game | `test_micro_fixture_passes_and_hashes_across_processes` | zero Findings and stable cross-process hash | accepted 2026-08-04 |
| [Kernel boundary](https://github.com/jarredparrett/verismill-lean/issues/18) | `stage2.extension-composition` | `kernel` | extra Accounting manifest | `test_namespaced_extensions_compose_without_changing_kernel_semantics` | Narrative profile pin plus independent namespace | accepted 2026-08-04 |
| [Domain ownership](https://github.com/jarredparrett/verismill-lean/issues/14) | `stage2.dangling-reference` | `narrative.validation` | missing Evidence ref | `test_defect_dangling_reference_quotes_missing_evidence` | exact missing ID and locus | accepted 2026-08-04 |
| [Domain ownership](https://github.com/jarredparrett/verismill-lean/issues/14) | `stage2.contradictory-truth` | `narrative.validation` | conflicting assignment | `test_defect_contradictory_truth_quotes_both_assignments` | both conflicting values | accepted 2026-08-04 |
| [Game research](https://github.com/jarredparrett/verismill-lean/issues/15) | `stage2.critical-access` | `narrative.validation` | missing Reveal | `test_defect_inaccessible_critical_evidence_names_the_evidence` | inaccessible critical Evidence ID | accepted 2026-08-04 |
| [Game research](https://github.com/jarredparrett/verismill-lean/issues/15) | `stage2.proof-redundancy` | `narrative.validation` | one Proof Path | `test_defect_single_point_proof_failure_names_the_only_path` | fragile path ID | accepted 2026-08-04 |
| [Game research](https://github.com/jarredparrett/verismill-lean/issues/15) | `stage2.reveal-timing` | `narrative.validation` | late Resolution | `test_defect_premature_proof_names_early_paths` | prematurely complete path IDs | accepted 2026-08-04 |
| [Domain ownership](https://github.com/jarredparrett/verismill-lean/issues/14) | `stage2.authorization` | `kernel` + `narrative` | expanded Reveal | `test_defect_unauthorized_disclosure_names_forbidden_seat` | unauthorized Seat ID | accepted 2026-08-04 |
| [Game research](https://github.com/jarredparrett/verismill-lean/issues/15) | `stage2.participation` | `narrative.validation` | objective-less Seat | `test_defect_inactive_seat_names_the_stranded_seat` | inactive Seat ID | accepted 2026-08-04 |
| [Game research](https://github.com/jarredparrett/verismill-lean/issues/15) | `stage2.recovery` | `narrative.validation` | no Intervention | `test_defect_unrecoverable_progression_quotes_missing_host_power` | missing recovery quote | accepted 2026-08-04 |
| [Domain ownership](https://github.com/jarredparrett/verismill-lean/issues/14) | `stage2.canonical-owner` | `narrative.derivations` | changed Truth assignment | `test_derived_views_read_one_truth_and_access_owner` | factuality changes while belief intent remains | accepted 2026-08-04 |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage2.purity` | `kernel` + `narrative` | source audit | `test_pure_packages_have_no_effectful_imports_or_hidden_registries` | no filesystem/network/clock/model/random imports | accepted 2026-08-04 |

Human Stage Review: accepted by the repository owner after the recreated clean
history and Stage 2 capability evidence were verified.

## Stage 3 — Candidate and Game Release compiler

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.release-identity` | `compiler` | materialized Micro Game | `test_candidate_release_and_bundle_identities_are_pinned` | pinned Candidate, Release, bundle, and Attempt links | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.cross-process` | `compiler` | materialized Micro Game | `test_release_bytes_are_identical_across_processes` | byte-identical base64 archives | implemented; human gate pending |
| [Release contract](https://github.com/jarredparrett/verismill-lean/issues/10) | `stage3.self-contained` | `compiler` | Release ZIP | `test_release_is_self_contained_and_every_file_hash_verifies` | exact files and verified hashes | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.blockers` | `compiler` | tampered Candidate | `test_tampered_candidate_blocks_without_partial_release` | blocked Attempt and no Release bytes | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.warnings` | `compiler` | pacing advisory | `test_warnings_remain_visible_without_claiming_stronger_standing` | immutable warning and development-only standing | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.input-commitment` | `compiler` | changed seed/access | `test_play_affecting_inputs_change_candidate_and_release_identity` | distinct Candidate and Release IDs | implemented; human gate pending |
| [Release contract](https://github.com/jarredparrett/verismill-lean/issues/10) | `stage3.secrecy` | `compiler.projections` | both Seat views | `test_seat_projections_contain_no_truth_proof_or_material_bytes` | recursive key and byte audit | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.freeze-gate` | `compiler` | invalid Draft/lock | `test_invalid_draft_or_component_lock_cannot_freeze_candidate` | no Candidate and quoted blockers | implemented; human gate pending |
| [Package architecture](https://github.com/jarredparrett/verismill-lean/issues/7) | `stage3.purity` | `compiler` | source audit | `test_compiler_package_has_no_ambient_effect_imports` | no filesystem/network/clock/model/random imports | implemented; human gate pending |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.traceability` | `compiler` | Release manifest | `test_release_manifest_is_canonical_and_commits_component_graph` | canonical manifest and complete hash graph | implemented; human gate pending |

Later stages append rows rather than replacing this evidence.
