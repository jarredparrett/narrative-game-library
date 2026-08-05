# A Game Blueprint wraps rather than replaces the canonical Game Definition

Stage 9 adds rich-text Materials, Arc Beats, and typed Authoring Operations in
an editable Game Blueprint, while world truth, Characters, Evidence, Reveals,
and resolution remain owned by the existing Game Definition. This avoids two
competing truth models and lets authored text derive Resource hashes by
construction; the trade-off is that profile adapters must translate and
validate Blueprint intent before the unchanged deterministic compiler can
freeze a Candidate.
