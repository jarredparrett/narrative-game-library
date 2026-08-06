# Extending the library

Extend the smallest owner that can express the new behavior. Do not add
genre-specific exceptions to the Kernel.

## Add a game profile

Define profile validation and a versioned `GameProfileAdapter`. The adapter
turns profile-owned blueprint data into a Complete Package and interprets typed
authoring operations. Freeze its ID and version in the Experiment Plan. A
different adapter version is a different experiment contract.

## Add a document capability

Request artifacts through the public Verismill Artifact Forge adapter. Add or
hill-climb the Mattermill emitter in Verismill, then consume the exact artifact
bytes and Artifact Attestation. Game code must not import Mattermill or inspect
Verismill's private object store or trace bus.

## Add a delivery surface

Consume maker, host, authorized player, print, or tutorial projections. Keep
canonical truth, access policy, commands, and Session mutation in the library.
An application may render or transport projections; it must not become a
second game engine.

## Acceptance pattern

1. Name the owning contract and requirement.
2. Add one attributable capability test.
3. Preserve seeded, offline, cross-process determinism.
4. Build a complete package and replay every affected hard gate.
5. Let agents propose changes; require human approval for canonical transitions.
6. Measure the child under the unchanged Instrument before selecting it.
7. State Standing only at the evidence tier actually earned.

Facilitated Investigation is the first proven profile. New genres should prove
the adapter pattern before asking the Kernel to own new concepts.
