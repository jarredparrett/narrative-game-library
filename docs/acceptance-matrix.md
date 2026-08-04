# Acceptance matrix

Every accepted requirement links its source decision to an owning package,
fixture, capability test, and evidence. Agents may assemble this evidence; a
human Stage Reviewer decides whether the gate is accepted.

## Stage 0 — dependency-boundary spike

| Source | Requirement | Owner | Fixture | Capability test | Evidence | Status |
|---|---|---|---|---|---|---|
| [Verismill integration boundary](https://github.com/jarredparrett/verismill-lean/issues/6) | `stage0.public-forge` | `adapters.verismill` | Stage 0 deed | `test_public_artifact_forge_is_seeded_verified_and_offline` | exact Artifact Result and Attestation | implemented; human gate pending |
| [Compilation determinism](https://github.com/jarredparrett/verismill-lean/issues/8) | `stage0.cross-process` | `contracts.canonical` | Stage 0 deed | `test_stage0_fixture_is_byte_identical_across_processes` | matching artifact, manifest, request, and attestation hashes | implemented; human gate pending |
| [Package architecture](https://github.com/jarredparrett/verismill-lean/issues/7) | `stage0.import-boundary` | repository | adapter source | `test_verismill_adapter_has_no_private_or_mattermill_imports` | AST import audit | implemented; human gate pending |
| [Implementation gates](https://github.com/jarredparrett/verismill-lean/issues/13) | `stage0.clean-build` | repository | locked environment | CI plus isolated offline run | source/wheel build and frozen-lock installation | implemented; human gate pending |

Later stages append rows rather than replacing this evidence.
