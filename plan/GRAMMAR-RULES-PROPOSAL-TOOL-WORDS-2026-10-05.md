# Proposal: the Oct 2 tool words as grammar rules (2026-10-05)

Medi 2026-10-05: "I need you to build a proposal on these on how to write them in our grammar rules and send them for review with letter number categories for Amal".

Family A = the noun phrase (A1 el-, A2 idafa, ... A12). Next free numbers: A13-A17. kul is already A11, so it gets one added line, not a new number.

| Id | Rule (one line) | Pattern | Bullets | Lesson examples |
|---|---|---|---|---|
| A13 | awal + noun = first; awal + el- + noun = the beginning of; after the noun: el-noun el-awal / el-oola (matches gender) | awal + noun = first  |  awal + el- + noun = the beginning of  |  el- + noun + el-awal / el-oola = the first | 4 | 5 |
| A14 | taani + noun = second; noun + taani = another / the second; el-noun el-taani / el-tanye; taani never takes el- in front | taani + noun = second  |  noun + taani = another / second  |  el- + noun + el-taani = the second | 3 | 6 |
| A15 | aa5er + noun = last; aa5er + el- + noun = the end of; after the noun the adjective a5eer / a5eera / a5eeraat | aa5er + noun = last  |  aa5er + el- + noun = the end of  |  el- + noun + el-a5eer / el-a5eera = the last | 3 | 6 |
| A16 | 8eir + noun = other / different; 8eir never takes el- in front; after the noun is rare | 8eir + noun (no el-) | 3 | 5 |
| A17 | nafs + el- + noun = the same ...; never el- before nafs; nafs is never an adjective after the noun | nafs + el- + noun | 3 | 4 |
| A11 (add) | kul + noun = every; kul + el- + noun = all / the whole; el-kull = everyone (new line for A11) | kul + noun = every  |  kul + el- + noun = all / the whole  |  el-kull = everyone | 3 | 4 |

Where it went:
- docs/data/grammar-proposals.json: P-A13 .. P-A17 + P-A11-add, medi pending, amal pending (the Grammar console shows proposals there).
- docs/amal/grammar-rules.html: a 'Proposed rules from the Oct 2 lesson' section, one card per rule with its bullets and the minute-stamped examples; Amal writes yes / the fix in the note box under each (her Tutor page > Grammar tab, rule ids P-A13 ...).
- Nothing is scored on these until Medi says yes and the detector gets a pattern for each (GR-18 / GR-23 path: proposals -> buckets).

Open: Medi says yes / change per rule; then the bucket definitions (docs/data/grammar-buckets.json) and detect_grammar_usage patterns are written.
