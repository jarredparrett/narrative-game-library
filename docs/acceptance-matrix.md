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
| [Stage 8 implementation](https://github.com/jarredparrett/narrative-game-library/issues/6) | `stage8.profile-adapter` | `experiment.GameProfileAdapter` | fixture investigation profile | `test_profile_adapter_builds_answer_safe_proposal_but_human_moves_branch` | profile builds and revises; Proposal remains inert until exact human Review | accepted 2026-08-05 |
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
