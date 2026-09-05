# 17 — Teacher brain: Levantine (Palestinian) Arabic for an English-speaking adult (living document)

Started 2026-09-05 at Medi's request ("become an expert Levantine Arabic teacher; learn the lesson plans, the common grammar lessons, what is hardest for English speakers; keep a teacher brain document"). This page is the brain. It grows every session; every rule that changes what Anees flags must also land in `docs/data/ai_rules.json`.

**Status: v2 (Claude research pass, 2026-09-05).** Section A is ground truth from Amal's two Docs and the two recorded lessons. Sections B and C now carry sources; section E is a library of ten ready lesson plans; section G turns the hard points into classifier rows; section H lists what Amal teaches that textbooks do not (and the reverse). Section F is reserved for the Claude-vs-Codex disagreement table (v3).

Standard of proof used on this page:
- **Amal's Docs beat any textbook** (rule A2). Where they differ, the Doc wins and the textbook is noted.
- Every outside claim has a URL. Claims are tagged **[sourced]** or **[teacher judgment]**.
- **No invented Arabic.** Every Arabic example is either (a) copied from Amal's vocabulary Doc (`data/vocab/words.json`, 2,120 rows), (b) copied from her "Arabic Materials" Doc (`data/vocab/grammar_materials_2026-09-05.md`), (c) quoted from a lesson transcript with its timestamp, or (d) marked **needs Amal's check**.
- Lesson evidence cites `data/lessons/<date>/transcript.txt` by `[mm:ss]` and `understanding.json` events by seconds; clips are in `data/lessons/<date>/clips/` (names in understanding.json).

Reading the Arabizi: 2 = ء (glottal stop; also urban Palestinian ق), 3 = ع, 5 = خ, 6 = ط, 7 = ح, 8 = غ, 9 = ص. Amal writes ق as 2 in her Docs (2al2aan, 2adeem, 2areeb), which is the urban Palestinian sound ([Wikipedia, Levantine Arabic phonology](https://en.wikipedia.org/wiki/Levantine_Arabic_phonology): Damascus / Beirut / Jerusalem-type cities say ʔ; Gaza says g).

## A. What Amal actually teaches (ground truth)

Sources: vocabulary Doc (2,120 words, 20 topics; largest: Past Tense 825 rows, Adjectives 169, Verbs List 145, Command Tense 107), "Arabic Materials" Doc (snapshot 2026-09-05), lessons Aug 25 (57 min, 293 Doc-word events) and Sep 4 (65 min, 147 events, 47 chat-typed forms).

| Amal's unit | Her rule in one line | Anees rule |
|---|---|---|
| Prepositions min / 3ala / fi / ma3 / bi / la | each has 2–4 core functions; adjectives usually take *min* (5aayef minnak), 2al2aan + 3ala, mishtaa2 + la, mu5talef + 3an | prepositions with verbs are a homework focus (Sep 4 chat 00:54: "Enbasa6ti **bi/fi** el-7afle") |
| Noun possessives (idafa) | thing + owner, no "of"; first noun never takes el-; feminine first noun adds -t; last noun decides definiteness | word-choice slips on el- are `article` grammar (M2) |
| Noun + adjective | adjective after noun; el- on noun only = a statement; el- on both = a defined phrase | `article` / `gender` grammar kinds |
| Time and clock | el-saa3a + feminine number; u + minutes; rube3 / noss / ella rube3; singular / dual / plural of minute, second, hour | numbers topic |
| Emotions / adjectives + bakoon | no "to be" in plain present (ana ta3baan); bakoon / ykoon for habit, future, and **conditional after lamma / iza** | **M6 (Medi's hard one)**: "lamma akun za3lan" vs "ana za3lan" |
| Kul | kul + el- = all; kul without el- = every | article |
| b-prefix elimination | drop b- after biddi / laazim / mumkin, after abel-ma / ba3ed-ma / lamma / ra7, after la- / 3ashaan, on the second verb of a pair, and through u / wala / aw chains; keep it after enno | candidate `tense` slip; Sep 4 drill "lamma **ne6la3**" |
| Pointer rule (resumptive pronoun) | object first → verb needs -o / -ha: aktar eshi basawwi**h**, ay 7ada bashuf**o** | Sep 4 chat "aktar ishi" moment |
| Verb families | past tense from present (Doc: 825 rows), command tense (107), causative vs. reflexive: **babse6** (I make happy) vs **banbese6** (I become happy); Doc topic "Grammar Terminology & Causative Verbs" lists 8 such pairs (bad7ak / bada77ek, bazha2 / bazahhe2, baz3al / baza33el, bat3ab / bata33eb, ba5aaf / ba5awwef, bajhaz / bajahhez, ba3asseb) | Sep 4 new words; N1 |

Lesson shape observed (Sep 4, 65 min): one verb family drilled through all persons, present then past then command; English explanation, Amal models, Medi repeats, Amal types the form in chat (21 typed forms for babse6 / banbese6 / enbasa6); frequent code-switching; corrections by recast (she repeats the right form) more than by "la". Aug 25 was a conversation lesson ("I feel like a therapist today", [16:58]) built around emotions verbs, with grammar taught in passing.

What Amal corrected across both lessons (understanding.json, `correction: true` on Medi's events): 16 corrections on Aug 25, 8 on Sep 4. By kind (miss_kind.py v2): Aug 25 = 9 choice, 1 article, 6 unclear; Sep 4 = 4 article, 1 choice, 1 word, 2 unclear. So far the machine sees **article** and **word choice** most; the tense / b-prefix slips below are visible in the transcript but the classifier does not name them yet (that is what section G is for).

## B. The usual Levantine syllabus (what most courses teach, in order) — sourced

Method: I compared five published sequences and kept the order they share. The column "Amal" says whether her two Docs or the two lessons already cover the unit.

Sources for the sequences:
- **S1** King's College London, Levantine Arabic Level 1 (45 h, CEFR A1), three-part outline with grammar per part ([KCL syllabus PDF](https://www.kcl.ac.uk/study-legacy/assets/pdf/modern-language-centre/levantine-arabic-level-1-evening-course-syllabus.pdf)). Part 1: sound plurals, possessive endings, definite / indefinite, personal pronouns, demonstratives, question words, adjectives I. Part 2: negative, idafa, adjectives II, dual, plural with numbers, how much / how many, past tense. Part 3: verbs in the plural, comparatives and superlatives, was / were, future.
- **S2** Ohio State University, Colloquial Arabic I (Levantine, textbook *Hakini Arabi: Palestinian and Jordanian Colloquial for Beginners*, Abuhakema 2015), six lessons: greetings and biographical information → family and professions → dates, numbers, telephone → directions → food and shopping → health; functions listed include routines, past sequences, "used to", comparing, future plans ([OSU syllabus PDF](https://nelc.osu.edu/sites/default/files/Arabic%204111%20SP17.pdf)).
- **S3** Wikibooks *Levantine Arabic*, chapter order: pronunciation, negation, pronouns, questions, verbs (subjunctive, present), greetings, adverbs, then topic vocabulary (countries, colours, clothes, family, numbers, time, date, body, weather, house), motion / perception verbs, emotions ([Wikibooks printable version](https://en.wikibooks.org/wiki/Levantine_Arabic/Printable_version)).
- **S4** mossyrune "Levantine Arabic grammar, step by step", 15 steps: roots and patterns → SVO word order → definite article → gender → broken plurals → conjugation → habitual b- and progressive 3am → past → future ra7 → negation ma / mish → adjectives follow and agree → possession (construct, taba3, suffixes) → questions → modals (want / can / must) ([mossyrune](https://mossyrune.com/grammar/walkthrough/levantine-arabic)).
- **S5** Routledge *Colloquial Arabic (Levantine)* (Al-Masri; lesson 1 "ahlan wa sahlan", lesson 2 "This World" …) and *'Arabiyyat al-Naas Part One* (Younes; 29 theme units: countries, clothes, colours, family, professions) ([Routledge Colloquial](https://www.routledge.com/Colloquial-Arabic-Levantine-The-Complete-Course-for-Beginners/Al-Masri/p/book/9780415726856), [Routledge 'Arabiyyat al-Naas](https://www.routledge.com/Arabiyyat-al-Naas-Part-One-An-Introductory-Course-in-Arabic/Younes-Weatherspoon-SalibaFoster/p/book/9781138492868)). Full tables of contents were not fetchable (403); only the publisher blurbs are cited.
- Reference grammar for the rules themselves: Cowell, *A Reference Grammar of Syrian Arabic* (Georgetown), chapter 13 "Mode" covers the subjunctive uses ([Georgetown Press](https://press.georgetown.edu/Book/A-Reference-Grammar-of-Syrian-Arabic), [full text on archive.org](https://archive.org/stream/AReferenceGrammarOfSyrianArabic_201704/A_Reference_Grammar_of_Syrian_Arabic_djvu.txt)); [Wikipedia, Levantine Arabic grammar](https://en.wikipedia.org/wiki/Levantine_Arabic_grammar) for b-imperfect vs subjunctive, copula, idafa, numbers, illi.

| # | Unit (shared order) | Who teaches it here | Amal covered? |
|---|---|---|---|
| 1 | Sounds and Arabizi: ء 2, ع 3, ح 7, خ 5, ط 6, غ 8, ص 9; long vs short vowels | S1 Part 1 ("alphabet and sounds"), S3 ch. 1, [Wikipedia phonology](https://en.wikipedia.org/wiki/Levantine_Arabic_phonology) | Implicitly (every Doc row is Arabizi); never drilled as a unit. Sep 4 [58:15] "nitla" for ne6la3 shows the cost |
| 2 | Greetings, introductions; personal pronouns | S1 Part 1, S2 lesson 1, S3 ch. 3 and 8 | Yes: Doc topic "Introductions, greetings, and Pleasantries" (68 rows) |
| 3 | Nominal sentence, no "to be"; gender (-a / -e); adjective after noun and agreeing | S1 Part 1 "Adjectives I", S4 steps 4 and 11, Wikipedia grammar "Copula", "Adjectives / Word order" | Yes: Materials Doc "Noun + adjective", "Emotions / adjectives" (M / F / plural rows) |
| 4 | Definite article el-; idafa; possessive suffixes | S1 Part 1 (definite / indefinite, possessive endings) and Part 2 (idafa), S4 steps 3 and 12, Wikipedia grammar "Nominal sentences" (first noun of idafa always indefinite) | Yes: Materials Doc "Noun possessives" (4 patterns + professions) |
| 5 | Demonstratives (hada / hadi / hadol); question words | S1 Part 1, S3 ch. 4, S4 step 13 | Partly: Doc has Hada / Hadi (Adjectives), Hadaak / Hadeek / Hadoal (Location), shu / wein / keefak (Greetings); no unit on hada vs hadi agreement (Sep 4 [58:56] slip) |
| 6 | Numbers 1–10 with the dual and the 3–10 plural rule; 11–100 with singular; time; days | S1 Part 2 (dual, plural with numbers) and Part 3 (time, days, months), S2 lesson 3, Wikipedia grammar "Cardinal numbers" | Partly: Doc topics Numbers (57), Time and Calendar (86), Materials Doc "Time and clock" (d2ee2a / d2ee2tain / d2aaye2). The 3–10 + plural rule for ordinary nouns is not in her Docs |
| 7 | Present with b-; negation ma … / mish; fi / ma fi | S3 ch. 2 and 7, S4 steps 7 and 10, S1 Part 2 "The negative" | Yes for b- (145 Verbs List rows, all "Ana ba…"); negation only in passing (Doc: "Ana abadan ma baru7", "Mesh zaaki"); no ma…sh unit |
| 8 | b-drop after modals and time words (biddi, laazem, mumkin, lamma, ra7); future with ra7 | S3 ch. 6 "Subjunctive", S4 step 14 "Modals", Wikipedia grammar "Helping verbs", Cowell ch. 13; a tutor's plain-language list at [The Levantongue](https://thelevantongue.com/levantine-arabic/b-prefix-verbs-levantine-arabic-simplified/) (secondary verbs, ra7, biddo, imperative, laazem / mumkin / balki / mamnoo3 / mafrood, 3am) | Yes, and more fully than any source: Materials Doc "Verb b prefix elimination" (intent, time conjunctions, purpose la- / 3ashaan, compound verbs, u / wala / aw chains, keep after enno) |
| 9 | Past tense; kaan for past states; kaan + b-verb for "used to" | S1 Part 2 "Past tense", Part 3 "Was / were", S2 ("describe things that used to happen"), S4 step 8 | Yes: Doc "Past Tense" 825 rows (every verb × 8 persons); kaan + laazem seen Aug 25 [05:11]; "used to" (kaan + b-) not yet |
| 10 | Object and prepositional suffixes (shufto, ma3i, 3aleik) | S1 Part 1 "possessive endings", Wikipedia grammar | Yes, inside other units: pointer rule (basawwih, bashufo), prepositions (minnak, minno, minna, ma3i) |
| 11 | Commands and negative commands; plurals (sound -een / -aat, broken) | S1 Part 1 "sound plurals", S4 step 5 "broken plurals", Doc Command Tense | Yes: Command Tense (107 rows), plural column on nouns (Doc lists broken plurals: Byoot, Bwaab, Shabaabeek …); negative command not yet |
| 12 | Comparatives and superlatives (aktar / a7san + pointer) | S1 Part 3, S2 ("compare and contrast") | Yes: Materials Doc "Pointer rule" (Aktar / A7san / Aswa2 / A2al); Sep 4 [61:23]–[61:34] |
| 13 | Relative clause with illi; conditional iza / lamma; ykoon / bakoon for states; progressive 3am | S3, S4 step 7 (3am), Wikipedia grammar "Relative pronouns" (illi invariable) | Yes for ykoon / bakoon ("Use of Bakoon"); illi only in examples ("Hadi el moazeh eli mish elo"); 3am + verb not in her Docs |

Reading of the table **[teacher judgment]**: Amal's order is not a textbook's. She front-loaded the verb system (present → past → command for every verb, 1,077 Doc rows) and teaches the "small grammar" (b-drop, pointer, bakoon, idafa) as it comes up in conversation. Compared with S1–S5 she is ahead on verbs, modals and the pointer rule, and behind on three beginner units: sounds as a unit, numbers + noun agreement, and negation (ma…sh, wala, negative command).

## C. What is hardest for English speakers — ranked, sourced, and mapped to Medi's lessons

Ranking rule **[teacher judgment]**: frequency of the error in Medi's two lessons first, then how often the sources name it. Each row: why English makes it hard, the source, the exact lesson moment.

| Rank | Difficulty | Why it is hard for English speakers | Source | Seen in Medi's lessons (transcript time, clip) |
|---|---|---|---|---|
| 1 | **b-prefix: when to drop it** | English has one present form; Levantine switches to the bare (subjunctive) form after modals, time words, purpose words and on second verbs | Wikipedia grammar "Helping verbs" (b- drops after biddi, mumkin, laazem, 7abb) [sourced]; The Levantongue (6 drop contexts) [sourced]; Cowell ch. 13 "Mode" [sourced]; Amal's "b prefix elimination" (7 contexts) | Aug 25 [55:28] Medi "لما **ب**زهأ" → Amal [55:35] "لما **أ**زهأ" (b- kept after lamma; clip 2026-08-25 ≈ 3328 s); Aug 25 [04:51] "who لازم اشتغلت كتير" → [05:11] "كان لازم أشتغل كتير" (wrong form after laazem); Sep 4 [58:11]–[58:18] "betenbesti lamma nitla" drilled right |
| 2 | **ykoon / bakoon / kaan for states** | English always says am / is / was; Arabic omits it in the plain present, needs ykoon after lamma / iza and for habit / future, kaan in the past | Wikipedia grammar "Copula" (no copula in present; kaan elsewhere) [sourced]; Amal's "Use of Bakoon" (lamma / iza signal conditional → bakoon / ykoon) | Sep 4 [61:53] Medi "لما **ب**كون في الطبيعة؟" → Amal [62:11] "لما **أ**كون"; Medi [62:13] "I knew it was conditional but I got past it" (M6, clip 2026-09-04_036637_036882); Aug 25 [43:42] "**ي**كونوا أهل" → Amal [43:47] "**ن**كون" (person on ykoon); Aug 25 [26:38] "akun sayye'" → Amal "baseer sayye'" (getting worse = baseer, not bakoon) |
| 3 | **Definiteness: el- on superlatives, idafa and noun + adjective** | English "the" is one rule; Arabic puts el- on the last noun of an idafa, never on aktar / a7san + eshi, and on both noun and adjective only for a defined phrase | Alkohlani 2023, 89 advanced-learner texts: al- "poses serious difficulties for adult learners even at advance levels" ([IJLLT](https://al-kindipublisher.com/index.php/ijllt/article/view/5800)) [sourced]; Wikipedia grammar "Nominal sentences" (first noun of idafa always indefinite) [sourced]; Amal's "Noun possessives", "Noun + adjective", "Pointer rule" | Sep 4 [01:35] "**ال**أحسن" recast (event 135.2 s, article); [61:23] "So **ال**أكتر إشي" → Amal [61:25] "No أل, just أكتر إشي" (event 3683 s); Aug 25 [17:21] "هذي **ال**كلمة" (event 1057 s, article); Sep 4 517 s / 530 s ba3Id, nafs article slips |
| 4 | **Gender agreement (hada / hadi, -a adjectives, -at / -i verb endings)** | English adjectives and demonstratives do not agree | Alhawary 2009, *Arabic Second Language Acquisition of Morphosyntax* (Yale): nominal and verbal gender agreement studied in English-, French-, Spanish- and Japanese-L1 adults; his 2005 study had 27 English and 26 French speakers on subject–verb and noun–adjective agreement ([book page](https://dokumen.pub/arabic-second-language-acquisition-of-morphosyntax-9780300159158.html)) [sourced, from search summaries; book not read]; Husein 2021 (15 Ghanaian learners, Processability Theory): agreement structures develop in the predicted order, predicate adjectives behave unexpectedly ([Al-Adab Journal](https://aladabj.uobaghdad.edu.iq/index.php/aladabjournal/article/view/915)) [sourced]; Al-Thubaiti, "Verbal gender agreement in L2 Standard Arabic by L1 English and L1 French speakers" (Cascadilla) [sourced, abstract only]; demonstrative-gender study by English natives ([ResearchGate 2019](https://www.researchgate.net/publication/332017133_The_Acquisition_of_Grammatical_Gender_in_Arabic_Demonstratives_by_English_Native_Speakers)) [sourced, title only, page 403] | Sep 4 [58:56] Medi "bass **Hadi** al fill" → Amal [59:04] "**Hada**" (fe3el is masculine; clip 19); Sep 4 chat 00:34 the whole Btebse6 / Btebse6i / Btebse6u paradigm typed because the -i / -u endings were shaky |
| 5 | **Pointer (resumptive) pronoun after a fronted object** | English leaves a gap ("the thing I do"); Arabic needs -o / -ha on the verb after aktar / a7san / ay / kul + object | Wikipedia grammar (illi invariable; agreement carried by the pronoun) [sourced]; Amal's "Pointer rule" (three triggers: superlatives, ay / kul, indefinite introductions). L2 studies on Arabic resumptives exist but I could not read them (UW-Madison thesis "The acquisition of relative clauses: how do second language learners of Arabic do it?", [record](https://minds.wisconsin.edu/handle/1793/93469), 301 redirect) [unverified] | Sep 4 [61:29]–[61:34] Medi "and then I have to say إلي right? … No there's no" → Amal "إلـ" → Medi "أكتر إشي (pause 5.9 s) … بيبسطني" [61:50] ✓; Aug 25 [18:22] Amal models "أكتر إشي بيتعبك" word by word |
| 6 | **Verb families: causative vs reflexive (I make happy vs I become happy)** | one English verb maps to two Arabic patterns (Form II doubled middle vs Form VII n-prefix); the roots look alike | Cowell (verb forms, Georgetown) [sourced]; mossyrune step 1 "roots and patterns" [sourced]; Amal's Doc topic "Grammar Terminology & Causative Verbs" (8 pairs) | Sep 4 whole lesson (21 typed forms); [62:23] Medi "to make someone happy is بيسبط" → Amal [62:30] "ببسّط" → [62:34] "I should make you record just ببسط ×5"; Aug 25 [32:40] "ببسطها. I hate this verb"; understanding.json Sep 4: babse6 corrected at 1866 s and 1977 s, banbese6 at 3012 s |
| 7 | **Pharyngeals, emphatics, uvulars (ع ح خ غ ط ص ق) and vowel length** | no English equivalent; learners replace them with the nearest English sound | Aldamen & Al-Deaibes 2023, 14 American-English learners: emphatic stops reach native VOT but vowel F1 goes the wrong way ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9932739/)) [sourced]; "Problematic Arabic consonants for native English speakers: learners' perspectives" ([ResearchGate](https://www.researchgate.net/publication/282189571_Problematic_Arabic_Consonants_for_Native_English_Speakers_Learners'_Perspectives), abstract: pharyngeal-glottal contrast rated hardest) [sourced, page 403 today]; Wikipedia phonology (ħ, ʕ, emphatics, length) [sourced] | Sep 4 [58:15] "nitla" for ne6la3 (ع dropped, ط → t; Amal [58:18] recasts "nitla" as well, so she let it pass); [00:57]–[00:59] "lokat / Luka" for lu8a (غ → k), Amal [00:58] "لُغَة"; Aug 25 [55:12]–[55:25] "أزآن / أزأل" for زهآن (ه lost) |
| 8 | **Numbers with nouns (dual; 3–10 + plural; 11+ + singular)** | English is regular | Wikipedia grammar "Cardinal numbers" [sourced]; Wikibooks Numbers [sourced]; S1 Part 2 "The Dual, Plural with numbers" | Not yet in a lesson. Amal's "Time and clock" teaches the dual for minutes / seconds / hours (d2ee2tain, Saaneitain, Saa3tain) |
| 9 | **Prepositions chosen by the verb or adjective** | arbitrary from the English side (scared **of** = 5aayef **min**; miss = mishtaa2 **la**; ask someone = 6alab **min**) | Amal's "Prepositions" and "Emotions / adjectives" [Doc]; no error study found for Levantine specifically [gap] | Aug 25 [20:20] Medi "أطلبهم أو أطلب لهم؟" → Amal [20:48] "أطلب **من**هم"; Sep 4 chat 00:54 "Enbasa6ti bi/fi el-7afle" and [60:35] Amal "every verb and what preposition goes with it" as homework |
| 10 | **Negation and the wala / aw / u system** | ma…(sh) vs mish vs wala; English "or" splits into aw (either) and wala (options / nor) | Wikibooks Negation [sourced]; S4 step 10; Amal (Aug 25 [56:06] "ولا is used more for options") | Aug 25 [56:02] Medi "What is ولا؟ … is or" (event 3364 s, choice); Aug 25 [47:32] "أنا ما بعصب. أنا أبدًا ما بعصب" said right; Doc "Ana abadan ma baru7" |

Not on the list on purpose: **pauses** (rule M7: Medi builds the sentence before speaking; Aug 25 [03:45] pause 13.7 s, Sep 4 [61:34] pause 5.9 s before a right answer) and **near-synonym choice** (وقت كتير vs وقت طويل, Aug 25 [32:19]; شوب vs the Doc's Su5un [08:40]) which are vocabulary, not grammar.

Pronunciation note **[teacher judgment]**: Amal recasts nitla → nitla ([58:18]) and lets Medi's ع go; that is normal tutor triage (meaning first). Anees should still log the ع / ط / غ drops as `pronunciation`, never as a missed word (M4 keeps the stumble).

## D. How Anees should use this brain

- The miss classifier names the grammar behind a slip (section G rows), so "لما بكون" is `tense (b-drop after lamma)` and "الأكتر إشي" is `article (superlative)`, not "wrong".
- The planner's grammar topics map to the units in B; the after-link "Wrong grammar" tap offers the unit name from the row that fired.
- Each unit gets a one-line Arabizi rule and one Amal example on the Grammar tab (already there for the Materials Doc units; sections B rows 1, 6, 7, 13 need Amal's own examples first).
- Order of attack for Medi **[teacher judgment]**: C1 + C2 together (they are one rule: bare verb after lamma / iza / modals, and ykoon is just a verb), then C3 (el-), then C4 / C5 (agreement + pointer), then C7 as a 5-minute warm-up in every lesson.

## E. Lesson-plan library — ten 60-minute plans in Amal's shape

Shape (observed Sep 4, minutes are a proposal **[teacher judgment]**): 0–5 warm-up in Arabic (last lesson's words) · 5–12 English explanation of the one grammar unit · 12–20 Amal models 3 sentences, Medi repeats each · 20–30 Amal types the forms in chat, Medi reads them back · 30–42 drill through persons (ana / inta / inti / huwwe / heyye / i7na / intu / humme) · 42–55 conversation using the unit (Amal asks, Medi answers in full sentences) · 55–60 Amal names the two slips to work on; homework = the after-link sheet.

Target words are copied from the Doc (topic in brackets). Example sentences: **[Doc]** = from Amal's Materials Doc or vocabulary Doc, **[Amal, lesson]** = she said or typed it in a recorded lesson, **[needs Amal's check]** = my composition, not to be shown to Medi until she approves.

### Plan 1 — Bare verb after lamma / iza, with akoon / tkoon / ykoon (units C1 + C2, rule M6)
- Target words [Sentence Toolbox, Adjectives, Time]: Lamma, Iza, ra7, Ta3baan, Za3laan, Mabsoo6, Ju3aan, Mertaa7, Qalqaan, Na3saan, Mitdaayeq, M3asseb, Bukra, Kul yoam, Marrat.
- Short: "Ana ta3baan" [Doc]. Medium: "Ana bakoon kasool ba3ed el-shu8ul" [Doc]. Long: "Heyye betkoon mad8oo6a lamma ykoon 3endha shu8ul kteer" [Doc].
- Drill: bakoon / btkoon / btkooni / bikoon / btkoon / mnkoon-bnkoon / btkoonu / bikoonu (Amal to type the Palestinian forms; her Doc shows bakoon, betkoon, benkoon, beykoon).
- Listen for: "lamma **ba**koon" (b- kept, Sep 4 [61:53]); "ana akoon ta3baan" (bare form in a plain statement); person mismatch "ykoonu" for "nkoon" (Aug 25 [43:42]); "akoon" where "baseer" (become) is meant (Aug 25 [26:38]).

### Plan 2 — b-drop after biddi / laazem / mumkin and through u / wala / aw chains (unit C1)
- Target words [Verbs List, Food, Toolbox]: Ana beddi, Laazem, Ana baqdar, Ana ba7eb, Ana baballesh, Ana bashteri, 5ubez, Ana baru7, Ana bartaa7, Ana basaa3ed, Ana ba5alles, U, Aw, Wla, Enno.
- Short: "Biddi ashrab" [Doc]. Medium: "Beddi aru7 3ala el-dukkan la-ashtri khobez" [Doc]. Long: "Ana ba7eb a66alla3 3ala el-njoom u a7ki ma3ha" [Doc]; contrast "Ana bazonn enno ma bey7ebna" [Doc] (b- comes back after enno).
- Drill: biddi / biddak / biddek / biddo / bidha / bidna / bidkom / bidhom + ashrab → tishrab → tishrabi → yishrab … (forms: needs Amal's check for the exact Palestinian vowels).
- Listen for: "laazem **b**ashrab"; "biddi **b**aru7 u **b**ashteri" (b- creeping back on the chained verb); "kaan laazem" said as "laazem + past" (Aug 25 [04:51]).

### Plan 3 — Causative vs reflexive pairs: I make X vs I become X (unit C6)
- Target words [Grammar Terminology & Causative Verbs; Travel]: Ana bad7ak / Ana bada77ek, Ana bazha2 / Ana bazahhe2, Ana baz3al / Ana baza33el, Ana bat3ab / Ana bata33eb, Ana ba5aaf / Ana ba5awwef, Ana bajhaz / Ana bajahhez, Ana ba3asseb, Banbese6, Byebse6.
- Short: "Enbes6i biyoamek" [Amal, Sep 4 chat 01:01]. Medium: "Enbasa6u bisafrethom" [Amal, Sep 4 chat 00:56]. Long: "Btenbese6i lamma ne6la3?" [Amal, Sep 4 chat 00:59].
- Drill: one pair per round, present → past → command, using the exact forms Amal typed on Sep 4 (Babse6 / Btebse6 / Btebse6i / Btebse6u / Byebse6 / Byebse6u / Bnebse6; Basa6 / Basa6at / Basa6u / Basa6eet / Basa6ti / Basa6tu / Basa6na; Enbasa6 / Enbas6at / Enbasa6u / Enbasa6et / Enbasa6ti / Enbasa6tu / Enbasa6na).
- Listen for: "bibsit / babysit" for babse6 (Sep 4 1866 s, 1977 s); "banbesit" for banbese6 (3012 s); using the causative when the reflexive is meant ("I hate this verb", Aug 25 [32:40]).

### Plan 4 — Superlatives and the pointer pronoun (units C3 + C5)
- Target words [Quantity, Toolbox, Random Nouns, Verbs List]: Aktar, Aktar shee, A2al, A2al shee, Ay, Ay eshi, Ay 7ada, Kul, Kul 7ada, Eshi, Sha5s, Makaan, Ana bashuf, Ana ba3raf, Ana basawwi.
- Short: "Aktar eshi basawwih" [Doc]. Medium: "Ay 7ada bashufo" [Doc]. Long: "Min a7san zboon bteshte8el ma3o" [Doc].
- Drill: same object, eight subjects (basawwih / btsawwih / btsawwiha … needs Amal's check).
- Listen for: "**el**-aktar eshi" (Sep 4 [61:23]); the missing pointer "aktar eshi bashuf" without -o (Sep 4 [61:29] Medi asks about it); "a7san" vs "aktar" meaning swap (Sep 4 [61:07]–[61:15]: the most thing = aktar eshi, the best thing = a7san eshi).

### Plan 5 — Idafa and el-: noun + noun, noun + adjective (unit C3)
- Target words [Household, Random Nouns, Adjectives]: Bait, Ktaab, 8urfa, Tâwla, Matba5, Seyyara, 3aileh, Sadeeq, Shu8ul, Akel, Kbeer, Jdeed, 2adeem, Ndeef, Wese5.
- Short: "Bait kbeer" [Doc]. Medium: "Akel el-bait" / "Tawlet el-matba5" [Doc]. Long: "Dawu 8urfet noam el-3aile" [Doc]; contrast "El-bet 7elwa" (statement) vs "el-lebes el-jdeed" (phrase) [Doc].
- Drill: Amal names two nouns, Medi links them (ktaab + Mehdi → Ktaab Mehdi; 8urfa + sadeeqi → 8urfet sadeeqi; Doc patterns).
- Listen for: el- on the first noun ("el-ktaab Mehdi"); missing -t on a feminine first noun ("8urfa sadeeqi"); el- on the adjective in a statement.

### Plan 6 — Which preposition goes with which verb or adjective (unit C9)
- Target words [Toolbox, Adjectives, Travel, Verbs List]: Min, 3ala, Fi, Ma3, Bi, La, 3an, 5aayef, Bashtaa2, Qalqaan, Ana ba6lub (min), Ana ba7ki, Ana baru7, Ana bashte8el, Ana baaji.
- Short: "Ana 5aayef minnak" [Doc]. Medium: "Ana baru7 3ala el-shu8ul ma3 sadiqi" [Doc]. Long: "Ana bat3allam 3arabi la2dar a7ki ma3kom" [Doc].
- Drill: verb card → Medi adds the preposition and a pronoun (ba6lub **min**-hom, mishtaa2 **l**-ek, 2al2aan **3al**-eik: pronoun forms need Amal's check).
- Listen for: "a6lub-hom / a6lub-lhom" for "a6lub minhom" (Aug 25 [20:20]); "enbasa6ti **fi** el-7afle" vs **bi** (Sep 4 chat: Amal accepts both, ask her which she prefers).

### Plan 7 — Clock time and the dual / plural of minute, hour (units B6, C8)
- Target words [Time and Calendar, Materials Doc]: 2addaish El-saa3a?, Ay saa3a?, Elsaa3a wa7de, Tentain, 7awaali, Badri, Met2a55ar, el-sube7, el-3aser, billail, Maw3ed, d2ee2a / d2ee2tain / d2aaye2, Saa3a / Saa3tain / Sa3aat, rube3 / noss / ella rube3.
- Short: "Elsaa3a wa7de u 5amse" [Doc]. Medium: "El-saa3a talaate u d2ee2tain" [Doc]. Long: **needs Amal's check** (a sentence that combines "3ala elsaa3a 3ashara" [Doc] with a Doc verb, e.g. an appointment).
- Drill: Amal says a digital time, Medi says it in Arabic; then the reverse.
- Listen for: masculine number with saa3a ("elsaa3a wa7ad"); "d2ee2a" plural after 3 ("talaate d2ee2a" for talaate d2aaye2); "u" dropped before minutes.

### Plan 8 — Telling yesterday: past tense plus kaan + laazem (unit B9)
- Target words [Past Tense, Time]: Ana akalet, Ana a5adet, Ana shta8alet, Ana 2a3adet, Ana qara2et, Ana daraset, Ana katabet, Mbaare7, Min zamaan, Ba3dain, 2abel shwai, la-wa2et taweel, Laazem, kAn.
- Short: "Ana shta8alet" [Doc]. Medium: "كان لازم أشتغل كتير" [Amal, Aug 25 05:11]. Long: **needs Amal's check** (a three-clause account of yesterday with ba3dain).
- Drill: Amal gives the present ("Ana bakul"), Medi gives the past for all eight persons (Doc has every row).
- Listen for: "laazem + past" instead of "kaan laazem + bare present" (Aug 25 [04:51]); feminine past -at vs -et ("heyye aklat" vs "ana akalet", Doc); "kaan" dropped in "iza kaanat" clauses (Aug 25 [50:20] Amal models "إذا كانت خطيبتك معصبة").

### Plan 9 — Emotions with gender and plural endings; hada vs hadi (unit C4)
- Target words [Adjectives, People]: Mabsoo6 / Mabsoo6een, Ta3baan / Ta3baaneen, 5aayef / 5aayfeen, Za3laan, Ju3aan, Shab3aan, 3a6shaan, Na3saan, Hada, Hadi, Hadoal, Benet, Walad, Naas.
- Short: "El-bet 7elwa" [Doc]. Medium: "Humme mabsoo6een" [Doc]. Long: "Humme ma7roojeen minna" [Doc].
- Drill: Amal names a person (Rinad / your brother / your parents), Medi gives the adjective with the right ending; then "hada / hadi + noun" for ten Doc nouns.
- Listen for: "hadi el-fe3el" (Sep 4 [58:56]); masculine adjective for a woman; -een for a feminine plural where Amal wants -aat (Doc: Humme 7anoonaat).

### Plan 10 — Travel talk: ra7 + bare verb, commands, enbese6 (units C1, B11)
- Target words [Travel and Weather]: Basaafer, Ba7jez, Bawsal, Bazoor, Basawwer, Safra, Ma6aar, 6ayyaara, Tazkara, Shanta, Soora, Tewsal, Enbes6u bi-re7letkom, ra7, 2addaish 7a22o.
- Short: "2addaish 7a22o?" [Doc]. Medium: "Enbes6u bi-re7letkom" [Doc]. Long: "Humme ra7 yjibu el-3asha ma3hom" [Doc].
- Drill: "ra7 + verb" through persons (ra7 asaafer / tsaafer / tsaafri … needs Amal's check), then the commands Roo7, Ta3aal, 5ud, Shoof [Doc].
- Listen for: "ra7 **b**asaafer"; command with a b- ("bshoof" for Shoof); "tewsal" said to a woman without -i (Doc: Tewsli).

## F. Disagreements with Codex's blind report (to be filled in v3)

Reserved. v3 adds a table: section · Claude says · Codex says · better source · who missed what · verdict (Amal's Docs decide).

## G. Classifier patterns — rows for `docs/data/ai_rules.json` (all status "planned")

Detection is on Medi's turns only; a row fires only with a signal (rule M1: Amal recasts or Medi asks). The trigger lists use Amal's Doc spellings plus the Arabic script the transcript engine writes.

```json
[
  {"id": "G1", "rule": "b-drop after modals: after biddi/beddi/bidd-, laazem/lazim, mumkin, ba7eb, baqdar, baballesh, bajarreb the next verb must have no b-/bi-/by- prefix. Medi's verb keeps the b- and Amal recasts it → grammar slip kind 'tense', pattern 'b-drop-modal'.", "why": "Amal's 'b prefix elimination'; Wikipedia Levantine grammar 'Helping verbs'; Aug 25 04:51.", "where": "miss_kind.py: window of 3 tokens after a trigger; compare Medi's form with Amal's recast", "status": "planned"},
  {"id": "G2", "rule": "b-drop after time / purpose words: after lamma, iza, abel-ma, ba3ed-ma, ra7, la-, 3ashaan the next verb has no b-. Same test as G1, pattern 'b-drop-time'. Exception: b- is kept after enno.", "why": "Amal's Doc; Aug 25 55:28 'lamma bazha2' → 'lamma azha2'; Sep 4 61:53 'lamma bakoon' → 'lamma akoon'.", "where": "miss_kind.py", "status": "planned"},
  {"id": "G3", "rule": "ykoon after lamma / iza: lamma or iza followed by an adjective from the Doc with NO akoon/tkoon/ykoon/nkoon between them, and Amal recasts with one → grammar slip 'tense', pattern 'ykoon-missing'. The reverse (akoon in a plain statement with no lamma/iza/ra7/bukra/kul yoam nearby, recast without it) → 'ykoon-extra'.", "why": "Rule M6 (Medi 2026-09-05); Amal's 'Use of Bakoon'.", "where": "miss_kind.py; adjective list = Doc topic Adjectives", "status": "planned"},
  {"id": "G4", "rule": "Person on ykoon: a ykoon form whose person does not match the subject pronoun in the same clause (i7na … ykoonu) and Amal recasts the person → 'tense', pattern 'ykoon-person'.", "why": "Aug 25 43:42 'ykoonu ahel' → 'nkoon'.", "where": "miss_kind.py", "status": "planned"},
  {"id": "G5", "rule": "Superlative article: aktar / a7san / aswa2 / a2al preceded by el-/al- (الأكتر, الأحسن) and followed by eshi/ishi or a noun → 'article', pattern 'superlative' (already partly built: 'superlative pattern' in miss_kind v2).", "why": "Amal's 'Pointer rule'; Sep 4 01:35 and 61:23.", "where": "miss_kind.py (exists as pattern superlative; add the el- test on the preceding token)", "status": "partly"},
  {"id": "G6", "rule": "Pointer pronoun: after aktar/a7san/aswa2/a2al + eshi/wa7ad/wa7de, or ay/kul + noun, the next Doc verb must end in -o/-h/-ha/-hom (ـو/ـه/ـها/ـهم). Bare verb + Amal recast with the suffix → 'article'-class grammar, pattern 'pointer-missing'.", "why": "Amal's 'Pointer rule'; Sep 4 61:29.", "where": "miss_kind.py; needs the verb-suffix stripper in arabizi.py", "status": "planned"},
  {"id": "G7", "rule": "Idafa article: two Doc nouns in a row where the FIRST carries el-/al- and Amal recasts without it → 'article', pattern 'idafa-first-noun'. Feminine first noun without -t/-et before the second noun → pattern 'idafa-t'.", "why": "Amal's 'Noun possessives'; Aug 25 1057 s (el-kelme).", "where": "miss_kind.py; feminine = Doc english '(F)' or arabizi ending -a/-e/-eh", "status": "planned"},
  {"id": "G8", "rule": "Demonstrative gender: hada/hadi/hadaak/hadeek + Doc noun whose gender disagrees (hadi + masculine noun) and Amal recasts the demonstrative → 'gender', pattern 'demonstrative'.", "why": "Sep 4 58:56 'hadi el-fe3el' → 'hada'.", "where": "miss_kind.py; noun gender from the Doc (feminine = ends -a/-e/-eh or english '(F)')", "status": "planned"},
  {"id": "G9", "rule": "Adjective / verb agreement: subject pronoun or a Doc noun with known gender/number followed by an adjective in the wrong form (heyye + masculine, humme + singular) → 'gender' or 'plural', pattern 'agreement'.", "why": "Amal's 'Emotions / adjectives', 'Plural forms'; Alhawary 2009.", "where": "miss_kind.py (gender/plural kinds exist; add the pronoun-anchored test)", "status": "partly"},
  {"id": "G10", "rule": "Causative vs reflexive: Medi uses one member of a Doc pair (babse6/banbese6, baz3al/baza33el, bat3ab/bata33eb, ba5aaf/ba5awwef, bazha2/bazahhe2, bad7ak/bada77ek, bajhaz/bajahhez) and Amal recasts with the other → 'choice', pattern 'verb-family'.", "why": "Doc topic 'Grammar Terminology & Causative Verbs'; Sep 4 62:23.", "where": "miss_kind.py; pairs table from the Doc topic", "status": "planned"},
  {"id": "G11", "rule": "Pronunciation drops: Medi's token matches a Doc word by skeleton but is missing ع (3), ح (7), or has t for ط (6), k for غ (8), s for ص (9), and Amal repeats the word → 'pronunciation', pattern 'pharyngeal'. Never a missed word.", "why": "Sep 4 58:15 'nitla' for ne6la3, 00:59 'Luka' for lu8a; Aldamen & Al-Deaibes 2023.", "where": "arabizi.Matcher skeleton tier already finds these; add the letter diff", "status": "planned"},
  {"id": "G12", "rule": "Preposition after a verb or adjective: Doc entries that carry a preposition in the key ('Ana ba6lub (min)', 5aayef + min, mishtaa2 + la, 2al2aan + 3ala, mu5talef + 3an) followed by a different preposition or a bare object suffix, with Amal's recast → 'choice', pattern 'preposition'.", "why": "Amal's 'Prepositions', 'Emotions'; Aug 25 20:20.", "where": "miss_kind.py; preposition list from the Doc keys and Materials Doc", "status": "planned"},
  {"id": "G13", "rule": "Number + noun: talaate…3ashara followed by a singular Doc noun, or 11+ followed by a plural, or tnein + non-dual → 'plural', pattern 'number-noun'.", "why": "Wikipedia Levantine grammar 'Cardinal numbers'; Amal's 'Time and clock' (d2ee2tain).", "where": "miss_kind.py; plural forms from the Doc plural column", "status": "planned"},
  {"id": "G14", "rule": "wala vs aw: Medi says aw where Amal recasts wala (or the reverse) → 'choice', pattern 'or-system'. ma…sh / mish swaps → 'choice', pattern 'negation'.", "why": "Aug 25 56:02–56:06.", "where": "miss_kind.py", "status": "planned"}
]
```

## H. What Amal teaches that textbooks do not — and the reverse

Amal, not the textbooks **[Doc vs S1–S5]**:
- The **pointer rule as a rule** with three triggers (superlative, ay / kul, indefinite introduction); textbooks bury it under "relative clauses".
- **Seven b-drop contexts in one list** including purpose la- / 3ashaan, compound verbs and u / wala / aw chains, plus the enno exception; the sources give two to six.
- **Bakoon as a fourth meaning** (habit, future, conditional, and "tend to be") tied to lamma / iza; the sources treat kaan only as past copula.
- **Professions idafa** (Doktoar snaan, M3allem el3arabi, Ustaazo elfarsi) with the el- placement.
- **Causative / reflexive pairs** as a vocabulary topic with eight pairs, taught by one full-lesson drill.
- The **full 8-person paradigm of every verb** in three tenses (1,077 Doc rows) before any "grammar unit".

Textbooks, not (yet) Amal **[S1–S5 vs Doc]**:
- **Sounds as a unit** (S1 Part 1, S3 ch. 1) with minimal pairs; Medi's ع / ط / غ drops are untreated.
- **Number + noun agreement** beyond the clock (S1 Part 2).
- **Negation as a system** (ma…sh, mish, wala, negative command; S3 ch. 2, S4 step 10).
- **Progressive 3am + verb** (S4 step 7; The Levantongue lists it as a b-drop context).
- **"Used to" = kaan + b-verb** (S2 functions).
- **Broken plurals as patterns** (S4 step 5); the Doc lists them word by word.

One dialect note: The Levantongue says "we" takes an **m-** prefix (mn-); Amal's Doc uses **bn-** (bnebse6, bne2dar, benkoon). Both are real Levantine; bn- is the Palestinian form Amal teaches, so Anees keeps bn- ([The Levantongue](https://thelevantongue.com/levantine-arabic/b-prefix-verbs-levantine-arabic-simplified/) vs Materials Doc).

## I. Source ledger (claim → source)

| Claim | Source |
|---|---|
| A1 course order: pronouns, possessives, definite / indefinite, demonstratives, questions, adjectives → negation, idafa, dual, numbers, past → plural verbs, comparatives, was / were, future | [KCL Levantine Level 1 syllabus](https://www.kcl.ac.uk/study-legacy/assets/pdf/modern-language-centre/levantine-arabic-level-1-evening-course-syllabus.pdf) |
| University Levantine course, six thematic lessons, Palestinian / Jordanian textbook | [OSU Colloquial Arabic I syllabus](https://nelc.osu.edu/sites/default/files/Arabic%204111%20SP17.pdf) |
| Wikibooks chapter order; numbers 3–10 + plural, 11+ singular; b- forms the present on the subjunctive | [Wikibooks Levantine Arabic](https://en.wikibooks.org/wiki/Levantine_Arabic/Printable_version) |
| 15-step grammar order (roots → article → gender → plurals → conjugation → b-/3am → past → ra7 → negation → adjectives → possession → questions → modals) | [mossyrune](https://mossyrune.com/grammar/walkthrough/levantine-arabic) |
| b-imperfect = indicative, subjunctive after modals (bidd, mumkin, laazem, 7abb); no present copula, kaan elsewhere; idafa first noun indefinite; adjectives follow and agree in definiteness; 3–10 plural, 11–99 singular, dual with 2; illi invariable | [Wikipedia Levantine Arabic grammar](https://en.wikipedia.org/wiki/Levantine_Arabic_grammar) |
| Six b-drop contexts (secondary verbs, ra7, biddo, imperative, laazem / mumkin / balki / mamnoo3 / mafrood, 3am); m- prefix for "we" | [The Levantongue](https://thelevantongue.com/levantine-arabic/b-prefix-verbs-levantine-arabic-simplified/) |
| Cowell ch. 13 "Mode", subjunctive uses | [Georgetown Press](https://press.georgetown.edu/Book/A-Reference-Grammar-of-Syrian-Arabic), [archive.org text](https://archive.org/stream/AReferenceGrammarOfSyrianArabic_201704/A_Reference_Grammar_of_Syrian_Arabic_djvu.txt) |
| Routledge Colloquial Arabic (Levantine) lesson 1–2 titles; 'Arabiyyat al-Naas 29 theme units | [Routledge](https://www.routledge.com/Colloquial-Arabic-Levantine-The-Complete-Course-for-Beginners/Al-Masri/p/book/9780415726856), [Routledge](https://www.routledge.com/Arabiyyat-al-Naas-Part-One-An-Introductory-Course-in-Arabic/Younes-Weatherspoon-SalibaFoster/p/book/9781138492868) |
| Elihay *Speaking Arabic* (Palestinian): 50 lessons, ~2,500 words | [Gefen Publishing](https://www.gefenpublishing.com/products/speaking-arabic) |
| Definite article al- difficult even for advanced learners (89 texts, Arabic Learner Corpus) | [Alkohlani 2023, IJLLT](https://al-kindipublisher.com/index.php/ijllt/article/view/5800) |
| Gender agreement (nominal, verbal) studied in English, French, Spanish, Japanese L1 adults; 2005 study 27 English + 26 French | [Alhawary 2009, Yale UP](https://dokumen.pub/arabic-second-language-acquisition-of-morphosyntax-9780300159158.html) (search summaries only) |
| Agreement structures develop in Processability-Theory order; predicate adjective is the odd one | [Husein 2021, Al-Adab Journal](https://aladabj.uobaghdad.edu.iq/index.php/aladabjournal/article/view/915) |
| Verbal gender agreement by L1 English and French learners | Al-Thubaiti, Cascadilla Press (found via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/search?query=Alhawary+acquisition+Arabic+gender+agreement+English+French+speakers); no open copy) |
| Gender in demonstratives by English natives | [ResearchGate 2019](https://www.researchgate.net/publication/332017133_The_Acquisition_of_Grammatical_Gender_in_Arabic_Demonstratives_by_English_Native_Speakers) (title only; page returned 403) |
| Emphatic consonants: American learners match VOT, mis-set vowel F1 (n = 14 learners + 5 natives) | [Aldamen & Al-Deaibes 2023, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9932739/) |
| Pharyngeal-glottal contrast rated hardest by English-speaking learners | [ResearchGate](https://www.researchgate.net/publication/282189571_Problematic_Arabic_Consonants_for_Native_English_Speakers_Learners'_Perspectives) (abstract via search; page 403) |
| Pharyngeals ħ ʕ, emphatics, uvular q; ʔ in Damascus / Beirut, g in Gaza; vowel length phonemic | [Wikipedia Levantine Arabic phonology](https://en.wikipedia.org/wiki/Levantine_Arabic_phonology) |
| Palestinian lexicon with plurals and phonology (36k entries) for checking forms | [Maknuune, arXiv 2210.12985](https://arxiv.org/abs/2210.12985) |
| Feedback that works (prompts > recasts for repair; explicit instruction wins) | wiki 02, Lyster & Saito 2010 ([ERIC](https://eric.ed.gov/?id=EJ892626)), Norris & Ortega 2000 ([ERIC](https://eric.ed.gov/?id=EJ611436)) |

Not reached this pass (403 / 404): Routledge tables of contents, Amazon look-inside for *Shou fi ma fi?* and Isleem, Sijal's Levantine syllabus (task-based, not enumerated), the UW-Madison relative-clause thesis, the Reading thesis on pharyngeals. None of the rankings above rests on them.

## J. Next

1. Codex's blind report → section F table → v3 merge (this session).
2. Amal to check the six "needs Amal's check" items (Plans 2, 4, 6, 7, 8, 10 drills / long sentences) on her next planner link.
3. Build G1–G3 and G5–G6 first (they cover C1–C3 and C5, the four most frequent slips); re-run both lessons and count how many of the 24 corrections get a named pattern.
