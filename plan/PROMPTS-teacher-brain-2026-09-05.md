# Teacher-brain research: the three prompts (2026-09-05)

Run 1 and 2 in parallel (two fresh chats), then 3.

## 1 · Claude (fresh chat in C:\dev\anees)

Read plan/HANDOFF-2026-09-05.md, the memory index, wiki/17-teacher-brain-levantine-arabic.md, data/vocab/grammar_materials_2026-09-05.md and docs/data/ai_rules.json. Then do the research pass in wiki/17 section E:

Goal: make wiki/17 the brain of an expert Levantine (Palestinian) Arabic teacher for one adult English-speaking learner (Medi, tutor Amal, one 60–70 min lesson a week over Google Meet). Deliverables, all inside wiki/17:
1. Section B "usual syllabus": the order most Levantine courses teach, with the source for each claim (textbook tables of contents, tutor curricula, university syllabi). Mark what Amal has already covered from her two Docs.
2. Section C "hardest for English speakers": the ten hardest points, ranked, each with at least one cited source (learner-error studies, teacher guides, textbooks) and the exact place it showed up in Medi's lessons (use data/lessons/*/understanding.json and the clips).
3. A lesson-plan library: ten ready 60-minute plans that follow Amal's observed shape (English explanation → Amal models → Medi repeats → Amal types the form in chat → drill through persons → conversation). Each plan names its grammar unit, 10–15 target words drawn from the Doc, three example sentences in short/medium/long, and the likely mistakes to listen for.
4. Classifier patterns: for each hard point, the trigger words and shapes Anees can detect in a transcript (for example: ykoon required after lamma/iza + adjective; b- must drop after biddi/laazem/mumkin/lamma/ra7/la-/3ashaan; pointer pronoun required after aktar/a7san/ay/kul + verb). Write them as rows that could be added to docs/data/ai_rules.json (id, rule, why, where, status planned).
5. A short "what Amal teaches that textbooks do not" list, and the reverse.
Standard of proof: Amal's Docs beat any textbook; cite every outside claim with a URL; separate "sourced" from "my teacher judgment"; no invented Arabic (every example either comes from Amal's Docs or is marked "needs Amal's check"). Do not change any code. Commit wiki/17 only when finished, message "wiki 17: teacher brain v2 (Claude)".

## 2 · Codex (fresh run, working directory C:\Users\Mahdi\Documents\Codex\2026-09-04\do)

You are an expert Levantine (Palestinian) Arabic teacher and applied linguist. Produce an independent research report at outputs/teacher-brain-codex-2026-09-05.md. Do NOT read C:\dev\anees\wiki\17-teacher-brain-levantine-arabic.md first; work blind so the two reports can be compared. You MAY read the learner's materials: C:\dev\anees\data\vocab\grammar_materials_2026-09-05.md (the tutor's grammar doc), C:\dev\anees\data\vocab\words.json (the 2,120-word vocabulary), C:\dev\anees\data\lessons\2026-08-25\understanding.json and C:\dev\anees\data\lessons\2026-09-04\understanding.json (two real lessons with every word the learner said, who said it, and where the tutor corrected him).

Deliver, with sources for every outside claim:
1. The usual Levantine syllabus order (textbooks, university courses, tutor platforms), with citations, and a gap list against the tutor's grammar doc.
2. The ten grammar or pronunciation points that adult English speakers get wrong most, ranked, with evidence (error studies, teacher guides) and, for each, whether the two real lessons show it (quote the moment).
3. Ten 60-minute lesson plans in the tutor's observed style (explain in English → tutor models → learner repeats → tutor types the form in chat → drill through persons → conversation), each with one grammar unit, 10–15 target words taken only from words.json, three example sentences (short/medium/long) marked "needs tutor check", and the mistakes to listen for.
4. Detection patterns: for each hard point, the trigger words and shapes a transcript classifier could use, as JSON rows {id, rule, why, where, status:"planned"}.
5. Your disagreements with the tutor's doc, if any, stated carefully.
Rules: no invented Arabic presented as fact; the tutor's doc outranks textbooks; mark judgment vs sourced; do not modify C:\dev\anees. End with a claim-to-source ledger.

## 3 · The argument and the merge (Claude, same fresh chat as 1, after both reports exist)

Read outputs/teacher-brain-codex-2026-09-05.md. For every section: where do we agree, where do we disagree, who has the better source, what did each miss. Write the disagreements as a table in wiki/17 section F, then merge the best of both into sections B–D and the lesson-plan library, keeping Amal's Docs as the top authority. Then ask Codex to review the merged wiki/17 for errors in Arabic and for unsupported claims (rescue task: "review C:\dev\anees\wiki\17 for factual errors, invented Arabic, and claims without sources; list them; do not edit"). Fix what Codex finds, commit "wiki 17: teacher brain v3 (merged)", and give Medi a one-screen summary: five things both agree on, three things they argued about and who won, and the first lesson plan to try with Amal.
