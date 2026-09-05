# 17 — Teacher brain: Levantine (Palestinian) Arabic for an English-speaking adult (living document)

Started 2026-09-05 at Medi's request ("become an expert Levantine Arabic teacher; learn the lesson plans, the common grammar lessons, what is hardest for English speakers; keep a teacher brain document"). This page is the brain. It grows every session; every rule that changes what Anees flags must also land in `docs/data/ai_rules.json`.

Status of this version: **seed**. Section A is grounded in Amal's own materials (her two Docs and the Sep-4 lesson). Sections B–D are my teacher knowledge and need a research pass with sources (planned: next session, fresh chat). Nothing below overrides Amal; where she and a textbook differ, Amal wins (rule A2).

## A. What Amal actually teaches (ground truth)

Sources: vocabulary Doc (2,120 words, 20 topics), "Arabic Materials" Doc (snapshot `data/vocab/grammar_materials_2026-09-05.md`), lessons Aug 25 and Sep 4.

| Amal's unit | Her rule in one line | Anees rule |
|---|---|---|
| Prepositions min / 3ala / fi / ma3 / bi / la | each has 2–4 core functions; adjectives usually take *min* (5aayef minnak), 2al2aan + 3ala, mishtaa2 + la, mu5talef + 3an | prepositions with verbs are a homework focus (Sep 4: "enbasa6ti **bi/fi** el-7afle") |
| Noun possessives (idafa) | thing + owner, no "of"; first noun never takes el-; feminine first noun adds -t; last noun decides definiteness | word-choice slips on el- are `article` grammar (M2) |
| Noun + adjective | adjective after noun; el- on noun only = a statement; el- on both = a defined phrase | `article` / `gender` grammar kinds |
| Time and clock | el-saa3a + feminine number; u + minutes; rube3 / noss / ella rube3; singular / dual / plural of minute, second, hour | numbers topic |
| Emotions / adjectives + bakoon | no "to be" in plain present (ana ta3baan); bakoon / ykoon for habit, future, and **conditional after lamma / iza** | **M6 (Medi's hard one)**: "lamma akun za3lan" vs "ana za3lan" |
| Kul | kul + el- = all; kul without el- = every | article |
| b-prefix elimination | drop b- after biddi / laazim / mumkin, after abel-ma / ba3ed-ma / lamma / ra7, after la- / 3ashaan, on the second verb of a pair, and through u / wala / aw chains; keep it after enno | candidate `tense` slip; Sep 4 drill "lamma **ne6la3**" |
| Pointer rule (resumptive pronoun) | object first → verb needs -o / -ha: aktar eshi basawwi**h**, ay 7ada bashuf**o** | Sep 4 chat "aktar ishi" moment |
| Verb families | past tense from present (Doc: 478 + 241 rows), command tense (107), causative vs. reflexive: **babse6** (I make happy) vs **banbese6** (I become happy) | Sep 4 new words; N1 |

Lesson shape observed (Sep 4, 65 min): one verb family drilled through all persons, present then past then command; English explanation, Amal models, Medi repeats, Amal types the form in chat; frequent code-switching; corrections by recast (she repeats the right form) more than by "la".

## B. The usual Levantine syllabus (what most courses teach, in order)

Typical sequence in Levantine textbooks and tutor curricula (to be sourced next session):
1. Sounds and Arabizi: ع 3, ح 7, ق 2 (glottal in Palestinian urban), غ 8, خ 5, ط 6, ص 9; long vs short vowels; stress.
2. Greetings, pleasantries, introductions; pronouns (ana, inta/inti, huwwe/hiyye, i7na, intu, humme).
3. Nominal sentences with no "to be"; gender of nouns (-a/-e feminine); adjective agreement.
4. Definiteness (el-) and the idafa (possessive) construction; possessive suffixes (-i, -ak/-ki, -o/-ha, -na, -kom, -hom).
5. Demonstratives (hada / hadi / hadol), questions (shu, wein, keef, leish, meen, ay, qaddaish).
6. Numbers 1–10 (with the dual and the 3–10 plural rule), 11–100, time, days.
7. Present tense with b-; negation ma … / mish; "there is" fi / ma fi.
8. b-drop after modal and time words (biddi, laazem, mumkin, lamma, ra7); future with ra7 / rah.
9. Past tense; kaan for past states; kaan + b-verb for habitual past.
10. Object pronoun suffixes on verbs and prepositions (shufto, ma3i, 3aleik).
11. Command and negative command; plurals (sound -een / -aat and broken plurals); comparatives and superlatives (aktar, a7san + pointer).
12. Relative clause with illi; conditional with iza / lamma; ykoon / bakoon for states.

## C. What is hardest for English speakers (teacher experience; to be sourced)

Ranked by how often adult English speakers get it wrong in speech, and mapped to Medi's evidence:

| Rank | Difficulty | Why it is hard for English speakers | Seen in Medi's lessons? |
|---|---|---|---|
| 1 | b-prefix: when to drop it | English has one present form; Arabic switches mood after modals, time words and purpose words | yes: drills with lamma / laazem (Sep 4, Aug 25) |
| 2 | ykoon / kaan for states | English always says "am / is"; Arabic omits it in the present and needs it for habit, future, condition | yes, Medi named it (M6) |
| 3 | Definiteness and idafa | "the" behaves differently: el- on the second noun only; "my friend's book" reverses order | article slips (Aug 25 el- discussions) |
| 4 | Gender agreement on adjectives and verbs (-i for inti, -at past feminine) | English adjectives do not agree | yes: hadi/hada el-fi3l self-repair (Sep 4 clip 19) |
| 5 | Pointer / resumptive pronoun | English leaves the gap ("the thing I do") | yes: aktar ishi (Sep 4) |
| 6 | Verb form families (I make X happy vs I become happy; causative vs reflexive) | one English verb maps to two Arabic patterns | yes: babse6 / banbese6 (Sep 4, the whole lesson) |
| 7 | Pharyngeal and emphatic consonants (ع ح ق غ خ ط ص) and vowel length | no English equivalents; ع dropped ("nitla" for ne6la3, Sep 4 clip 18) | yes |
| 8 | Numbers with nouns (dual; 3–10 + plural; 11+ + singular) | English is regular | not yet drilled |
| 9 | Prepositions chosen by the verb or adjective (5aayef **min**, mishtaa2 **la**) | arbitrary from the English side | yes: bi/fi el-7afle |
| 10 | Word order and topic-first sentences (object first, pointer after) | English is fixed SVO | partly |

Retrieval pauses are **not** on this list on purpose: Medi builds the whole sentence before speaking (rule M7).

## D. How Anees should use this brain

- The miss classifier should know the pattern behind each difficulty (b-drop context words, ykoon triggers lamma/iza, idafa shape, agreement endings, pointer triggers aktar/a7san/ay/kul) so a slip is named by its grammar, not just "wrong".
- The planner's grammar topics should map to these units; the after-link's "wrong grammar" tap should offer the unit name.
- Each unit gets a one-line Arabizi rule and one Amal example for the Grammar tab (already there for Amal's units; the rest after the research pass).

## E. Next research pass (fresh chat)

Sources to read and cite: Amal's two Docs; wiki 02 (teaching methods) and 05 (Palestinian specifics); a Levantine textbook syllabus (e.g. the Georgetown / Lingualism / Cowell grammar tables of contents); ACTFL-style error studies for English L1 learners of Arabic; Maknuune for Palestinian forms. Output: fill B and C with sources, add a "lesson plan library" with 10 ready 60-minute plans that follow Amal's shape, and turn the C table into classifier patterns.
