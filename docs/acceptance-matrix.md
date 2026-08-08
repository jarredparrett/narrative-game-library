# Acceptance matrix

Every accepted requirement links its source decision to an owning package,
fixture, capability test, and evidence. Agents may assemble this evidence; a
the frozen policy decides whether the gate is accepted; human evidence remains
separately attributable when present.

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
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.release-identity` | `compiler` | materialized Micro Game | `test_candidate_release_and_bundle_identities_are_pinned` | pinned Candidate, Release, bundle, and Attempt links | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.cross-process` | `compiler` | materialized Micro Game | `test_release_bytes_are_identical_across_processes` | byte-identical base64 archives | accepted 2026-08-04 |
| [Release contract](https://github.com/jarredparrett/verismill-lean/issues/10) | `stage3.self-contained` | `compiler` | Release ZIP | `test_release_is_self_contained_and_every_file_hash_verifies` | exact files and verified hashes | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.blockers` | `compiler` | tampered Candidate | `test_tampered_candidate_blocks_without_partial_release` | blocked Attempt and no Release bytes | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.warnings` | `compiler` | pacing advisory | `test_warnings_remain_visible_without_claiming_stronger_standing` | immutable warning and development-only standing | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.input-commitment` | `compiler` | changed seed/access | `test_play_affecting_inputs_change_candidate_and_release_identity` | distinct Candidate and Release IDs | accepted 2026-08-04 |
| [Release contract](https://github.com/jarredparrett/verismill-lean/issues/10) | `stage3.secrecy` | `compiler.projections` | both Seat views | `test_seat_projections_contain_no_truth_proof_or_material_bytes` | recursive key and byte audit | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.freeze-gate` | `compiler` | invalid Draft/lock | `test_invalid_draft_or_component_lock_cannot_freeze_candidate` | no Candidate and quoted blockers | accepted 2026-08-04 |
| [Package architecture](https://github.com/jarredparrett/verismill-lean/issues/7) | `stage3.purity` | `compiler` | source audit | `test_compiler_package_has_no_ambient_effect_imports` | no filesystem/network/clock/model/random imports | accepted 2026-08-04 |
| [Compiler semantics](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage3.traceability` | `compiler` | Release manifest | `test_release_manifest_is_canonical_and_commits_component_graph` | canonical manifest and complete hash graph | accepted 2026-08-04 |

Human Stage Review: accepted by the repository owner after the deterministic
Release and clean cross-version build evidence were verified.

## Stage 4 — Session Authority and runtime

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.trajectory` | `runtime` | complete Micro Session | `test_complete_session_replays_to_the_pinned_resolution` | pinned nine-Event chain and resolved state | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.authorization` | `runtime` | both Actor contexts | `test_authorization_precedes_snapshot_and_resource_serialization` | opaque rejection and distinct authorized projections | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.command-atomicity` | `runtime` | stale/retried Commands | `test_commands_are_atomic_revision_checked_and_exactly_idempotent` | one Event or rejection Receipt | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.replay` | `runtime` | portable/tampered History | `test_restart_recovery_and_tamper_detection_are_deterministic` | identical restored state and detected edit | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.actor-replacement` | `runtime` | replacement Actor | `test_actor_replacement_does_not_transfer_private_notes` | ended Binding and isolated notes | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.forks` | `runtime` | simulation fork | `test_simulation_fork_is_isolated_and_live_model_substitution_is_blocked` | verified prefix and isolated model suffix | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.session-isolation` | `runtime` | two Sessions | `test_concurrent_sessions_over_one_release_remain_isolated` | distinct state and Event heads | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.physical-evidence` | `runtime` | witnessed receipt | `test_physical_disclosure_preserves_method_and_evidence_grade` | explicit Disclosure Event grade | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.exceptional-intervention` | `runtime` | unforeseen host action | `test_exceptional_intervention_is_exact_recorded_and_access_bounded` | exact content/reason/audience and blocked leak | accepted 2026-08-04 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage4.cross-process` | `runtime` | complete Micro Session | `test_session_bytes_and_snapshots_match_across_processes` | identical History and Seat Snapshot bytes | accepted 2026-08-04 |
| [Package architecture](https://github.com/jarredparrett/verismill-lean/issues/7) | `stage4.purity` | `runtime` | source audit | `test_runtime_core_has_no_ambient_effect_imports` | no filesystem/network/clock/model/random imports | accepted 2026-08-04 |

Human Stage Review: accepted by the repository owner after the complete replay,
authorization, physical-disclosure, and isolation evidence was presented.

## Stage 5 - rich worked example and Physical Export

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage5.complete-example` | `stage5_fixture` | The Ashwood Ledger | `test_worked_scenario_freezes_forges_compiles_runs_and_persists` | Candidate, artifact, Release, Physical Export, Session, Workspace | accepted 2026-08-05 |
| [Verismill integration boundary](https://github.com/jarredparrett/verismill-lean/issues/6) | `stage5.artifact-boundary` | `adapters.verismill` | 1997 Madison deed | `test_artifact_boundary_preserves_bytes_attestation_and_only_pinned_facts` | exact bytes, request pins, manifest, measurement, attestation | accepted 2026-08-05 |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage5.claim-trace` | `physical.exporter` | eight displayed claims | `test_every_displayed_claim_has_reexecuted_proposition_lineage` | quoted material span or exact artifact-request pin | accepted 2026-08-05 |
| [Physical export](https://github.com/jarredparrett/verismill-lean/issues/11) | `stage5.physical-equivalence` | `physical.exporter` | exact package plan | `test_physical_plan_is_access_equivalent_explicit_and_spoiler_safe` | copy, audience, condition, custodian, container, duplicate lineage | accepted 2026-08-05 |
| [Physical export](https://github.com/jarredparrett/verismill-lean/issues/11) | `stage5.print-safety` | `physical.exporter` | 12 printable PDFs | `test_every_print_page_is_letter_sized_marked_and_preflighted` | page size/count, fictional mark, exact unmodified source artifact | accepted 2026-08-05 |
| [Session authority](https://github.com/jarredparrett/verismill-lean/issues/5) | `stage5.authorized-play` | `runtime` | 13-Event worked Session | `test_authorized_seat_experiences_remain_distinct_and_replay_portably` | distinct Seat materials, exact replay, no trusted truth leak | accepted 2026-08-05 |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage5.claim-gate` | `physical.exporter` | drifted host-guide claim | `test_physical_export_detects_a_broken_displayed_claim` | failed export naming absent quote | accepted 2026-08-05 |
| [Persistence semantics](https://github.com/jarredparrett/verismill-lean/issues/16) | `stage5.rebuild` | repository | two isolated output roots | `test_complete_rebuild_is_path_independent_and_offline` | exact Candidate, Release, Physical Export, Session, Workspace; no network | accepted 2026-08-05 |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage5.cross-process` | repository | two CLI processes | `test_stage5_cli_outputs_are_identical_across_processes` | byte-identical durable outputs and matching summary | accepted 2026-08-05 |
| [Physical export](https://github.com/jarredparrett/verismill-lean/issues/11) | `stage5.independent-operation` | `physical.exporter` | assembly guide | `test_an_unfamiliar_operator_has_complete_assembly_and_run_instructions` | setup, containers, run controls, verification, provenance | accepted 2026-08-05 |

Human Stage Review: accepted by the repository owner after reviewing the final
rendered package, deterministic release evidence, and honest realism standing.

## Stage 6 - native agentic hill climbing

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.closed-bundle` | `climb.model` + `climb.validation` | closed climb bundle | `test_valid_native_climb_bundle_has_no_findings` | immutable typed Tasks, receipts, Findings, Requirements, Evaluations, Reviews, Transitions, and Standing | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.human-transition` | `climb.ledger` + `workspace` | rejected and approved Ashwood Proposals | `test_proposal_is_inert_until_exact_human_approval_advances_workspace` | agent approval and rejected review are inert; exact human approval advances once | accepted 2026-08-05 |
| [Agentic policy](adr/0007-agentic-qualification-keeps-human-evidence-optional.md) | `stage6.agentic-transition` | `climb.ledger` + `workspace` | independent Agent Review | `test_independent_agent_review_can_advance_without_a_human_gate` | exact reviewer Model Receipt and principal separation authorize once | implemented |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.blind-inputs` | `climb.validation` | blind judge receipt/exposure defects | `test_blind_evaluation_requires_exact_judge_receipts_and_exposure_ledger` | exact judge receipts and task-scoped Exposure Ledger | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.role-blindness` | `climb.validation` | excluded builder as judge | `test_builder_or_fixer_cannot_judge_its_candidate` | explicit self-judging blocker | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.harvest-honesty` | `climb.validation` | scored harvest | `test_harvest_cannot_claim_a_score_or_standing` | harvest cannot move a rung | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.portable-replay` | `climb.ledger` + `workspace` | relocated Stage 6 archive | `test_climb_reopens_archives_and_preserves_exact_model_outputs` | verified hash chains, raw/parsed model outputs, and path-independent archive | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.vertical-loop` | `stage6_fixture` | The Ashwood Ledger | `test_ashwood_climb_moves_only_after_review_and_improves_frozen_score` | persisted fixture control plane from 66.9 baseline to 82.8 child; no hard-gate regression | accepted 2026-08-05 |
| [Stage 6 implementation](https://github.com/jarredparrett/narrative-game-library/issues/2) | `stage6.offline-replay` | repository | two isolated CLI processes | `test_stage6_build_path_is_offline_and_cross_process_deterministic` | byte-identical portable archives and summaries with network blocked | accepted 2026-08-05 |

Human Stage Review: accepted by the repository owner through merge of PR #3
after the public Python 3.11/3.13 CI run passed. The offline judge fixture
demonstrates control-plane correctness and illustrative score movement only;
it does not claim measured quality improvement, fresh human play, or public
realism standing.

## Stage 7 - real measured-climb proof

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.model-driver` | `climb.execution` + `climb.drivers` | replaceable model occupants | `test_replaceable_driver_persists_an_exact_replay_envelope` | provider, resolved model, inputs, raw/parsed output, tools, and seed survive replay | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.complete-trial` | `climb.trial` | complete Ashwood Release and Physical Export | `test_blind_trial_contains_complete_seat_experience_without_trusted_truth` | complete authorized player tree with exact printable assets | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.blindness` | `climb.trial` + `climb.validation` | anonymous baseline and child trials | `test_trial_conceals_source_identity_answers_and_provenance` | no trusted truth, answers, lineage labels, or prior scores | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.real-measurement` | `stage7_experiment` | fresh three-member model panel | `test_measurement_records_driver_scores_and_quoted_spans_without_selecting` | Evaluation `evaluation:8cdffcda972cf1ee8671e68cfbd7c2338d36ddb7a0772ea4a836bdf9b28087cf`; Instrument 1.1; score 72.4; failed | accepted as process evidence 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.human-gate` | `climb.ledger` + `workspace` | approved S6 Proposal | `test_builder_receives_answer_safe_requirements_and_stops_at_proposal` | exact human Review precedes canonical child Transition | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.full-child` | compiler + `physical` + `climb.trial` | S6 child | `test_complete_child_package_changes_trial_without_revealing_lineage` | verified Candidate, Release, Physical Export, Blind Trial, and Trial Binding | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.archive-fidelity` | `climb.trial` | resource and dossier rendition namespaces | `test_preflight_paths_name_exact_shipped_print_files`; `test_preflight_projection_handles_dossier_rendition_namespace` | every preflight path names exact shipped Trial bytes; verifier rejects unshipped paths | accepted 2026-08-06 after live model falsification |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.selection` | `climb.selection` | baseline/child Evaluations | `test_hard_gate_regression_retains_baseline_despite_higher_score` | Decision `selection:56a7d8b872806e9184f627a1a99b533d0aceff84170e4d2ed99ab78a1ad8ace6`; frozen rule retained baseline because child failed qualification | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.portability` | Workspace + `climb.ledger` | relocated Stage 7 archive | `test_prepared_archive_relocates_complete_release_physical_and_trial_bytes` | exact releases, exports, trials, receipts, evaluations, and selection remain verifiable | accepted 2026-08-05 |
| [Stage 7 implementation](https://github.com/jarredparrett/narrative-game-library/issues/4) | `stage7.honest-standing` | `climb.selection` | failed fresh child panel | `test_capability_fixture_scores_cannot_select_a_child` | no standing issued and no quality acceptance claimed | accepted 2026-08-05 |

Human Stage Review: the repository owner accepted Stage 7 as a bounded process
prototype after the live panel completed. The measured child did not qualify:
`72.4` overall, with all hard gates green, and the frozen selection rule
retained the baseline. This closes the orchestration proof while preserving
the failed result and its quoted findings as design input. It does not accept
Ashwood's game quality or confer human-play standing.

Deferred general rules for Stage 8 and later validation: phase-accurate
availability, nonduplicative progressive disclosure, distinct character voice,
artifact-specific measurement applicability, and objective host checkpoints.

## Stage 8 - reusable experiment and orchestration API

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.plan` | `experiment.Experiment` + `climb.ExperimentPlan` | relocated fixture Experiment | `test_experiment_plan_persists_profile_instrument_and_archive_identity` | one portable plan freezes profile identity, version, Instrument, and branch | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.profile-adapter` | `experiment.GameProfileAdapter` | fixture investigation profile | `test_profile_adapter_builds_answer_safe_proposal_and_agent_review_moves_branch` | profile builds and revises; Proposal remains inert until an exact independent receipted Review | implemented |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.human-evidence` | `climb.HumanReceipt` + `experiment.Experiment` | model baseline and human child panels | `test_model_and_human_judges_are_distinct_first_order_receipts` | exact human observations participate without impersonating Model Receipts | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.frozen-strategy` | `experiment.ScoreAggregator` | attempted aggregator/profile swaps | `test_frozen_aggregation_and_profile_identity_cannot_be_swapped` | alternate strategies and adapter versions require explicit contract changes | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.selection` | `experiment.Experiment` + `climb.selection` | mixed model/human evidence | `test_model_and_human_judges_are_distinct_first_order_receipts` | frozen evidence classes select the qualifying child without granting Standing | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.portability` | Workspace + `experiment.Experiment` | exported and relocated archive | `test_experiment_plan_persists_profile_instrument_and_archive_identity` | profile contract, packages, receipts, evaluations, and lineage remain content-addressed | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.fixture-independence` | `experiment` package | source dependency audit | `test_public_experiment_api_has_no_ashwood_or_stage_fixture_dependency` | reusable API imports no Ashwood or stage fixture module | accepted 2026-08-05 |
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.worked-migration` | `stage7_experiment` | fresh Stage 7 model panel | `test_fresh_panel_uses_three_identities_and_frozen_dimension_medians` | worked example delegates panel measurement, review, child binding, and selection to the public Experiment API | accepted 2026-08-05 |

Human Stage Review: accepted by the repository owner through merge of PR #12
after the public Python 3.11/3.13 CI run passed. This stage generalizes
experiment mechanics; it does not claim new Ashwood quality standing or
human-play acceptance.

## Stage 9 - agentic game-authoring contract

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 9 implementation](https://github.com/jarredparrett/narrative-game-library/issues/7) | `stage9.blueprint` | `blueprint` | Vanished Ledger rich-text Blueprint | `test_blueprint_derives_canonical_resources_and_validates_arc_alignment` | Material text derives Resource hashes; Arc Beats stay aligned with canonical Reveals | accepted 2026-08-05 |
| [Stage 9 implementation](https://github.com/jarredparrett/narrative-game-library/issues/7) | `stage9.operations` | `blueprint` | Requirement-bound Material revision | `test_authoring_operations_are_requirement_complete_and_domain_sized` | typed operation, exact Requirement coverage, preserved Truth Model | accepted 2026-08-05 |
| [Stage 9 implementation](https://github.com/jarredparrett/narrative-game-library/issues/7) | `stage9.adapter` | `profiles.facilitated_investigation` | complete rich-text package | `test_profile_adapter_builds_complete_deterministic_rich_text_package` | byte-identical Candidate, Release, Physical Export, and Blind Trial | accepted 2026-08-05 |
| [Stage 9 implementation](https://github.com/jarredparrett/narrative-game-library/issues/7) | `stage9.human-control` | `experiment` + profile adapter | witness-voice climb | `test_agentic_authoring_stops_at_human_review_before_child_transition` | Proposal preview, exact human Review, fresh child remeasurement, and frozen selection | accepted 2026-08-05 |

Human Stage Review: accepted by the repository owner through merge of PR #13
after the public Python 3.11/3.13 CI run passed. This stage proves reusable
construction and revision mechanics; it does not claim that the synthetic
worked Blueprint has human-play standing.

## Stage 10 - human-play evidence and standing

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.first-order-run` | `playtest` + `climb.ledger` | completed Micro Game Session | `test_playtest_run_binds_live_session_package_roles_consent_and_observations` | exact Release and Physical Export, live Session history, role Authorities, versioned consent, phase-scoped quotes, and frozen scores | implemented |
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.harvest` | `playtest.PlaytestProgram` + `experiment.Experiment` | progressive-disclosure observation | `test_playtest_findings_translate_to_answer_safe_requirements` | quoted Finding becomes attributable Requirement and inert builder Proposal without exposing the answer | implemented |
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.standing` | `playtest` + `climb.validation` | two passing fresh cohorts and divergent model panel | `test_two_fresh_runs_and_independent_review_can_support_accepted_standing` | exact model-human comparison, preserved divergence, independent publisher, and accepted Standing | implemented |
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.freshness` | `playtest` + `climb.validation` | simulation, repeated cohort, and participant reviewer | `test_simulation_reused_cohort_and_participant_reviewer_cannot_claim_fresh_standing` | each invalid human-play or review claim is rejected before Standing | implemented |
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.portability` | Workspace + `climb.ledger` | relocated Stage 10 archive | `test_human_play_evidence_survives_portable_archive_replay` | Runs, exact responses, comparison, and Standing reconstruct and verify after relocation | implemented |
| [Stage 10 implementation](https://github.com/jarredparrett/narrative-game-library/issues/8) | `stage10.cross-process` | Workspace + `playtest` | two isolated evidence programs | `test_human_play_archive_is_identical_across_processes` | byte-identical portable archive under different process hash seeds and paths | implemented |

Human Stage Review: pending review of the public CI run and Stage 10 evidence
lineage. The capability fixture proves the measurement contract; its synthetic
scores do not confer standing on a public game Release.

## Stage 11 - tutorial-led experience boundary

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.headless-boundary` | `experience.reference` | reference renderer | `test_reference_renderer_depends_only_on_projection_and_canonical_contracts` | renderer imports projection and canonical serialization contracts, not game or authority rules | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.tutorial` | `experience.projections` | Vanished Ledger tutorial | `test_tutorial_explains_components_through_the_exact_worked_game` | deterministic component ownership, outputs, and exact in-game references | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.boundary` | `experience` | five exact projections | `test_surfaces_share_exact_identity_without_sharing_one_layout_or_authority` | distinct maker, host, player, and print projections share Release, Session, and Physical Export identities | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.authorization` | `experience.projections` + `runtime` | Avery and Blake views | `test_character_web_view_contains_only_runtime_authorized_material` | recursive role separation with no trusted truth or cross-Seat material | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.controls` | `experience.projections` + `runtime` | typed UI intents | `test_host_and_player_intents_use_session_authority_and_reject_stale_or_foreign_views` | stale, foreign, and unavailable actions cannot bypass Session authority | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.reference-ui` | `experience.reference` | standalone reference pages | `test_reference_pages_are_accessible_intent_emitters_bound_to_exact_exports` | responsive offline HTML, keyboard focus, reduced-motion support, typed intents, and exact identities | implemented |
| [Stage 11 experience boundary](https://github.com/jarredparrett/narrative-game-library/issues/9) | `stage11.determinism` | `stage11_fixture` | complete experience export | `test_worked_experience_is_offline_and_byte_identical_across_processes` | byte-identical tutorial, projections, archives, Session, and summary under different process hash seeds | implemented |

Human Stage Review: pending review and merge of the Stage 11 implementation.
The reference HTML demonstrates the application boundary; it does not claim a
production web service, completed dossier depth, or six-player human standing.

## Stage 11 - deep dossiers and phase-aware characters

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Deep dossiers](https://github.com/jarredparrett/narrative-game-library/issues/15) | `stage11.dossiers` | `narrative.CharacterProgram` + physical exporter | six Winter Observatory roles | `test_six_dossiers_are_complete_canonical_and_render_three_to_five_pages` | deterministic layered Markdown and 3–5 page PDFs for all six Seats | implemented |
| [Deep dossiers](https://github.com/jarredparrett/narrative-game-library/issues/15) | `stage11.character-example` | worked fixture | six-role review package | `test_worked_character_export_is_byte_identical` | exact game, six Markdown/PDF pairs, and hash-bearing summary reproduce byte-identically | implemented |
| [Deep dossiers](https://github.com/jarredparrett/narrative-game-library/issues/15) | `stage11.dossier-secrecy` | compiler Seat projection | Eleanor projection | `test_seat_projection_has_deep_play_but_never_host_or_other_seat_truth` | host solution and other Dossier identities are absent | implemented |
| [Agentic characters](https://github.com/jarredparrett/narrative-game-library/issues/16) | `stage11.character-gates` | Character Program validator | adversarial mutations | `test_validator_blocks_leakage_unreachable_secrets_and_dead_end_arcs` | leakage, unreachable revelations, and dead ends block release | implemented |
| [Agentic characters](https://github.com/jarredparrett/narrative-game-library/issues/16) | `stage11.character-agency` | Session Authority | six-model simulation cast | `test_agentic_cast_uses_same_authority_and_persists_human_direction` | move, belief, objective, and human direction replay as Character State | implemented |
| [Agentic characters](https://github.com/jarredparrett/narrative-game-library/issues/16) | `stage11.phase-agency` | Session Authority | future Move attempt | `test_current_phase_rejects_future_moves` | a Character Agent cannot act outside its current Phase Arc | implemented |

Human Stage Review: pending review and merge of issues 15 and 16.

The worked example proves structural depth, determinism, access safety, and
phase agency. It does not claim six-player human standing; that is Stage 11
issue 17.

## Stage 11 - exact six-player human-play boundary

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-rubric` | Frozen Instrument | ten dossier-experience dimensions | `test_human_instrument_freezes_every_issue_17_dimension_and_gate` | onboarding, recall, post-exposure agency, relationships, social agency, cognitive load, reveal guidance, emotional resolution, intervention, and enjoyment freeze before recruitment | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-trace` | Play Observation | exact response metadata | `test_response_contract_preserves_stage_timestamp_rubric_and_defect_owner` | stage, timestamp, rubric item, exact response ref, and defect owner round-trip | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-kit` | worked preparation | selected Candidate 6 child | `test_review_forms_cover_six_roles_every_phase_and_every_rubric_item` | six assignments, all Phases, all rubric items, consent, host log, and debrief are deterministic | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-boundary` | Playtest Program | strict Micro Run | `test_strict_protocol_requires_individual_stages_and_timestamped_facilitation` | valid first-order Run includes individual pre/post responses, timestamped facilitation, and group debrief | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-ingest-atomicity` | Climb Ledger | invalid late-stage Run | `test_closed_run_preflight_rejects_without_partial_lineage_or_objects` | closed-set preflight leaves journals and object store unchanged | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.human-ingest-cli` | Playtest recorder | completed file bundle | `test_operator_bundle_records_and_verifies_exact_run_idempotently` | offline repeat records one identical verified Run | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.session-release` | Release loader | compiled and corrupt archives | `test_exact_release_loader_round_trips_compiled_archive_and_rejects_corruption` | exact files and manifest rehash before runtime | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.session-transcript` | Session recorder | complete host plan | `test_host_transcript_materializes_same_resolved_live_history_twice` | repeated physical transcript yields identical live history | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.agentic-session` | Session recorder | complete model-seat plan | `test_same_transcript_can_record_an_exact_agentic_play_run` | model Actors use the same exact replayable Session Authority | implemented |
| [Six-player playtest](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.session-cli` | Session recorder | rejected command | `test_session_cli_writes_only_after_every_transcript_command_passes` | no partial history is written | implemented |

Prepared exact package: Candidate `sha256:f1d0425d…fc767`, Release
`sha256:5d170735…b998`, Physical Export `sha256:9cd7267b…b463`, and Protocol
`playtest-protocol:1bd2ef94…ea0f`. The portable Workspace verifies cleanly.

Optional Human Stage Review: no completed six-player Run exists. Preparation
does not impersonate first-order human evidence or confer human-play standing;
the missing Run does not block agentic qualification.

## Stage 12 - public-release qualification

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.policy` | Public Release Policy | twelve ordered gates | `test_policy_freezes_one_owned_gate_for_every_stage_8_through_12_requirement` | policy content identity, owners, and remediation | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.evidence-availability` | Evidence bundle | corrupt object map | `test_dangling_or_corrupt_hash_strings_are_not_evidence` | claimed bytes are supplied and rehashed | implemented |
| [Roadmap](https://github.com/jarredparrett/narrative-game-library/issues/5) | `release.stage8.portable-experiment` | Experiment | exact binding | `test_portable_experiment_gate_requires_verified_exact_package_binding` | Workspace and ledger verification | implemented |
| [Roadmap](https://github.com/jarredparrett/narrative-game-library/issues/5) | `release.stage9.reusable-authoring` | Authoring | exact proof ref | `test_reusable_authoring_gate_requires_content_addressed_proof` | Blueprint/adapter proof | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage10.agentic-standing` | Agentic measurement | two blind evaluations | `test_agentic_standing_requires_two_passing_blind_evaluations` | one panel cannot self-corroborate | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage10.independent-agentic-verification` | Agentic review | distinct authority principals | `test_independent_agentic_verification_excludes_judge_principals` | review agent cannot be a blind judge | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.human-optionality` | Evidence policy | agent-only fixture | `test_human_play_is_optional_evidence_not_a_release_gate` | complete qualification uses no human object | implemented |
| [Human play](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.model-human-operator-path` | Playtest operator | configured model panel and approved review manifests | `test_operator_model_baseline_records_exact_evaluation_for_later_human_comparison`; `test_operator_review_preflights_comparison_and_standing_without_partial_writes` | exact blind Evaluation precedes two fresh cohorts; comparison and independent Standing need no custom Python | implemented; evidence pending |
| [Human play](https://github.com/jarredparrett/narrative-game-library/issues/17) | `stage11.codex-driver` | Model provider adapter | isolated anonymous ZIP | `test_codex_driver_isolates_trial_and_returns_replay_receipts`; `test_codex_driver_rejects_archive_path_escape_before_invocation` | explicit model, byte-exact quote instruction, ephemeral workspace, CLI trace, and path confinement | implemented; valid v7 Evaluation `evaluation:5b1fdbed784e9c3a4a76f760e69c72331ec9fae00e5dece63f9b9178c5b250d9` |
| [Experience](https://github.com/jarredparrett/narrative-game-library/issues/9) | `release.stage11.creator-player-print` | Experience | exact proof ref | `test_creator_player_print_gate_requires_one_exact_lineage_proof` | one Release/Session lineage | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.tagged-upstreams` | Distribution | version map | `test_tagged_upstream_gate_rejects_git_and_commit_pins` | repository pins fail | implemented; releases pending |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.compatibility` | Public API | epoch and policy | `test_compatibility_gate_requires_stable_epoch_and_exact_policy` | experimental epoch fails | implemented; decision pending |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.support-matrix` | Verification | Python receipts | `test_support_matrix_gate_requires_exact_receipt_for_each_supported_python` | 3.11 and 3.13 required | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.package-artifacts` | Distribution | package refs | `test_package_gate_requires_exact_sdist_and_wheel_refs` | exact sdist and wheel | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.documentation` | Documentation | document refs | `test_documentation_gate_requires_every_public_entry_path` | five required entry paths | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.known-limitations` | Publisher | disclosure | `test_limitations_gate_makes_debt_visible_without_upgrading_standing` | nonempty honest limitations | implemented |
| [Release decision](https://github.com/jarredparrett/narrative-game-library/issues/10) | `release.stage12.release-attestation` | Release review | exact agent receipt | `test_release_attestation_requires_distinct_agent_and_exact_model_receipt` | distinct principal, policy/version/standing/package binding | implemented |

The evaluator is complete. The agent-only capability fixture qualifies, while
the current real release remains `not_qualified` until its exact agentic
evidence, upstream release versions, and contract epoch 1 exist.

## Stage 11 - portable qualification spine and Candidate 6 migration

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 11 retrospective implementation](https://github.com/jarredparrett/narrative-game-library/issues/18) | `stage11.portable-spine` | `experiment.ExperimentSpine` + Workspace | selected Candidate with 19 external measurements | `test_candidate_6_standing_is_separate_derived_and_portable` | exact Release, Physical Export, approval, evidence, accessibility contracts, external capsules, and separated standing survive relocation | implemented |
| [Stage 11 retrospective implementation](https://github.com/jarredparrett/narrative-game-library/issues/18) | `stage11.derived-standing` | `experiment.ExperimentSpine` | stale projection and removed external object | `test_projection_is_replaced_from_journal_and_mutation_is_detected` | journal replay replaces stale status and content verification rejects missing evidence | implemented |
| [Stage 11 retrospective implementation](https://github.com/jarredparrett/narrative-game-library/issues/18) | `stage11.rung-integrity` | qualification journal | missing parent and forged approval | `test_parentage_and_exact_approval_scope_cannot_be_forged` | historical parent anchors and exact Candidate/collection approval scope are mandatory | implemented |
| [Stage 11 retrospective implementation](https://github.com/jarredparrett/narrative-game-library/issues/18) | `stage11.evidence-invariants` | `contracts.evidence` | incomplete claim trace and interpreted accessible rendition | `test_claim_and_accessibility_contracts_reject_missing_or_interpreted_evidence` | every accepted proof path is licensed; native and accessible propositions match; artifact interpretation remains empty | implemented |
| [Stage 11 retrospective implementation](https://github.com/jarredparrett/narrative-game-library/issues/18) | `stage11.cross-system-reference` | `experiment.migration` | public Verismill facade stub | `test_external_verismill_reference_uses_only_the_verified_public_facade` | path-free capsule seals verified replay, bus head, manifest, and attestation and rejects identity mismatch | implemented |

The real Candidate 6 migration was also executed against all 19 historical
Verismill Experiments and imported into a new directory. Both Workspace and
qualification verification passed. This preserves historical evidence and
creates no new Candidate or standing claim. The exact results and limitations
are recorded in the [Winter Observatory retrospective](retrospectives/winter-observatory-hill-climb.md).

## Stage 11 - impact-scoped, bounded experiment execution

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.efficiency-routing` | `climb.planning` | every supported finding class | `test_finding_routes_choose_the_smallest_loop_and_explain_broadening` | default owner and loop are explicit; broader scope requires a persisted reason | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.impact` | `climb.planning` | seven typed contract changes | `test_impact_policy_invalidates_only_contract_dependents` | identical hashes carry forward; critical evidence, accessibility, canonical, host, artifact, renderer, and instrument changes derive distinct obligations | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.stop-rules` | `experiment.EfficiencyController` | handwriting-register preflight | `test_one_tranche_approval_allows_bounded_work_then_three_failures_escalate` | one tranche approval permits iteration; the third repeated failure escalates and preserves baseline | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.budgets` | `climb.planning` + `experiment.EfficiencyController` | one-iteration budget | `test_budget_exhaustion_parks_debt_and_observations_are_idempotent` | exhaustion parks debt, idempotent replay does not spend twice, and baseline remains selected | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.concurrent-panel` | `climb.execution` + `experiment.Experiment` | three barrier-synchronized judges | `test_independent_model_calls_are_concurrent_but_receipts_are_ordered` | calls overlap while replay receipts preserve input authority order | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.active-projection` | `experiment.EfficiencyController` | relocated bounded plan | `test_active_projection_is_portable_replayable_and_detects_staleness` | target, route, invalidation, approvals, budget, stop state, and next transition replay after relocation | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.current-experiment` | `ExperimentSpine` + `EfficiencyController` | Candidate 6 with active handwriting plan | `test_current_standing_embeds_the_active_efficiency_plan` | current standing contains the derived active plan and next human boundary | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.formal-boundary` | `climb.EfficiencyPlan` | exact Candidate 7 measurement | `test_formal_measurement_freezes_child_and_excludes_its_fixer` | standing is allowed only for an exact child with independent judges | implemented |
| [Stage 11 efficiency](https://github.com/jarredparrett/narrative-game-library/issues/19) | `stage11.review-boundaries` | `experiment.EfficiencyController` | exact Candidate 7 formal lifecycle | `test_formal_panel_runs_once_between_candidate_review_and_disposition` | completed-Candidate review precedes exact evidence; disposition follows it | implemented |

The worked Winter Observatory plan replaces 76 builds across four full-suite
preflights and 111 historical full artifact-judge calls with at most three
representative diagnostic builds, six non-standing diagnostic calls, and one
three-judge formal panel.
The other eighteen results carry forward only when their artifact bytes are
content-identical. This is execution-efficiency evidence, not a new realism or
public-release standing claim.

## Version 0.19 - agentic generation

| Requirement | Owner | Capability test | Evidence | Status |
|---|---|---|---|---|
| `generation.contracts` | `generation.model` | `test_generation_contracts_are_versioned_content_addressed_and_deterministic` | strict cross-process Creative Brief, role, budget, stop, and artifact-plan identities | implemented |
| `generation.creation-parse` | facilitated-investigation adapter | `test_profile_parses_only_complete_exact_valid_initial_creation_output` | complete canonical Blueprint or rejection without silent repair | implemented |
| `generation.artifact-truth` | Blueprint + artifact plan | `test_artifact_truth_binding_invalidates_every_canonical_world_drift` | exact pins/canon are content-bound to referenced Proposition meanings, truth assignments, and Events; either-side drift invalidates the plan | implemented |
| `generation.coordinator` | `GenerationCoordinator` | `test_brief_to_passing_candidate_is_resumable_and_fully_receipted` | brief → creator → independent review → failed blind round → answer-safe revision → fresh passing round → selected child; replay invokes no model twice | implemented |
| `generation.artifacts` | Verismill suite importer + compiler | `test_accepted_artifact_suite_replaces_source_text_at_compilation` | import-only public suite verification, world binding, member qualification, request/manifest agreement, PDF replacement, and preserved attestations | implemented |

## Version 0.20 - production artifact closure

| Requirement | Owner | Capability test | Evidence | Status |
|---|---|---|---|---|
| `generation.production-artifacts` | facilitated-investigation adapter | `test_production_target_requires_complete_evidence_artifact_coverage` | production derives the full non-Dossier evidence set and rejects empty or partial Artifact Plans | implemented |
| `generation.release-target` | `GenerationPlan` + status projection | `test_release_target_is_frozen_without_changing_legacy_plan_identity` | production intent is content-addressed while legacy development Plan identities remain stable | implemented |
| `generation.production-measurement` | facilitated-investigation adapter + blind panel | `test_production_instrument_requires_visual_and_host_quality_floors` | production requires independent design/usability floors, three judges, and visual inspection of exact print PDFs | implemented |
| `generation.production-visual-inspection` | blind panel | `test_visual_panel_requires_a_verified_receipt_for_every_print_pdf` | every judge returns exact paths, verified page counts, and visual observations for the complete print set; text-only scoring is rejected | implemented |
| `generation.exact-artifact-bytes` | Physical Export + Verismill suite importer | `test_accepted_artifact_suite_replaces_source_text_at_compilation` | accepted PDFs keep native geometry and enter the player package byte-identically; preflight proves the content hash | implemented |
| `generation.production-accessibility` | Verismill suite importer | `test_accepted_artifact_suite_replaces_source_text_at_compilation` | every production artifact requires an accessible specification and embedded extractable/OCR text | implemented |

## Version 0.21 - Harbor multi-agent RL environment

| Requirement | Owner | Capability test | Evidence | Status |
|---|---|---|---|---|
| `harbor-rl.reset-isolation` | `simulation.MultiAgentEpisode` | `test_reset_binds_isolated_roles_and_seeded_schedule_without_truth_leakage` | exact role credentials, deterministic order, and distinct authorized projections | implemented |
| `harbor-rl.hard-authorization` | simulation + Session Authority | `test_unauthorized_evidence_attempt_terminates_and_hard_zeros_reward` | cross-seat evidence read is rejected, terminates, and scores zero | implemented |
| `harbor-rl.resolution-menu` | simulation role projection | `test_resolution_phase_exposes_choices_without_the_answer_key` | competing theories become visible at resolution while proof paths, required evidence sets, and correctness markers remain hidden | implemented |
| `harbor-rl.replay-reward` | `simulation.verification` | `test_complete_episode_replays_exactly_and_emits_binary_reward_plus_diagnostics`; `test_edited_arena_trace_fails_replay_and_cannot_retain_reward` | outcome and integrity jointly produce one shared binary reward; explanatory diagnostics survive archive round-trip; edited trace hard-zeros | implemented |
| `harbor-rl.binary-reward` | `simulation.verification` | `test_incorrect_outcome_scores_zero_without_becoming_an_integrity_failure` | an intact but incorrect episode records integrity `1`, outcome `0`, and reward `0` | implemented |
| `harbor-rl.reward-versioning` | `simulation.verification` | `test_reward_v1_archives_keep_their_original_aggregate_semantics` | reward v3 becomes the default without reinterpreting immutable v1 or v2 episodes | implemented |
| `harbor-rl.credit-assignment` | Harbor rollout adapter | `test_each_trainable_role_has_a_separate_token_attributed_rollout` | one trial expands to one token/mask/logprob-bearing rollout per trainable role | implemented |
| `harbor-rl.packaging` | Harbor task adapter | `test_harbor_task_and_trial_artifacts_are_complete_and_offline_verifiable` | frozen Release task plus standard reward, trajectory, attestation, and Session artifacts | implemented |
| `harbor-rl.atif` | Harbor agent adapter | `test_harbor_agent_writes_native_atif_with_global_and_role_local_traces` | native ATIF root preserves global order and embeds one independently valid trace per role | implemented |
| `harbor-rl.concrete-agent` | Harbor agent adapter | `test_concrete_harbor_agent_builds_deterministic_isolated_role_lineup` | Harbor instantiates the arena directly with deterministic, distinct role contexts and heterogeneous model overrides | implemented |
| `harbor-rl.provider-policy` | Harbor LiteLLM adapter | `test_harbor_model_policy_records_safe_rationale_usage_and_exact_tokens` | one real provider boundary emits a structured action, safe rationale, usage, and exact token receipt without persisting private reasoning | implemented |
| `harbor-rl.agent-run` | concrete Harbor arena agent | `test_concrete_harbor_agent_runs_a_complete_isolated_trial_offline` | async isolated policies drive a frozen Release to verified termination and emit artifacts, usage, and native ATIF | implemented |
| `harbor-rl.policy-variable` | arena boundary | `test_policy_behavior_can_change_without_changing_release_or_reward_contract` | changed policy behavior changes trace while Release and reward locks remain exact | implemented |
| `harbor-rl.falsifying-matrix` | `simulation.experiment` | `test_twenty_episode_plan_rotates_four_roles_across_two_model_families` | deterministic 20-episode matrix covers every Seat with both model families; accepted Sybil v5 Release exports as a Harbor 0.20-valid task; live five-context Sol episodes have passed both the historical reward-v1 contract and the current reward-v3 outcome-and-integrity contract | implemented; full fixed-panel reward-v3 difficulty evaluation tracked separately |

## Version 0.22 - Prime hosted multi-agent execution

| Requirement | Owner | Capability test | Evidence | Status |
|---|---|---|---|---|
| `prime-rl.multi-agent` | `narrative_game_prime.NarrativeGameEnv` | `test_prime_runs_one_isolated_interaction_per_role_and_scores_canonical_outcome` | one persistent host interaction and one isolated interaction per Seat produce a replay-verified canonical archive; Prime records the shared binary outcome-and-integrity reward on every trace | implemented |
| `prime-rl.hub-package` | `environments/narrative_game_arena` | `test_prime_hub_package_materializes_its_frozen_release_without_local_paths` | the publishable Prime Hub package contains an exact frozen Release and materializes its task without a caller-local path | implemented |

## Version 0.23 - epistemically valid multi-agent resolution

| Requirement | Owner | Capability test | Evidence | Status |
|---|---|---|---|---|
| `arena.epistemic-lineage` | `simulation.MultiAgentEpisode` | `test_correct_answer_without_acquired_evidence_is_rejected_and_cannot_score` | a policy that names the exact correct theory and proof resources without acquiring them receives no submission and cannot terminate successfully | implemented |
| `arena.facilitator-blindness` | simulation host projection | `test_model_host_receives_facilitator_controls_without_answer_graph` | the model host retains phases, reveal eligibility, and interventions while truth, hypotheses, correctness markers, and proof paths remain absent | implemented |
| `prime-rl.action-framing` | Prime policy adapter | `test_prime_policy_recovers_one_action_object_from_trailing_model_chatter` | the first valid JSON object alone determines the action; trailing provider prose cannot mutate it or crash the episode | implemented |
| `prime-rl.embodied-role-prompt` | Prime policy adapter | `test_prime_runs_one_isolated_interaction_per_role_and_scores_canonical_outcome` | every Seat receives its own stable character identity and conduct boundary in the system prompt while phase knowledge remains in the authorized observation; other characters and answer-key identifiers stay absent | implemented |

## Agentic difficulty implementation — planned

These rows are the ordered handoff from [issue #48](https://github.com/jarredparrett/narrative-game-library/issues/48)
and [the implementation plan](agentic-difficulty-implementation-plan.md). They
are requirements, not claims of current capability. A row remains `planned`
until its implementation, named test, and attributable evidence land together.

### D0 — contract lock and falsifying fixtures

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Handoff #48](https://github.com/jarredparrett/narrative-game-library/issues/48) | `difficulty.d0.contract-lock` | `difficulty.contracts` | normative contract catalog | `test_difficulty_contract_catalog_rejects_unknown_or_changed_normative_versions` | exact content refs for every pinned contract and schema | implemented |
| [Episode evidence #40](https://github.com/jarredparrett/narrative-game-library/issues/40) | `difficulty.d0.semantic-fixtures` | `simulation` + `difficulty.derivations` | missing-rescue and failed-handoff Episodes | `test_first_semantic_fixtures_replay_with_answer_safe_span_addressable_evidence` | replay receipts, Verification Status, and exact view manifests | implemented |

### D1 — evidence spine and portable claims

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d1.evidence-objects` | `workspace` | typed difficulty object closure | `test_difficulty_evidence_objects_are_content_addressed_and_cross_process_identical` | canonical bytes and identical object refs | planned |
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d1.checkpoint` | `workspace` | five-Journal Workspace | `test_checkpoint_pins_verified_heads_without_cross_journal_partial_state` | verified heads and rejected mixed checkpoint | planned |
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d1.claim-manifest` | `workspace` | reportable diagnostic claim | `test_claim_manifest_requires_complete_transitive_objects_schemas_and_verifiers` | exact closure and missing-object rejection | planned |
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d1.portability` | `workspace` | relocated Archive and Claim Capsule | `test_difficulty_archive_and_capsule_verify_offline_after_relocation` | deterministic bytes, import receipt, and offline verification | planned |
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d1.migration` | `workspace` | Workspace `0.1` | `test_workspace_migration_is_append_only_receipted_and_preserves_old_identity` | old/new refs, migrator identity, warnings, and no in-place edits | planned |

### D2 — frozen Instrument and one-Episode analysis

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Instrument #49](https://github.com/jarredparrett/narrative-game-library/issues/49) | `difficulty.d2.instrument-identity` | `difficulty.contracts` | Instrument v1 | `test_instrument_identity_commits_models_prompts_views_tools_schemas_retries_conflicts_and_atlas` | exact Definition/Application refs and drift identities | planned |
| [Authorities #39](https://github.com/jarredparrett/narrative-game-library/issues/39) | `difficulty.d2.evidence-views` | `difficulty.derivations` | all twelve assignments | `test_each_analysis_authority_receives_only_its_content_addressed_evidence_view` | allow/deny audit and Exposure Ledger | planned |
| [Instrument #49](https://github.com/jarredparrett/narrative-game-library/issues/49) | `difficulty.d2.eligibility` | `difficulty.transitions` | nine Instrument eligibility cases | `test_instrument_v1_accepts_reference_lineage_and_rejects_all_nine_boundary_failures` | one eligible and nine attributable results | planned |
| [Instrument #49](https://github.com/jarredparrett/narrative-game-library/issues/49) | `difficulty.d2.attempts` | `experiment.difficulty` | transport, schema, semantic, and best-of attempts | `test_analysis_attempts_preserve_failures_and_forbid_semantic_or_best_of_retry` | complete attempt receipts and fail-closed exhaustion | planned |
| [Discovery #42](https://github.com/jarredparrett/narrative-game-library/issues/42) | `difficulty.d2.real-agent-falsifier` | `experiment.difficulty` | two D0 Episodes | `test_live_instrument_demo_emits_complete_portable_receipts_and_preserves_disagreement` | provider receipts, cited spans, costs, and diagnostic Claim Capsule | planned live evidence |

### D3 — matched measurement and governed scheduling

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Panel identity #38](https://github.com/jarredparrett/narrative-game-library/issues/38) | `difficulty.d3.panel-application` | `difficulty.contracts` + `difficulty.transitions` | matched and drifted Releases | `test_panel_application_preserves_panel_identity_and_reports_every_compatibility_grade` | exact locks, match grade, missing and incompatible assignments | planned |
| [Profiles #47](https://github.com/jarredparrett/narrative-game-library/issues/47) | `difficulty.d3.profile-uncertainty` | `difficulty.derivations` | stratified outcome matrix | `test_profile_keeps_seven_distributions_denominators_and_required_uncertainty_methods` | Wilson and eligible bootstrap receipts; insufficient below threshold | planned |
| [Scheduling #55](https://github.com/jarredparrett/narrative-game-library/issues/55) | `difficulty.d3.sampling-separation` | `difficulty.transitions` | standing plan plus adaptive queue | `test_diagnostic_outcomes_cannot_change_current_standing_membership_or_stop_time` | separate immutable membership and scheduling receipts | planned |
| [Scheduling #55](https://github.com/jarredparrett/narrative-game-library/issues/55) | `difficulty.d3.scheduling` | `experiment.difficulty` + `difficulty.transitions` | competing Evidence Work Packages | `test_scheduler_applies_evidence_cascade_priority_vector_and_stop_states_deterministically` | all alternatives, rejection reasons, selected package, and stop state | planned |
| [Scheduling #55](https://github.com/jarredparrett/narrative-game-library/issues/55) | `difficulty.d3.budget-sealed` | `difficulty.transitions` | protected budgets and sealed handle | `test_standing_and_sealed_budgets_are_protected_and_sealed_cases_remain_opaque` | reservation ledger and allowlisted aggregate receipt | planned |

### D4 — discovery, causal evidence, and Atlas lifecycle

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Discovery #42](https://github.com/jarredparrett/narrative-game-library/issues/42) | `difficulty.d4.discovery` | `experiment.difficulty` + `difficulty.transitions` | complete, partial, and conflicting sweeps | `test_five_truth_blind_sweeps_require_coverage_and_independent_corroboration` | Sweep Coverage, cursors, exclusions, and unresolved signals | planned |
| [Attribution #44](https://github.com/jarredparrett/narrative-game-library/issues/44) | `difficulty.d4.attribution` | `experiment.difficulty` + `difficulty.derivations` | failed-handoff Incident | `test_isolated_attributions_preserve_alternatives_and_require_causal_corroboration` | two hypothesis sets, counterevidence, contrasts, and ownership status | planned |
| [Atlas #45](https://github.com/jarredparrett/narrative-game-library/issues/45) | `difficulty.d4.atlas-promotion` | `difficulty.transitions` | eligible and incomplete class proposals | `test_atlas_promotion_requires_fixtures_rerunnable_measurement_and_independent_review` | Workbench history, review, transition, and immutable Published Atlas | planned |
| [Challenge governance #43](https://github.com/jarredparrett/narrative-game-library/issues/43) | `difficulty.d4.suite-binding` | `difficulty.transitions` | development, challenge, and sealed cases | `test_suite_bindings_are_immutable_one_way_and_sealed_cohorts_are_single_use` | binding receipts and rejected promotion/reuse | planned |

### D5 — failure-driven hardening

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Hardening #50](https://github.com/jarredparrett/narrative-game-library/issues/50) | `difficulty.d5.routing` | `difficulty.transitions` | agent failure, defect, and unresolved evidence | `test_failure_routing_selects_harden_repair_or_quarantine_without_favorable_default` | exact owning-layer and confounder evidence | planned |
| [Hardening #50](https://github.com/jarredparrett/narrative-game-library/issues/50) | `difficulty.d5.state-machine` | `difficulty.transitions` | reference plus rejection matrix | `test_hardening_state_machine_accepts_reference_path_and_rejects_every_named_boundary_case` | thirteen transition receipts and attributable terminal routes | planned |
| [Hardening #50](https://github.com/jarredparrett/narrative-game-library/issues/50) | `difficulty.d5.builder-boundary` | `generation` + `difficulty.contracts` | handoff requirement | `test_builder_receives_answer_safe_requirement_and_existing_generator_produces_one_child` | bounded input, independent receipts, immutable child, and no hidden answer | planned |
| [Hardening #50](https://github.com/jarredparrett/narrative-game-library/issues/50) | `difficulty.d5.preflight` | `generation` + `adapters.verismill` | coherent, leaky, unsolved, and failed-artifact children | `test_challenge_preflight_requires_two_solvers_oracle_leakage_review_and_all_artifact_attestations` | exact gate receipts and quarantine reasons | planned |
| [Profiles #47](https://github.com/jarredparrett/narrative-game-library/issues/47) | `difficulty.d5.matched-comparison` | `difficulty.derivations` + `difficulty.transitions` | baseline, child, and non-manifesting control | `test_target_dominance_requires_matched_uncertainty_movement_control_discrimination_and_no_regression` | Release Comparison with all intervals and hard gates | planned |
| [Hardening #50](https://github.com/jarredparrett/narrative-game-library/issues/50) | `difficulty.d5.full-loop` | repository | real failed-handoff hardening demonstration | `test_real_agent_hardening_demo_closes_lineage_without_fixture_scores` | complete measured Claim Capsule or explicit non-accepting terminal result | planned live evidence |

### D6 — operator surface and release qualification

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Monitor #59](https://github.com/jarredparrett/narrative-game-library/issues/59) | `difficulty.d6.monitor-states` | `experience` + `difficulty.derivations` | current, incomplete, stale, and corrupt Checkpoints | `test_operator_monitor_fails_closed_across_all_freshness_and_completeness_states` | correct conclusions, debt, history, or suppression | planned |
| [Monitor #59](https://github.com/jarredparrett/narrative-game-library/issues/59) | `difficulty.d6.monitor-authority` | `experience` | complete operator projection | `test_operator_monitor_is_read_only_traceable_accessible_and_sealed_safe` | no mutation commands, exact claim links, keyboard/a11y audit, opaque sealed fields | planned |
| [Monitor #59](https://github.com/jarredparrett/narrative-game-library/issues/59) | `difficulty.d6.projection-rebuild` | `experience` + `workspace` | deleted projection | `test_operator_projection_rebuild_is_offline_cross_process_and_claim_preserving` | byte-identical regenerated projection from the same Checkpoint | planned |
| [Persistence #46](https://github.com/jarredparrett/narrative-game-library/issues/46) | `difficulty.d6.release-capsule` | `workspace` + repository | relocated full-loop Claim Capsule | `test_release_capsule_contains_exact_verifier_and_rechecks_every_reportable_claim_offline` | verifier bundle, component lock, complete closure, and reproducibility status | planned |
