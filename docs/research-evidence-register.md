# Research evidence register

This register records the approved research principles that directly support
Stage 2 requirements. It records provenance and scope; it does not copy source
material or claim that any one source establishes a universal numeric rule.

| Requirement | Source provenance | Extracted principle | Stage 2 scope | Capability evidence |
|---|---|---|---|---|
| `stage2.proof-redundancy` | [GUMSHOE SRD](https://pelgranepress.com/nas/content/live/pelgranepress/wp-content/uploads/2013/10/GUMSHOE-SRD-CC-v2.pdf); [Three Clue Rule](https://thealexandrian.net/wordpress/1101/roleplaying-games/three-clue-rule-part-3-the-three-clue-rule) | Critical investigative progress needs independent evidence routes; no universal clue count is asserted. | A resolution cannot depend on only one declared Proof Path. | `test_defect_single_point_proof_failure_names_the_only_path` |
| `stage2.canonical-owner` | [Overboard! postmortem](https://www.gamedeveloper.com/design/how-get-away-murder-overboard); [Changeable Minds](https://www.gamedeveloper.com/design/changeable-minds) | World truth and character knowledge/belief must remain separate and revisable. | Claim factuality derives from one Truth Model; intent derives separately from Character Belief. | `test_derived_views_read_one_truth_and_access_owner` |
| `stage2.reveal-timing` | [The Burden of Proof](https://www.gdcvault.com/play/1027723/The-Burden-of-Proof-Narrative) | Investigation should assemble an explicit case, not expose a culprit field or accept a guess. | An acceptable Proof Path cannot be complete before its Resolution Phase. | `test_defect_premature_proof_names_early_paths` |
| `stage2.participation` | [Freeform Games player guide](https://www.freeformgames.com/pdf/playing_a_murder_mystery_game.pdf) | Characters need beliefs, goals, and information that support active unscripted play. | Every supported Seat has a Character, Objective, and evidence opportunity. | `test_defect_inactive_seat_names_the_stranded_seat` |
| `stage2.recovery` | [Ask Why](https://scottnicholson.com/pubs/askwhy.pdf); [escape-room survey](https://scottnicholson.com/pubs/erfacwhite.pdf) | Integrated hints and recovery protect progression without replacing the fiction. | A host has an explicit hint/recovery route into the proof graph. | `test_defect_unrecoverable_progression_quotes_missing_host_power` |
| `stage2.critical-access` | [Facilitated Investigation decision](https://github.com/jarredparrett/verismill-lean/issues/17) | Optional structure cannot strand required information or supported participants. | Every acceptable Proof Path's evidence can reach a supported Seat by resolution. | `test_defect_inaccessible_critical_evidence_names_the_evidence` |
| `stage2.authorization` | [Canonical ownership decision](https://github.com/jarredparrett/verismill-lean/issues/14) | Narrative disclosure may narrow, never expand, Kernel authorization. | Reveal audiences are a subset of the Resource's Access Policy. | `test_defect_unauthorized_disclosure_names_forbidden_seat` |
| `stage2.contradictory-truth` | [Canonical ownership decision](https://github.com/jarredparrett/verismill-lean/issues/14) | One immutable game version has one canonical assignment per Proposition. | Conflicting Truth assignments are blockers with the exact values quoted. | `test_defect_contradictory_truth_quotes_both_assignments` |

Later stages append rather than reinterpret entries. Human play evidence remains
first-order evidence under the separate standing policy.
