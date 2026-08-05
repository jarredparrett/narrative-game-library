# Separate experiment orchestration from game-profile authoring

An Experiment owns one persisted plan, authority graph, evidence lineage,
human gate, and frozen selection process. A versioned Game Profile Adapter owns
how domain authoring data becomes a Complete Package and how builder output
becomes a proposed revision. We chose this boundary over profile conditionals
inside the orchestrator so new genres, accounting games, or insurance cases can
reuse the measured climb without changing its evidence and authority semantics;
changing adapter identity is therefore an explicit Experiment-contract change.
