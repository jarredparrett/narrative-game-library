# Character Program is canonical, not prompt memory

- Status: accepted
- Date: 2026-08-06

## Context

Long-form characters need private history, beliefs, objectives, reveal windows, and phase choices. If those details live only in an agent prompt, they cannot be validated for leakage, replayed after human direction, rendered consistently to print and web, or compared across a hill climb.

## Decision

An optional `CharacterProgram` is embedded in the canonical `GameDefinition`. It owns one `Dossier` per supported Seat, explicit Knowledge Boundaries, phase Moves, Reveal Paths, and ending choices. Agents and humans occupy the same Seat contract. Their evolving Character State is recorded by Session Authority; it never changes canonical truth.

## Consequences

The compiler can project the same Dossier to Markdown, PDF, and a seat-private web view. Validation can reject unauthorized knowledge, unavailable evidence, missing relationships, unreachable secrets, and dead-end phase states before release. The tradeoff is a larger canonical game object and an explicit migration for games that opt into deep characters; games without a Character Program remain byte-compatible.
