"""Stage 12 public-release qualification capability tests."""

from dataclasses import replace
from types import SimpleNamespace

from narrative_game.climb import Authority, StandingAttestation, TrialBinding
from narrative_game.release import (
    PUBLIC_RELEASE_GATES,
    PublicReleasePolicy,
    PublisherApproval,
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


def accepted_fixture():
    binding = TrialBinding(CANDIDATE, RELEASE, H, H, H, H, H, {
        "package.verify": True,
    })
    standing = StandingAttestation(
        CANDIDATE, "accepted", (H,),
        ("fresh-human-play", "independent-standing-review", "model-human-comparison"),
        "reviewer", "accepted after exact human play", ("run-1", "run-2"), H,
    )
    authorities = (
        Authority("reviewer", "human", "reviewer", "reviewer-principal"),
        Authority("publisher", "human", "publisher", "publisher-principal"),
        Authority("player-1", "human", "participant", "player-principal"),
        Authority("host", "human", "facilitator", "host-principal"),
    )
    runs = tuple(
        SimpleNamespace(
            run_id=f"run-{index}", participant_authority_ids=("player-1",),
            facilitator_authority_id="host", observer_authority_ids=(),
        )
        for index in (1, 2)
    )
    snapshot = {
        "trial_bindings": (binding,), "standings": (standing,),
        "authorities": authorities, "playtest_runs": runs,
    }
    policy = PublicReleasePolicy()
    packages = {"sdist": H, "wheel": H}
    approval = PublisherApproval(
        policy.policy_id, "1.0.0", CANDIDATE, standing.attestation_id,
        "publisher", packages, H,
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
        approval,
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
        "stage10.accepted-human-standing", "stage10.independent-verification",
        "stage11.creator-player-print", "stage12.tagged-upstreams",
        "stage12.compatibility", "stage12.support-matrix",
        "stage12.package-artifacts", "stage12.documentation",
        "stage12.known-limitations", "stage12.publisher-approval",
    )
    assert policy.policy_id.startswith("release-policy:")


def test_portable_experiment_gate_requires_verified_exact_package_binding():
    """release.stage8.portable-experiment: failed verification blocks release."""
    experiment, evidence = accepted_fixture()
    experiment.ok = False
    assert not gate(qualify(experiment, evidence), "stage8.portable-experiment").passed


def test_reusable_authoring_gate_requires_content_addressed_proof():
    """release.stage9.reusable-authoring: Blueprint/adapter proof must be exact."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, authoring_proof_ref="missing"))
    assert not gate(report, "stage9.reusable-authoring").passed


def test_human_standing_gate_cannot_be_satisfied_by_build_or_model_evidence():
    """release.stage10.accepted-human-standing: accepted Playtest Standing is required."""
    experiment, evidence = accepted_fixture()
    experiment.ledger.value["standings"] = ()
    assert not gate(qualify(experiment, evidence), "stage10.accepted-human-standing").passed


def test_independent_verification_gate_excludes_the_playtest_roster():
    """release.stage10.independent-verification: the standing reviewer did not play."""
    experiment, evidence = accepted_fixture()
    standing = experiment.ledger.value["standings"][0]
    experiment.ledger.value["authorities"] += (
        Authority("player-reviewer", "human", "reviewer", "same-person"),
    )
    experiment.ledger.value["standings"] = (replace(standing, reviewer_authority_id="player-1"),)
    assert not gate(qualify(experiment, evidence), "stage10.independent-verification").passed


def test_creator_player_print_gate_requires_one_exact_lineage_proof():
    """release.stage11.creator-player-print: all experience projections share exact proof."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, experience_proof_ref="missing"))
    assert not gate(report, "stage11.creator-player-print").passed


def test_tagged_upstream_gate_rejects_git_and_commit_pins():
    """release.stage12.tagged-upstreams: public dependencies are released versions."""
    experiment, evidence = accepted_fixture()
    evidence = replace(evidence, upstream_versions={
        "verismill": "git+https://example.test/repo@abc", "mattermill": "1.0.0",
    })
    assert not gate(qualify(experiment, evidence), "stage12.tagged-upstreams").passed


def test_compatibility_gate_requires_stable_epoch_and_exact_policy():
    """release.stage12.compatibility: experimental schema promises cannot qualify."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, contract_epoch="experimental"))
    assert not gate(report, "stage12.compatibility").passed


def test_support_matrix_gate_requires_exact_receipt_for_each_supported_python():
    """release.stage12.support-matrix: every promised interpreter is verified."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, test_receipts={"3.11": H}))
    assert not gate(report, "stage12.support-matrix").passed


def test_package_gate_requires_exact_sdist_and_wheel_refs():
    """release.stage12.package-artifacts: both public distributions are exact."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, package_artifact_refs={"wheel": H}))
    assert not gate(report, "stage12.package-artifacts").passed


def test_documentation_gate_requires_every_public_entry_path():
    """release.stage12.documentation: quickstart through limitations are published."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, documentation_refs={"quickstart": H}))
    assert not gate(report, "stage12.documentation").passed


def test_limitations_gate_makes_debt_visible_without_upgrading_standing():
    """release.stage12.known-limitations: an empty disclosure cannot qualify."""
    experiment, evidence = accepted_fixture()
    report = qualify(experiment, replace(evidence, known_limitations=()))
    assert not gate(report, "stage12.known-limitations").passed


def test_publisher_gate_requires_distinct_human_approval_over_exact_refs():
    """release.stage12.publisher-approval: CI or the standing reviewer cannot publish."""
    experiment, evidence = accepted_fixture()
    approval = replace(evidence.publisher_approval, publisher_authority_id="reviewer")
    report = qualify(experiment, replace(evidence, publisher_approval=approval))
    assert not gate(report, "stage12.publisher-approval").passed


def test_all_twelve_gates_are_required_and_report_identity_is_deterministic():
    """release.qualification: no partial pass is called a public release."""
    experiment, evidence = accepted_fixture()
    first = qualify(experiment, evidence)
    second = qualify(experiment, ReleaseEvidence.from_mapping(evidence.to_mapping()))
    assert first.status == "qualified"
    assert len(first.gates) == 12
    assert all(item.passed for item in first.gates)
    assert first.to_mapping() == second.to_mapping()


def test_dangling_or_corrupt_hash_strings_are_not_evidence():
    """release.evidence-availability: every claimed ref is rehashed from supplied bytes."""
    experiment, evidence = accepted_fixture()
    report = qualify_public_release(
        experiment, evidence, evidence_objects={H: b"different bytes"}
    )
    assert report.status == "not_qualified"
    assert not gate(report, "stage12.package-artifacts").passed
