"""Stage 12 public-release qualification capability tests."""

from dataclasses import replace
from types import SimpleNamespace

from narrative_game.climb import Authority, StandingAttestation, TrialBinding
from narrative_game.release import (
    PUBLIC_RELEASE_GATES,
    PublicReleasePolicy,
    ReleaseAttestation,
    ReleaseEvidence,
    qualify_public_release,
)
from narrative_game.contracts import digest_bytes


OBJECT = b"exact release evidence"
H = digest_bytes(OBJECT)
CANDIDATE = "sha256:" + "2" * 64
RELEASE = "sha256:" + "3" * 64


class Ledger:
    def __init__(self, snapshot):
        self.value = snapshot

    def snapshot(self):
        return self.value


class FakeExperiment:
    def __init__(self, snapshot, *, ok=True):
        self.ledger = Ledger(snapshot)
        self.ok = ok

    def verify(self):
        return {"ok": self.ok}


def qualified_fixture():
    binding = TrialBinding(CANDIDATE, RELEASE, H, H, H, H, H, {
        "package.verify": True,
    })
    evaluations = tuple(
        SimpleNamespace(
            evaluation_id=f"evaluation-{index}", candidate_id=CANDIDATE,
            instrument_id="instrument-1", mode="blind", outcome="pass",
            judge_authority_ids=(f"judge-{index}",),
        )
        for index in (1, 2)
    )
    standing = StandingAttestation(
        CANDIDATE, "machine_qualified",
        tuple(item.evaluation_id for item in evaluations),
        ("model-blind-panel", "independent-agentic-review"),
        "standing-reviewer",
        "Two independent blind panels passed; an independent agent verified the claim.",
    )
    authorities = (
        Authority("judge-1", "agent", "judge", "judge-principal-1"),
        Authority("judge-2", "agent", "judge", "judge-principal-2"),
        Authority("builder", "agent", "builder", "builder-principal"),
        Authority("standing-reviewer", "agent", "reviewer", "standing-review-principal"),
        Authority("release-reviewer", "agent", "release-reviewer", "release-review-principal"),
    )
    release_receipt = SimpleNamespace(
        receipt_id="release-receipt", authority_id="release-reviewer",
        role="release-reviewer", parsed_output_ref=H,
    )
    snapshot = {
        "trial_bindings": (binding,), "standings": (standing,),
        "authorities": authorities, "evaluations": evaluations,
        "model_receipts": (release_receipt,),
        "proposals": (SimpleNamespace(builder_authority_id="builder"),),
    }
    policy = PublicReleasePolicy()
    packages = {"sdist": H, "wheel": H}
    attestation = ReleaseAttestation(
        policy.policy_id, "1.0.0", CANDIDATE, standing.attestation_id,
        "release-reviewer", release_receipt.receipt_id, packages, H,
    )
    evidence = ReleaseEvidence(
        "1.0.0", "1", CANDIDATE, RELEASE, H, H,
        {"verismill": "1.0.0", "mattermill": "1.0.0"},
        {"3.11": H, "3.13": H}, packages,
        {
            "quickstart": H, "tutorial": H, "extension-guide": H,
            "release-policy": H, "known-limitations": H,
        },
        ("first public version supports Facilitated Investigation only",), H,
        attestation,
    )
    return FakeExperiment(snapshot), evidence


def gate(report, code):
    return next(item for item in report.gates if item.code == code)


def qualify(experiment, evidence):
    return qualify_public_release(experiment, evidence, evidence_objects={H: OBJECT})


def test_policy_freezes_one_owned_gate_for_every_stage_8_through_12_requirement():
    """release.policy: exact gate order and owners are content-addressed."""
    policy = PublicReleasePolicy()
    assert policy.gates == PUBLIC_RELEASE_GATES
    assert tuple(item.code for item in policy.gates) == (
        "stage8.portable-experiment", "stage9.reusable-authoring",
        "stage10.agentic-standing", "stage10.independent-agentic-verification",
        "stage11.creator-player-print", "stage12.tagged-upstreams",
        "stage12.compatibility", "stage12.support-matrix",
        "stage12.package-artifacts", "stage12.documentation",
        "stage12.known-limitations", "stage12.release-attestation",
    )
    assert policy.version == "2.0.0"
    assert policy.policy_id.startswith("release-policy:")


def test_portable_experiment_gate_requires_verified_exact_package_binding():
    """release.stage8.portable-experiment: failed verification blocks release."""
    experiment, evidence = qualified_fixture()
    experiment.ok = False
    assert not gate(qualify(experiment, evidence), "stage8.portable-experiment").passed


def test_reusable_authoring_gate_requires_content_addressed_proof():
    """release.stage9.reusable-authoring: Blueprint/adapter proof must be exact."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, authoring_proof_ref="missing"))
    assert not gate(report, "stage9.reusable-authoring").passed


def test_agentic_standing_requires_two_passing_blind_evaluations():
    """release.stage10.agentic-standing: one panel cannot self-corroborate."""
    experiment, evidence = qualified_fixture()
    standing = experiment.ledger.value["standings"][0]
    experiment.ledger.value["standings"] = (
        replace(standing, evaluation_ids=(standing.evaluation_ids[0],)),
    )
    assert not gate(qualify(experiment, evidence), "stage10.agentic-standing").passed
    experiment, evidence = qualified_fixture()
    experiment.ledger.value["authorities"] = tuple(
        replace(item, principal="judge-principal-1")
        if item.authority_id == "judge-2" else item
        for item in experiment.ledger.value["authorities"]
    )
    assert not gate(qualify(experiment, evidence), "stage10.agentic-standing").passed


def test_independent_agentic_verification_excludes_judge_principals():
    """release.stage10.independent-agentic-verification: a judge cannot review its panel."""
    experiment, evidence = qualified_fixture()
    authorities = tuple(
        replace(item, principal="judge-principal-1")
        if item.authority_id == "standing-reviewer" else item
        for item in experiment.ledger.value["authorities"]
    )
    experiment.ledger.value["authorities"] = authorities
    assert not gate(
        qualify(experiment, evidence), "stage10.independent-agentic-verification"
    ).passed


def test_creator_player_print_gate_requires_one_exact_lineage_proof():
    """release.stage11.creator-player-print: all experience projections share exact proof."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, experience_proof_ref="missing"))
    assert not gate(report, "stage11.creator-player-print").passed


def test_tagged_upstream_gate_rejects_git_and_commit_pins():
    """release.stage12.tagged-upstreams: public dependencies are released versions."""
    experiment, evidence = qualified_fixture()
    evidence = replace(evidence, upstream_versions={
        "verismill": "git+https://example.test/repo@abc", "mattermill": "1.0.0",
    })
    assert not gate(qualify(experiment, evidence), "stage12.tagged-upstreams").passed


def test_compatibility_gate_requires_stable_epoch_and_exact_policy():
    """release.stage12.compatibility: experimental schema promises cannot qualify."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, contract_epoch="experimental"))
    assert not gate(report, "stage12.compatibility").passed


def test_support_matrix_gate_requires_exact_receipt_for_each_supported_python():
    """release.stage12.support-matrix: every promised interpreter is verified."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, test_receipts={"3.11": H}))
    assert not gate(report, "stage12.support-matrix").passed


def test_package_gate_requires_exact_sdist_and_wheel_refs():
    """release.stage12.package-artifacts: both public distributions are exact."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, package_artifact_refs={"wheel": H}))
    assert not gate(report, "stage12.package-artifacts").passed


def test_documentation_gate_requires_every_public_entry_path():
    """release.stage12.documentation: quickstart through limitations are published."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, documentation_refs={"quickstart": H}))
    assert not gate(report, "stage12.documentation").passed


def test_limitations_gate_makes_debt_visible_without_upgrading_standing():
    """release.stage12.known-limitations: an empty disclosure cannot qualify."""
    experiment, evidence = qualified_fixture()
    report = qualify(experiment, replace(evidence, known_limitations=()))
    assert not gate(report, "stage12.known-limitations").passed


def test_release_attestation_requires_distinct_agent_and_exact_model_receipt():
    """release.stage12.release-attestation: builders, judges, and bare CI cannot release."""
    experiment, evidence = qualified_fixture()
    experiment.ledger.value["authorities"] = tuple(
        replace(item, principal="builder-principal")
        if item.authority_id == "release-reviewer" else item
        for item in experiment.ledger.value["authorities"]
    )
    report = qualify(experiment, evidence)
    assert not gate(report, "stage12.release-attestation").passed
    experiment, evidence = qualified_fixture()
    attestation = replace(evidence.release_attestation, model_receipt_id="missing")
    report = qualify(experiment, replace(evidence, release_attestation=attestation))
    assert not gate(report, "stage12.release-attestation").passed


def test_human_play_is_optional_evidence_not_a_release_gate():
    """release.human-optionality: no human object is required for agentic qualification."""
    experiment, evidence = qualified_fixture()
    assert "playtest_runs" not in experiment.ledger.value
    assert qualify(experiment, evidence).status == "qualified"


def test_all_twelve_gates_are_required_and_report_identity_is_deterministic():
    """release.qualification: no partial pass is called a public release."""
    experiment, evidence = qualified_fixture()
    first = qualify(experiment, evidence)
    second = qualify(experiment, ReleaseEvidence.from_mapping(evidence.to_mapping()))
    assert first.status == "qualified"
    assert len(first.gates) == 12
    assert all(item.passed for item in first.gates)
    assert first.to_mapping() == second.to_mapping()


def test_dangling_or_corrupt_hash_strings_are_not_evidence():
    """release.evidence-availability: every claimed ref is rehashed from supplied bytes."""
    experiment, evidence = qualified_fixture()
    report = qualify_public_release(
        experiment, evidence, evidence_objects={H: b"different bytes"}
    )
    assert report.status == "not_qualified"
    assert not gate(report, "stage12.package-artifacts").passed
