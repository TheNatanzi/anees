# Grammar-correction sweep — 2026-09-24

Every Amal turn after a Medi turn, all **13** recorded lessons (09-18 and 09-19 are two separate lessons). Counts only fixes Amal **said out loud**. Vocab, pronunciation (S4), his own fixes, pauses (S5) and chat-only fixes are kept apart. Nothing was re-transcribed, no score / bucket / console / Word Bank was changed, nothing was sent.

Data: `data/grammar-sweep-2026-09-24.json` · chart: `C:/Claude/reports/GRAMMAR-SWEEP-BUCKET-CHART-2026-09-24.png`

## Headline

| | count |
|---|---|
| Grammar fixes when Medi **spoke** | **312** |
| · fit an existing bucket | 283 |
| · fit no bucket → 3 proposed new buckets | 29 |
| Fixes when he **misread** her Arabic (listening drills, mostly 09-19) — kept apart | 21 |
| Vocabulary fixes → Word Bank list | 147 |
| Machine audit already had | 103 of 312 (**33%**); on the 11 audited lessons 103 of 272 (38%) |

**Hand check:** 20 random rows re-read against the transcript → **17 / 20 right (85%)**.
- ✗ 0921-30 not a correction (rejected)
- ✗ 0904-10 root-letter slip = pronunciation (moved with 4 like it)
- ✗ 0918-12 Medi's line untranscribed - cannot verify (kept, low)
- ↻ 0921-23 verb agreement, not adjective -> NEW-B18 (with 13 like it)

After the check, 5 root-letter slips (بنسبت for بنبسط) moved to pronunciation, 1 row rejected, and 14 verb-agreement rows moved from A8/B1/B5 to proposed B18.

## Things Medi should know

1. **B3 text vs Amal.** Three times she kept the b- after `iza`: 09-05 53:49 *إذا بكون مش أكون*, 09-10 22:27 *إذا ما بشوفك*, 09-11 24:45 ("with B"). B3 says drop b- after iza. Not changed — needs Medi / Amal ruling.
2. **Gap buckets she is already teaching.** Gap buckets are never scored, but Amal corrected them out loud: B11 negative commands 9×, B15 participles 9×, C4 negation 6×, E1 number+noun 3×, C9 2×, A9b 1×, B7 1×. By the wiki's own rule these may flip to normal buckets.
3. **Machine audit is often in the wrong bucket** even when it finds the fix (e.g. E1→E5, B10→B11/B12, A8→A3). 55 of 165 machine-audit events and 47 of 134 gold-set events were rejected on read (chat-only, vocab, self-fix, or not a fix) — list in the JSON `audit_reconcile`.
4. **Transcript holes (not paid for):** 09-23 Medi's first ~23:40 missing; 09-16 27:01-27:45, 28:55-31:33, 1:02:47-1:08:20; 09-11 18:13-22:42, 30:33-36:33; 09-17 ~14:00-22:15; 09-18 20:40-31:10; 09-23 59:08-1:02:16. Fixes there are low confidence or missing.

## Totals per bucket (speaking only)

| bucket | name | fixes | machine had |
|---|---|---|---|
| B5 | past tense | 32 | 5 |
| B12 | make-X vs get-X | 28 | 3 |
| NEW-B18 | NEW B18 verb matches its subject | 26 | 7 |
| D2 | verb + its fixed preposition | 24 | 7 |
| D4 | endings on verbs | 20 | 7 |
| B1 | present with b- | 13 | 10 |
| A9 | plurals | 12 | 1 |
| D1 | prepositions | 11 | 5 |
| A1 | el- (the) | 9 | 4 |
| B15 | participles | 9 | 1 |
| C7 | illi | 9 | 2 |
| B11 | negative commands | 9 | 2 |
| A2 | idafa (possession) | 8 | 7 |
| B2 | b-drop after modals | 7 | 0 |
| A8 | gender on adjectives | 6 | 3 |
| A4 | possessive endings | 6 | 2 |
| C2 | the pointer rule | 6 | 2 |
| C4 | saying no | 6 | 2 |
| D3 | endings on prepositions | 6 | 5 |
| A7 | noun + adjective | 5 | 3 |
| B3 | b-drop after time words | 5 | 3 |
| C3 | comparatives | 5 | 2 |
| B8 | bakoon / ykoon | 5 | 3 |
| B10 | commands | 5 | 1 |
| A3 | feminine -t in idafa | 4 | 2 |
| B16 | kan laazem | 3 | 3 |
| E1 | number + noun | 3 | 0 |
| B6 | kaan = was / were | 3 | 1 |
| A10 | hada / hadi | 2 | 2 |
| C9 | word order | 2 | 0 |
| E2 | clock time | 2 | 1 |
| E5 | kam + singular | 2 | 1 |
| A11 | kul: all vs every | 2 | 1 |
| B13 | future with ra7 | 2 | 1 |
| C4b | words that drag a ma along | 2 | 0 |
| NEW-A12 | NEW A12 pronoun matches who you mean | 2 | 0 |
| B9 | person on ykoon | 1 | 1 |
| C5 | u / aw / wala | 1 | 0 |
| C1 | no word for 'to be' | 1 | 0 |
| A9b | broken plurals are patterns | 1 | 0 |
| B7 | kaan + b-verb = used to | 1 | 0 |
| C10 | preposition goes in front | 1 | 0 |
| E4 | calendar | 1 | 1 |
| E3 | time units, two-of and many-of | 1 | 1 |
| A6 | professions | 1 | 1 |
| A5 | chain possession | 1 | 0 |
| NEW-C11 | NEW C11 noun (not verb) after a preposition | 1 | 0 |

Listening-drill misreads (not scored as speaking): B12 7, D2 4, B5 2, B1 2, D3 2, NEW-B18 2, B10 1, D4 1

## Per lesson

| lesson | speaking fixes | machine had | listening | vocab |
|---|---|---|---|---|
| 2026-08-25 | 24 | 12 | 0 | 13 |
| 2026-09-04 | 24 | 4 | 0 | 11 |
| 2026-09-05 | 25 | 9 | 0 | 5 |
| 2026-09-10 | 20 | 0 | 0 | 10 |
| 2026-09-11 | 21 | 6 | 0 | 10 |
| 2026-09-14 | 29 | 6 | 0 | 7 |
| 2026-09-15 | 29 | 6 | 0 | 8 |
| 2026-09-16 | 23 | 5 | 0 | 10 |
| 2026-09-17 | 28 | 21 | 0 | 5 |
| 2026-09-18 | 20 | 0 | 0 | 4 |
| 2026-09-19 | 5 | 0 | 20 | 12 |
| 2026-09-21 | 42 | 29 | 0 | 32 |
| 2026-09-23 | 22 | 5 | 1 | 20 |

### 2026-08-25

_read all 624 turns 02:54-59:55 (source transcript.txt, chat=0 so no typed lines). 36:27-42:30 is transcribed in Latin transliteration (‹›) not Arabic script. No untranscribed gaps; 09:32-13:48 is Meet setup talk in English._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0825-01 | 04:22→04:49 | بس إحنا بدأ...<br>_Bass i7na bada..._ | بدأنا.<br>_badaina._ | إحنا بدأ → بدأنا | past verb missing the 'we' ending -na | B5 | medium | **missed** |
| 0825-02 | 04:51→05:11 | بدأنا a marketing project who who لازم اشتغلت كتير<br>_badaina a marketing project who who Laazem shta8alet Kteer_ | كان لازم أشتغل كتير.<br>_kaan Laazem Eshte8el Kteer._ | لازم اشتغلت → كان لازم أشتغل | put the past on the verb after laazem instead of kaan laazem + bare verb | B16+B2 | high | yes |
| 0825-03 | 09:12→09:14 | درجة حرارة.<br>_Daraja 7araara._ | درجة الحرارة.<br>_Daraja el-7araara._ | درجة حرارة → درجة الحرارة | idafa owner missing el- | A2 | high | yes |
| 0825-U1 | 13:54→14:08 | بقدر، آ-آآآ، تفهم-<br>_ba2dar, aaa-aaa, تفهم-_ | يفهم<br>_يفهم_ | تفهم → يفهم | wrong person prefix on present verb (Google Meet = he/it) | NEW-B18 | medium | **missed** |
| 0825-04 | 14:44→14:52 | يأتينا، الـ ترجمة. الـ-<br>_ya2teena, el Tarjame. el-_ | ترجمة<br>_Tarjame_ | الـ ترجمة → ترجمة | el- on a new (unknown) thing | A1 | low | yes |
| 0825-05 | 15:31→15:47 | الـ تاني مشكلة. No.<br>_el taani mushkelah. No._ | Okay. So second goes after on- ... تاني، تاني مشكلة or المشكلة التانية<br>_Okay. So second goes after on- ... taani, taani mushkelah or el-mushkelah el-taanye_ | الـ تاني مشكلة → المشكلة التانية / تاني مشكلة | el- on the ordinal in front of the noun; ordinal-adjective goes after | A7 | high | yes |
| 0825-06 | 20:20→20:48 | أطلبهم أو أطلب-- is it أطلب لهم or أطلبهم؟<br>_a6lobhom Aw etlob-- is it etlob ilhom or a6lobhom?_ | أطلب منهم.<br>_etlob minhom._ | أطلبهم / أطلب لهم → أطلب منهم | talab takes min, not a direct object or la- | D2 | high | **missed** |
| 0825-U2 | 22:13→22:44 | عيلتي، اللي، أشتغل معهم. و هو...<br>_3elti, illi, Eshte8el ma3hom. u Huwwe..._ | هما.<br>_humma._ | هو → هما | singular pronoun for the family members (they) | NEW-A12 | medium | **missed** |
| 0825-07 | 22:54→23:09 | لازم، لازم أطلب، أطلبهم-<br>_Laazem, Laazem etlob, a6lobhom-_ | منهم.<br>_minhom._ | أطلبهم → أطلب منهم | again dropped min after talab | D2 | high | **missed** |
| 0825-08 | 23:10→23:24 | أطلب منهم كتير إنو، يخلص، يخلصهم؟<br>_etlob minhom Kteer Eno, y5alles, y5alleshom?_ | يخلصوه.<br>_y5allsu._ | يخلصهم → يخلصوه | object ending should be -o (the work = it) on the they-verb, not -hom | D4 | medium | yes |
| 0825-09 | 25:47→28:16 | بتضل تعصب، تعصب، زمان طويل.<br>_btiDall ti3a99ib, ti3a99ib, zamaan Taweel._ | خطيبتي ما بتضل تعصب... So it's angry, not to get angry. It's the adjective.<br>_5a6ibti ma btiDall ti3a99ib... So it's angry, not to get angry. It's the adjective._ | ما بتضل تعصب → ما بتضل معصبة | used the verb 'get angry' after dall instead of the state word 'angry' | B15 | high | **missed** |
| 0825-10 | 27:24→27:54 | أنا أعمل، ب- أ- أ- أعمل؟ بـ... أعمل. أعمل غلط.<br>_Ana E3mel, Bi- aa- aa- E3mel? Bi... E3mel. E3mel 8ala6._ | أنا, I did something wrong. What's I made- ... عملت<br>_Ana, I did something wrong. What's I made- ... 3melet_ | أعمل غلط → عملت إشي غلط | present form for a past event | B5 | medium | **missed** |
| 0825-11 | 28:45→28:52 | So ما, ما بتضل معصب؟<br>_So ma, ma btiDall M3asseb?_ | معصبة<br>_M3asbe_ | معصب → معصبة | masculine adjective for his fiancee | A8 | high | yes |
| 0825-U3 | 31:59→32:06 | إن، إنتي ما-<br>_en, inti ma-_ | هي.<br>_heyye._ | إنتي → هي | 'you' instead of 'she' for the fiancee | NEW-A12 | medium | **missed** |
| 0825-12 | 37:34→37:36 | Wouldn't it be ‹balhom› 'cause we're watching the kids?<br>_Wouldn't it be ‹balhom› 'cause we're watching the kids?_ | No, we are... Still this is part of the verb... ‹bindir balna›<br>_No, we are... Still this is part of the verb... ‹bindir balna›_ | بندير بالهم → بندير بالنا | possessive on baal must match the subject (we), not the kids | A4 | high | yes |
| 0825-13 | 37:48→37:52 | So is it ‹yahom›?<br>_So is it ‹yahom›?_ | ‹Ala›.<br>_‹Ala›._ | بندير بالنا ياهم → بندير بالنا على | wrong preposition after dar baal (takes 3ala) | D2 | medium | **missed** |
| 0825-14 | 39:07→39:29 | ‹Ahna il tinen›, ‹bin khaf, bin khaf min, is it ‹nakun ahel›?<br>_‹Ahna il tinen›, ‹bin khaf, bin khaf min, is it ‹nakun ahel›?_ | Oh, here ‹hala ma btihtaj min›. ‹Bin khaf nakun›.<br>_Oh, here ‹hala ma btihtaj min›. ‹Bin khaf nakun›._ | بنخاف من نكون → بنخاف نكون | kept min before a verb after khaaf (min only before a noun) | D2 | medium | **missed** |
| 0825-15 | 43:42→43:47 | بنخطط. اه، يكونوا أهل.<br>_ben5a66et. aah, ykunu Ahel._ | نكون.<br>_nkoon._ | يكونوا → نكون | they-form of ykoon for 'we' | B9 | high | yes |
| 0825-16 | 48:51→48:55 | عشان، اه، بعصب<br>_3ashaan, aah, ba3asseb_ | أعصب<br>_a3a99ib_ | عشان بعصب → عشان أعصب | kept b- after 3ashaan | B3 | high | yes |
| 0825-U4 | 49:19→49:33 | ولا إشي، ولا إشي بيعص-- بعصبني<br>_Wala eshi, Wala eshi بيعص-- bey3assebni_ | بيعصبني<br>_bi3a99ibni_ | بعصبني → بيعصبني | I-prefix ba- instead of it-prefix bi(y)- on the present verb | NEW-B18 | medium | **missed** |
| 0825-17 | 50:50→51:08 | هي ما، ما تعصب<br>_heyye ma, ma ti3a99ib_ | بتعصب<br>_bti3a99ib_ | ما تعصب → ما بتعصب | dropped the b- on a plain present verb | B1 | high | yes |
| 0825-18 | 55:28→55:35 | زهآن. زهآن. بس، آه، لما بزهأ.<br>_zah2aan. zah2aan. Bass, aaah, Lamma bazha2._ | لما أزهأ.<br>_Lamma azha2._ | لما بزهأ → لما أزهأ | kept b- after lamma | B3 | high | yes |
| 0825-19 | 55:36→56:01 | Oh, I can say ولا right؟ ولا،<br>_Oh, I can say Wala right? Wala,_ | أو؟ ... ولا is used more for options يعني.<br>_Aw? ... Wala is used more for options Ya3ni._ | ولا → أو | wala used for a plain 'or' in a statement; it's for offering options | C5 | medium | **missed** |
| 0825-20 | 58:18→58:21 | أغو، أغير الجو.<br>_أغو, a8ayyer El-jaw._ | بغير جو. ... No ال. Just جو.<br>_Ba8ayyer Jaww. ... No el. Just Jaww._ | أغير الجو → بغير جو | no b- on the present verb, and el- on jaw in the set phrase | B1+A1 | high | yes |

### 2026-09-04

_read all 1046 turns 00:04-1:03:11 (source transcript.txt, chat=0). Diarization is badly fragmented: many turns are 1-3 words and sentences are split across speakers, so Amal/Medi labels are often swapped (e.g. 02:15-02:19, 52:21-52:33, 1:01:29-1:01:33). 11:00-22:30 is almost all English about AI tooling; 22:50-24:50 is an English interruption with a honey seller. 21:00 onward is mostly Latin transliteration. Lesson core 28:00-1:03:00 is a بسط/انبسط conjugation drill._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0904-01 | 02:06→02:10 | في<br>_Fi_ | اللي فيه<br>_illi fih_ | طريقة ... في → طريقة اللي فيها | relative clause needs illi + fi with a pointer ending | C7+D3 | low | yes |
| 0904-02 | 02:15→02:19 | الأحسن<br>_el-a7san_ | طريقة. شو أحسن ... طريقة<br>_Tari2a. shu a7san ... Tari2a_ | الأحسن → أحسن طريقة | el- on the superlative in front of the noun | C3 | low | **missed** |
| 0904-03 | 03:15→03:24 | بقدر آم أصلح، أصلحه آم…<br>_ba2dar Emm أصلح, أصلحه Emm…_ | أصلّحها بي لأنه مشكلة is<br>_أصلّحها بي la2anno mushkelah is_ | أصلحه → أصلّحها | masculine object ending for مشكلة (feminine) | D4+A8 | high | **missed** |
| 0904-04 | 03:47→04:08 | أنا بتحمس. amm أنا بتحمس<br>_Ana bat7ammas. amm Ana bat7ammas_ | You are excited or you get excited? ... So neither not تحمس not بهمِس<br>_You are excited or you get excited? ... So neither not et7ammas not بهمِس_ | أنا بتحمس → أنا متحمس | verb 'I get excited' where the state word 'excited' was meant | B15 | high | **missed** |
| 0904-05 | 07:12→07:16 | أي كلمة مشكلة<br>_Ay Kelme mushkelah_ | عندي مشكلة فيها<br>_3endi mushkelah fiha_ | أي كلمة مشكلة → عندي مشكلة فيها | missing the preposition with a pointer ending back to the word | C2+D3 | medium | **missed** |
| 0904-06 | 08:36→08:42 | ana بعيد الـ، الـ نفس مش الـ-<br>_ana Ba3eed el, el Nafs mesh el-_ | No, نفس المشكلة<br>_No, Nafs el-mushkelah_ | الـ نفس مشكلة → نفس المشكلة | el- on nafs instead of on the second noun | A2 | high | yes |
| 0904-07 | 09:56→10:03 | عند-- ما عنده،<br>_3end-- ma 3indo,_ | صحيح. لما ما يكون عنده جواب للـ السؤال<br>_sa7i7. Lamma ma ykun 3indo jawaab لل el-su2aal_ | لما الـ ... ما عنده → لما ما يكون عنده | no ykoon after lamma | B8 | medium | **missed** |
| 0904-08 | 12:54→13:02 | al-, el<br>_al-, el_ | Not el, just ghayr<br>_Not el, just ghayr_ | الغير → غير | added el- where none belongs | A1 | low | **missed** |
| 0904-24 | 1:01:23→1:01:25 | So الأكتر إشي-<br>_So el-Aktar eshi-_ | No أل just أكتر إشي.<br>_No el just Aktar eshi._ | الأكتر إشي → أكتر إشي | el- on the superlative in front of the noun | C3 | high | **missed** |
| 0904-25 | 1:01:29→1:01:33 | إشي and then I have to say إلي right؟<br>_eshi and then I have to say eli right?_ | No there's no ... إلـ.<br>_No there's no ... el._ | أكتر إشي إلي → أكتر إشي | added illi after aktar ishi | C7 | low | **missed** |
| 0904-27 | 1:01:53→1:02:11 | بيبسطني لماaa would this be conditional؟ لما بكون في الطبيعة؟<br>_byebse6ni Lammaaa would this be conditional? Lamma bakoon Fi el-6abee3a?_ | لما أكون<br>_Lamma akun_ | لما بكون → لما أكون | kept b- on akoon after lamma | B3+B8 | high | yes |
| 0904-28 | 1:02:23→1:02:30 | to make someone happy is آآá بيسبط.<br>_to make someone happy is aaaá byebse6._ | ببسّط.<br>_babse6._ | بيسبط → ببسّط | root ب dropped after the prefix (and he-form for 'I') | NEW-B18 | high | **missed** |
| 0904-11 | 36:23→36:37 | بسطه.<br>_بسطه._ | Basato, basatto. It's double t ... O and te.<br>_Basato, basatto. It's double t ... O and te._ | بسطه → بسطتُه | 'I made him happy' missing the I-ending -t before the object | B5 | medium | **missed** |
| 0904-12 | 43:31→43:36 | So yeah, بسّت، بسτι. بسّت.<br>_So yeah, بسّت, Bassτι. بسّت._ | No. ليش ما منحط إي بدنا إي ... إبست ... because it's three consonants or more.<br>_No. lesh ma منحط Ay biddna Ay ... إبست ... because it's three consonants or more._ | بسّت → ابسط | command needs the helper i- in front (three consonants) | B10 | high | **missed** |
| 0904-13 | 44:55→44:59 | like go have fun with them.<br>_like go have fun with them._ | لسه ... مش بي ببست ... not with this verb. It's with the other version.<br>_Lissa ... mesh بي ببست ... not with this verb. It's with the other version._ | ابسطهم (= have fun with them) → انبسط | used the make-happy verb for 'have fun'; that's the get-happy form | B12 | medium | **missed** |
| 0904-14 | 50:43→50:53 | is it nabasit or is it, nabasat? Or nabast?<br>_is it nabasit or is it, nabasat? Or nabast?_ | So now we do need to add something ... So inbasat.<br>_So now we do need to add something ... So inbasat._ | نبسط (past) → انبسط | past of the n- verb needs the i- in front | B5 | medium | **missed** |
| 0904-15 | 51:37→51:41 | hiya inbas- inbashatat.<br>_hiya inbas- inbashatat._ | Inbastat.<br>_Inbastat._ | انبسطتت → انبسطت | she-past ending mangled (extra syllable) | B5 | low | **missed** |
| 0904-17 | 53:36→53:39 | be embasattet, right? Embassatet il hafla.<br>_be embasattet, right? Embassatet il hafla._ | EMBASATI. I need a preposition. What was it? ... Bi or fi<br>_EMBASATI. I need a preposition. What was it? ... Bi or fi_ | انبسطت الحفلة → انبسطتي بالحفلة / في الحفلة | inbasat needs bi/fi before the thing enjoyed | D2 | high | **missed** |
| 0904-18 | 55:30→55:40 | In basatu Their trip. Safarhom. Safarhom.<br>_In basatu Their trip. Safarhom. Safarhom._ | Yeah but fee preposition shoo<br>_Yeah but fee preposition shoo_ | انبسطوا سفرهم → انبسطوا بسفرتهم | again left out the preposition after inbasat | D2 | high | **missed** |
| 0904-19 | 55:42→55:45 | al. Bi safar hom<br>_al. Bi safar hom_ | Safartom<br>_Safartom_ | سفرهم → سفرتهم | feminine noun (safra) needs -t before the owner ending | A3+A4 | medium | **missed** |
| 0904-U1 | 56:32→56:36 | Inti beten bestiti<br>_Inti beten bestiti_ | Betenbisti<br>_Betenbisti_ | بتنبسطتي → بتنبسطي | you(f) present got a past-style -ti ending | NEW-B18 | low | **missed** |
| 0904-21 | 58:36→58:52 | Ana, ana ban biscuit. ashann ihna aa taalam natal ana naataallam<br>_Ana, ana ban biscuit. ashann ihna aa taalam natal ana naataallam_ | Ihna bentallaams<br>_Ihna bentallaams_ | عشان احنا نتعلم → عشان احنا بنتعلم | dropped b- after 3ashan meaning 'because' (keeps b-) | B1+B3 | medium | **missed** |
| 0904-22 | 58:56→59:04 | bantalaam bass Hadi al filll<br>_bantalaam bass Hadi al filll_ | Hada<br>_Hada_ | هادي الفعل → هادا الفعل | feminine hadi with a masculine noun | A10 | high | yes |
| 0904-23 | 59:45→59:56 | Enjoy your day So command tensing Investii yomek<br>_Enjoy your day So command tensing Investii yomek_ | Bee Yomeek<br>_Bee Yomeek_ | انبسطي يومك → انبسطي بيومك | left out bi- after inbasat a third time | D2 | high | **missed** |

### 2026-09-05

_read all 834 turns 00:26-1:02:14; no chat lines in file; 00:26-06:02 is app demo talk (Medi recounts an OLD lazim ba'amal fix at 04:32 - not counted); Medi's Arabic mostly transcribed in Latin letters, so wrong/right pieces are rendered in Arabic script from those spellings_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0905-01 | 06:32→06:37 | I put enbustee. I put enbustee.<br>_I put enbustee. I put enbustee._ | انبسطتي ... It's not انبسطتي. Something is missing ... You forgot the double T and the في<br>_enbasa6ti ... It's not enbasa6ti. Something is missing ... You forgot the double T and the Fi_ | انبسطي → انبسطتي في | past 'you (f) enjoyed' missing the -ti ending, and dropped في after inbasat | B5+D2 | high | yes |
| 0905-02 | 09:56→10:00 | Yeah, enbasat, didn't I? ... el takheem basat<br>_Yeah, enbasat, didn't I? ... el takheem basat_ | You put انبسط. Does the تخيم have emotions? Does it get happy? ... بسط وحمس<br>_You put Enbese6. Does the تخيم have emotions? Does it get happy? ... بسط وحمس_ | انبسط → بسط | used 'get happy' (in-) for 'camping MADE everyone happy' | B12 | high | **missed** |
| 0905-03 | 11:16→11:21 | Is it, isn't it lisa ma bansabit? ... Ma lisa ma en-enbisit<br>_Is it, isn't it lisa ma bansabit? ... Ma lisa ma en-enbisit_ | This is I don't get happy yet ... It's a command ... ما تنبسط لسه<br>_This is I don't get happy yet ... It's a command ... ma tenbese6 Lissa_ | لسه ما بنبسط → ما تنبسط لسه | gave 'I don't get happy' instead of the negative command | B11 | high | **missed** |
| 0905-U1 | 11:53→11:59 | Ma teenbesit lisa ma ba'arif kul shey.<br>_Ma teenbesit lisa ma ba'arif kul shey._ | Ma, we don't know.<br>_Ma, we don't know._ | ما بعرف → ما منعرف | used 'I' form for 'we don't know' | NEW-B18 | medium | **missed** |
| 0905-04 | 15:51→16:03 | imbare ... Imbare lele or lele imbare<br>_imbare ... Imbare lele or lele imbare_ | ليلة امبارح<br>_lailet embare7_ | امبارح ليلة → ليلة امبارح | put 'yesterday' before 'night' in the idafa and no -t on leile | A3+A2 | medium | yes |
| 0905-05 | 18:39→18:46 | and anbisit, anbisit hafla- haflatik.<br>_and anbisit, anbisit hafla- haflatik._ | Mm-mm. We forgot something. ... في<br>_Mm-mm. We forgot something. ... Fi_ | انبسط حفلتك → انبسط في حفلتك | dropped في after inbasat (enjoy) | D2 | high | **missed** |
| 0905-06 | 19:48→19:57 | So ma'tanbisti halak.<br>_So ma'tanbisti halak._ | I'm gonna keep making you repeat until you say في on your own ... ما تنبسط بحالك ... That's في or ب<br>_I'm gonna keep making you repeat until you say Fi on your own ... ma tenbese6 b7aalak ... That's Fi or Bi_ | ما تنبسط حالك → ما تنبسط بحالك | dropped في/ب after inbasat again | D2 | high | yes |
| 0905-21 | 1:00:37→1:00:53 | I wasn't annoyed ... أنا انزعجت.<br>_I wasn't annoyed ... Ana nza3ajet._ | I didn't get.<br>_I didn't get._ | أنا انزعجت → أنا ما انزعجت | left out ما for 'I wasn't annoyed' | C4 | medium | **missed** |
| 0905-22 | 1:00:59→1:01:10 | اه، أنا، اه، زعلان.<br>_aah, Ana, aah, Za3laan._ | زعلت. ... أنا ما انزعجت، أنا زعلت.<br>_z3elet. ... Ana ma nza3ajet, Ana z3elet._ | أنا زعلان → أنا زعلت | used the present adjective for 'I was sad' instead of the past verb | B5 | medium | yes |
| 0905-07 | 20:31→20:51 | so anbisti fi laylak. ... So laylatik, laylatik.<br>_so anbisti fi laylak. ... So laylatik, laylatik._ | This your night. One night. ... بليلتك. Yes. ... ليلتك<br>_This your night. One night. ... bi-lailtak. Yes. ... ليلتك_ | ليلك → ليلتك | used lel (night, general) + -ak instead of leilt-ik (feminine -t before the ending) | A3 | medium | yes |
| 0905-08 | 22:59→23:09 | I remembered mazuj as annoying and moza- mozaj as annoyed<br>_I remembered mazuj as annoying and moza- mozaj as annoyed_ | بالعكس ... If it has this oo sound ... All of them is annoyed. Feeling the thing, not causing it.<br>_b-el-3aks ... If it has this oo sound ... All of them is annoyed. Feeling the thing, not causing it._ | مزعوج = annoying → مزعوج = annoyed, مزعج = annoying | swapped the feeling (maf3uul) and causing (muf3il) participle patterns | B15 | medium | **missed** |
| 0905-09 | 24:40→24:43 | So past tense, are you annoyed?<br>_So past tense, are you annoyed?_ | No, no, no. Are. The are is present. ... It's not do you get. It's just are you.<br>_No, no, no. Are. The are is present. ... It's not do you get. It's just are you._ | (past verb) → إنتي مزعوجة | planned a past verb for 'are you annoyed' instead of present adjective with no 'to be' | C1 | low | **missed** |
| 0905-10 | 29:25→29:31 | Feeya za'ajat-za'ajatek.<br>_Feeya za'ajat-za'ajatek._ | أزعجتك ... See? It's easier to say ... أزعجتك<br>_az3ajtak ... See? It's easier to say ... az3ajtak_ | زعجتك → أزعجتك | dropped the a- form Amal asked for; then said az'ajet without -ik | B12+D4 | low | yes |
| 0905-11 | 30:45→31:17 | az'aj, az'ajtu ... Az'ajtu.<br>_az'aj, az'ajtu ... Az'ajtu._ | أزعجتُ. You can't say أزعجتُ ... Doesn't sound right ... Yes, there is an h.<br>_أزعجتُ. You can't say أزعجتُ ... Doesn't sound right ... Yes, there is an h._ | أزعجتو → أزعجتوه | 'you guys annoyed him' missing the -h 'him' ending | D4 | medium | **missed** |
| 0905-12 | 34:06→34:19 | Ana ma, ma bitti, az'ajkum.<br>_Ana ma, ma bitti, az'ajkum._ | أزعجهم.<br>_أزعجهم._ | أزعجكم → أزعجهم | 'them' said as -kum (you pl) instead of -hum | D4 | high | **missed** |
| 0905-13 | 37:13→37:21 | So الولاد أزعجووو، أزعجووو،<br>_So el-wlad أزعجووو, أزعجووو,_ | أزعجوه؟<br>_أزعجوه?_ | أزعجوا → أزعجوه | 'annoyed him' missing the -h 'him' ending | D4 | medium | **missed** |
| 0905-U2 | 38:49→38:55 | هو بيزعج، بيزعجوني.<br>_Huwwe byez3ej, byez3ejuni._ | بيزعج، ... بيزعجني.<br>_byez3ej, ... byez3ejni._ | بيزعجوني → بيزعجني | plural 'they' form for 'he annoys me' | NEW-B18 | medium | **missed** |
| 0905-14 | 39:25→39:33 | Do I need to say like، هو بيزعج؟<br>_Do I need to say like, Huwwe byez3ej?_ | بدون هو. بس the هي conjugation. بس without the هي.<br>_bidoon Huwwe. Bass the heyye conjugation. Bass without the heyye._ | هو بيزعجني → بيزعجني | put a subject pronoun in front for 'it annoys me' | C9 | low | **missed** |
| 0905-U3 | 39:36→39:40 | Okay, so بي-بيزعج-بيزعجوني.<br>_Okay, so بي-byez3ej-byez3ejuni._ | بزعجني.<br>_بزعجني._ | بيزعجوني → بيزعجني | plural 'they' form again for 'it annoys me' | NEW-B18 | high | **missed** |
| 0905-15 | 48:08→48:13 | ما تنزعجي. ما زع-- ما تزع--<br>_ma tenze3ji. ma زع-- ma تزع--_ | تنزعجي. ... ما تنزعجي ... Cuz it's ززز، all of them together.<br>_tenze3ji. ... ma tenze3ji ... Cuz it's ززز, all of them together._ | ما تزعجي → ما تنزعجي | dropped the n: said 'don't annoy' for 'don't get annoyed' | B12 | medium | yes |
| 0905-16 | 49:06→49:20 | So this is without the N ... It does have an N. ma-matan, matanzajini.<br>_So this is without the N ... It does have an N. ma-matan, matanzajini._ | ليش؟ ... No. ... By me. ما تنزعجي ... ما تنزعجي مني<br>_lesh? ... No. ... By me. ma tenze3ji ... ma tenze3ji minni_ | ما تنزعجيني → ما تنزعجي مني | put 'me' as an ending on get-annoyed instead of مني; first said it has no n | D2+B12 | medium | yes |
| 0905-17 | 53:03→53:15 | Ana, so I get annoyed. It's present tense. Anabazaj. Na ba-banj.<br>_Ana, so I get annoyed. It's present tense. Anabazaj. Na ba-banj._ | Gets.<br>_Gets._ | بزعج → بنزعج | used 'I annoy' for 'I get annoyed' | B12 | medium | **missed** |
| 0905-18 | 53:24→53:49 | Oh, if. Iza. Iza akoon joan.<br>_Oh, if. Iza. Iza akoon joan._ | بس إذا بكون، مش أكون. ليش؟ ... If is conditional، but it doesn't take out the be.<br>_Bass Iza bakoon, mesh akun. lesh? ... If is conditional, but it doesn't take out the be._ | إذا أكون → إذا بكون | dropped b- on akoon after iza | B8+B3 | high | yes |
| 0905-19 | 56:01→56:17 | So I annoy who annoys me. أنا بزعج مين<br>_So I annoy who annoys me. Ana baz3ej meen_ | mean or what's the better one؟ The one who. يلي.<br>_mean or what's the better one? The one who. يلي._ | مين → اللي | used مين (who?) for 'the one who' | C7 | medium | **missed** |
| 0905-20 | 56:26→56:44 | اللي who annoys me. Okay. So، اه، بينزعجني.<br>_illi who annoys me. Okay. So, aah, byenze3ejni._ | ليش أن annoys me.<br>_lesh en annoys me._ | بينزعجني → بيزعجني | used get-annoyed (n) for 'annoys me' | B12 | high | **missed** |

### 2026-09-10

_read all 970 turns 00:03-1:02:40; no chat lines; no machine audit exists for this lesson (never audited) so every row is a machine miss; 00:03-01:42 is setup noise; 42:15-42:34 Medi talks to a passer-by; 57:27-end is mostly Amal explaining which verbs to learn_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0910-01 | 07:19→07:21 | Intayn ila tult.<br>_Intayn ila tult._ | تنتين إلا تلت.<br>_Tentain Illa talat._ | اتنين → تنتين | masculine 'two' in clock time instead of the feminine form | E2 | low | **missed** |
| 0910-02 | 10:34→10:44 | صلاح، صلاحني شوي. صلاحلي, helps to me, شوي.<br>_صلاح, صلاحني shwai. صلاحلي, helps to me, shwai._ | صلحني would be he fixed me. Like you, you were who's being fixed. ... Fixed for me، صلح لي.<br>_صلحني would be he fixed me. Like you, you were who's being fixed. ... Fixed for me, 9alla7 li._ | صلحني → صلح لي | put 'me' as an object ending instead of لي (for me) | D4+D3 | medium | **missed** |
| 0910-03 | 12:05→12:13 | um, ورداني<br>_um, ورداني_ | بدائية.<br>_بدائية._ | ورداني → وردية | masculine colour adjective on بلوزة | A8 | medium | **missed** |
| 0910-04 | 12:44→12:48 | اه، this is take Allah بيتي.<br>_aah, this is take Allah baiti._ | بِ أو فِي بيتي؟<br>_Bi Aw Fi baiti?_ | ضليت بيتي → ضليت ب بيتي | left out the preposition 'in' before بيتي | D1 | medium | **missed** |
| 0910-05 | 13:22→13:24 | وحدة كلمة صح و<br>_Wa7deh Kelme sa7 u_ | بس كلمة وحدة.<br>_Bass Kelme Wa7deh._ | وحدة كلمة → كلمة وحدة | put 'one' before the noun | E1+A7 | high | **missed** |
| 0910-06 | 16:02→16:05 | انزعجتي، اه، ما، ماضي.<br>_انزعجتي, aah, ma, Maadi._ | ليش ما؟ ... You were annoyed with me. You got annoyed with. Yes.<br>_lesh ma? ... You were annoyed with me. You got annoyed with. Yes._ | انزعجتي ما → انزعجتي مني | said ما where 'with me' (مني) was needed | D2 | low | **missed** |
| 0910-07 | 18:41→18:45 | إنتي تشكلك مزعوج.<br>_inti تشكلك Maz3ooj._ | إنتي أو انت؟<br>_inti Aw enti?_ | إنتي مزعوج → إنتي مزعوجة | masculine adjective with إنتي | A8 | high | **missed** |
| 0910-U1 | 19:58→20:03 | بازيجيني هدول اليوم.<br>_بازيجيني Hadoal El-youm._ | بزعجوني. بزعجوني. ... you could say بتزعجني بس مش بزعجني.<br>_بزعجوني. بزعجوني. ... you could say btez3ejni Bass mesh بزعجني._ | بيزعجني → بيزعجوني / بتزعجني | 'he' form verb for plural 'many things' | NEW-B18 | high | **missed** |
| 0910-08 | 20:40→20:43 | هدول اليوم.<br>_Hadoal El-youm._ | أيام.<br>_ayyaam._ | هدول اليوم → هدول الأيام | singular 'day' for 'these days' | A9 | high | **missed** |
| 0910-09 | 21:00→21:27 | إنتي متأكتي إلي إنتو ما ازعجتو.<br>_inti متأكتي eli intu ma ازعجتو._ | Why اللي؟ ... إنو مش اللي.<br>_Why illi? ... Eno mesh illi._ | اللي → إنو | used اللي for 'that' after 'sure' instead of إنو | C7 | high | **missed** |
| 0910-10 | 22:19→22:27 | إذا ما أشوفك... Is it تكوني or just مبسوطة?<br>_Iza ma ashufak... Is it تكوني or just Mabsoo6a?_ | بس مبسوطة إذا ما بشوف هيك.<br>_Bass Mabsoo6a Iza ma bashuf Heik._ | إذا ما أشوفك → إذا ما بشوفك | dropped b- after إذا ما | B3 | medium | **missed** |
| 0910-11 | 23:18→23:22 | إنزعجي، إنزعجي.<br>_إنزعجي, إنزعجي._ | So don't be. ... ما تنزعج<br>_So don't be. ... ma tenze3ej_ | انزعجي → ما تنزعجي | gave the positive command for 'don't be annoyed' | B11 | high | **missed** |
| 0910-12 | 25:07→25:13 | بيتايو، بيتايوك، بيتايوكي.<br>_بيتايو, بيتايوك, بيتايوكي._ | مم، يدايقوكي.<br>_mm, يدايقوكي._ | بيضايقوكي → يضايقوكي | kept b- after 'it wasn't their intention to' | B2 | low | **missed** |
| 0910-13 | 38:29→38:32 | كل أشيائي...<br>_kul أشيائي..._ | أشياءي نوع الإل.<br>_أشياءي Noa3 el-el._ | الأشيائي → أشيائي | el- on a noun that has a possessive ending | A4+A1 | low | **missed** |
| 0910-14 | 39:55→39:57 | كاسته. كاسته.<br>_كاسته. كاسته._ | كساته.<br>_كساته._ | كاسته → كاساته | singular 'his cup' for 'his cups' | A9 | medium | **missed** |
| 0910-15 | 40:37→40:43 | كاسته، آآمم، ان-انكسر.<br>_كاسته, آآمم, en-nkasar._ | كاسه. ... انكسرت. ... كاسه انكسرت.<br>_كاسه. ... انكسرت. ... كاسه انكسرت._ | انكسر → انكسرت | masculine past ending for a feminine noun (the cup) | NEW-B18 | high | **missed** |
| 0910-16 | 43:35→43:35 | or كان عمرها أو عمرها كان؟ كانت. ... كانت، right؟<br>_or kaan عمرها Aw عمرها kaan? kaanat. ... kaanat, right?_ | Both، بس كان عمر is better. كان عمرها. ... لأ، كان عمرها صح.<br>_Both, Bass kaan عمر is better. kaan عمرها. ... la, kaan عمرها sa7._ | كانت عمرها → كان عمرها | made كان feminine to match 'she' instead of عمر | B6 | medium | **missed** |
| 0910-17 | 51:43→52:05 | أنا ما بكسر، اشي ... Never broken anything.<br>_Ana ma bakser, eshi ... Never broken anything._ | بكسر أو كسرت؟ ... لا، who said that? ... The only thing with أبداً is the consistent thing is ما.<br>_bakser Aw kasaret? ... la, who said that? ... The only thing with Abadan is the consistent thing is ma._ | أبدًا ما بكسر → أبدًا ما كسرت | present verb for 'never broken' (thought أبدًا needs present) | B5+C4b | high | **missed** |
| 0910-18 | 53:45→53:49 | أنا نِمِت مش منيح.<br>_Ana nemet mesh mneeh._ | Or ما نمت منيح.<br>_Or ma nemet mneeh._ | نمت مش منيح → ما نمت منيح | negated with مش after the verb instead of ما before it | C4 | low | **missed** |
| 0910-19 | 54:43→54:51 | الف-الفعلات. الفعلات إن.<br>_alf-الفعلات. الفعلات en._ | أفعال.<br>_af3al._ | الفعلات → الأفعال | made a regular -aat plural of فعل instead of the broken plural | A9b | high | **missed** |

### 2026-09-11

_read all 937 turns 00:41-1:02:26 (no chat lines). Gaps: Medi's Arabic mostly '[speaking Arabic]' 18:13-22:42, 30:33-31:57, 33:14-36:33; Amal '[speaks Arabic]' 49:44-56:28; 46:02-58:37 Medi in Latin script._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0911-01 | 05:01→05:05 | آآآ، الشمال الـ، روسيا the, the north of Russia. الشمال.<br>_aaa, el-Shmaal el, Roosya the, the north of Russia. el-Shmaal._ | بس، بس شمال روسيا.<br>_Bass, Bass Shmaal Roosya._ | الشمال الـ روسيا → شمال روسيا | put el- on the first word of an idafa | A2 | high | yes |
| 0911-02 | 09:29→09:32 | is it أنجم؟ I don't know. أنجم، نجوم،<br>_is it أنجم? I don't know. أنجم, nujoom,_ | نجوم.<br>_nujoom._ | أنجم → نجوم | wrong broken plural of نجمة | A9 | medium | **missed** |
| 0911-03 | 10:18→10:35 | قريب، قريبًا مني.<br>_2areeb, 2areeban minni._ | What's the، what's-- وشو جمع غريب؟ ... غراب.<br>_What's the, what's-- w-shu Jame3 8areeb? ... غراب._ | قريب → قراب | singular adjective for plural cities; she asked for the plural | A9 | medium | **missed** |
| 0911-04 | 12:45→12:48 | آآآ، ع الـ-- أول الكلمة.<br>_aaa, ع el-- Awal el-kilme._ | لا، أول الكلمة.<br>_la, Awal el-kilme._ | ع الـ أول الكلمة → أول الكلمة | el- in front of أول (superlative/idafa head) | C3+A2 | high | yes |
| 0911-05 | 13:01→13:14 | آآآ، بر-- بخرب. بخرب<br>_aaa, بر-- ba5rab. ba5rab_ | مم. It's not بخرب yet. It's بخرب.<br>_mm. It's not ba5rab yet. It's ba5rab._ | بخرّب → بخرَب | gave the doubled (make-X) verb instead of the plain one from خربان | B12 | medium | **missed** |
| 0911-06 | 16:03→16:05 | آآآ، هي خربات.<br>_aaa, heyye خربات._ | mm-hmm. خربت.<br>_mm-hmm. 5arabet._ | هي خربات → هي خربت | wrong past ending for هي | B5 | high | **missed** |
| 0911-07 | 20:05→20:11 | (not transcribed) because<br>_(not transcribed) because_ | بس still هذا الفعل الثاني. أمم، not بخرب. بخرب that would be.<br>_Bass still Haada el-fi3el الثاني. umm, not ba5rab. ba5rab that would be._ | بخرّب → بخرَب | used the make-X verb where he meant 'it stops working' | B12 | low | **missed** |
| 0911-08 | 20:48→21:13 | Um, [speaking Arabic]<br>_Um, [speaking Arabic]_ | بتستعمل.<br>_بتستعمل._ | (untranscribed you-form) → بتستعمل | wrong person on the present verb (you instead of she) | NEW-B18 | low | **missed** |
| 0911-09 | 21:19→21:25 | Uh, but [speaking Arabic] oh, that's right, it's she and not you. [speaking Arabic]<br>_Uh, but [speaking Arabic] oh, that's right, it's she and not you. [speaking Arabic]_ | بتستعمله.<br>_بتستعمله._ | بتستعمل → بتستعمله | missing pointer ending after fronted كل إشي | C2 | medium | **missed** |
| 0911-10 | 21:39→21:46 | [speaking Arabic] / Yeah, [speaking Arabic]<br>_[speaking Arabic] / Yeah, [speaking Arabic]_ | بس. بيخرب. بس بيخرب. No, because it breaks ... So كل إشي بتستعمله بيخرب.<br>_Bass. bi5arrib. Bass bi5arrib. No, because it breaks ... So kul eshi بتستعمله bi5arrib._ | (pointer on بيخرب) → بيخرب | added the pointer ending to the second verb too | C2 | low | **missed** |
| 0911-11 | 25:00→25:08 | ما، ما تفتحي. / ما بهتي، ما بهتي. بي-- بتفتحي<br>_ma, ma tefta7i. / ma بهتي, ma بهتي. بي-- btefta7i_ | With B. ما بتحطي...<br>_With B. ma bet7utti..._ | إذا ما تفتحي → إذا ما بتحطي | dropped b- on the present verb after إذا ما | B1 | medium | yes |
| 0911-12 | 30:20→30:32 | [يضحك] لازم. اه، خرب<br>_[يضحك] Laazem. aah, 5arab_ | عزومة is feminine or masculine؟ ... خربت.<br>_3azoome is feminine or masculine? ... 5arabet._ | (العزومة) خرب → خربت | masculine verb for feminine عزومة | NEW-B18 | high | yes |
| 0911-13 | 40:15→40:22 | شو خرب? ... جلايك.<br>_shu 5arab? ... jallaayak._ | جلاية؟ So<br>_جلاية? So_ | جلايك → جلايتك | dropped the feminine -t before the possessive ending | A3 | high | **missed** |
| 0911-14 | 42:23→42:40 | مش قصدهم إنّه... / مش كان<br>_mesh 2azdhom enno... / mesh kaan_ | مش، مش ... or it's past also. / Not مش. If you use can. Not can.<br>_mesh, mesh ... or it's past also. / Not mesh. If you use can. Not can._ | مش قصدهم / مش كان → ما كان قصدهم | used مش with a verb and left out past كان | C4+B6 | high | **missed** |
| 0911-15 | 42:56→43:01 | kharabu.<br>_kharabu._ | So، في عندنا خلاص ما can is a verb. Because can and then the verb after it should be what؟<br>_So, Fi 3inna خلاص ma can is a verb. Because can and then the verb after it should be what?_ | kharabu (past) → yecharbu (present) | past verb after ما كان قصدهم instead of a bare present | B2 | low | **missed** |
| 0911-16 | 43:48→44:03 | Il, iljao sh-- Iljao shoub. ... Iljao shoub,<br>_Il, iljao sh-- Iljao shoub. ... Iljao shoub,_ | الشوب the hot weather.<br>_el-Shoab the hot weather._ | iljao shoub (a sentence) → iljao ilshoub (phrase) | noun+adjective as a sentence where a phrase subject was needed | A7 | low | yes |
| 0911-17 | 44:39→44:56 | it would be echarrab, echarrbi.<br>_it would be echarrab, echarrbi._ | So it's بخرررب. There is a double medal here. / No. خرب. / When do I not put the a in command؟<br>_So it's بخرررب. There is a double medal here. / No. 5arab. / When do I not put the a in command?_ | echarrab, echarrbi → خرّب | added the initial vowel to a doubled-middle command | B10 | high | **missed** |
| 0911-18 | 53:03→53:11 | bidullu, um, yikharabu. Keeps, uh, yikharabu?<br>_bidullu, um, yikharabu. Keeps, uh, yikharabu?_ | Mm-mm, no. [speaks Arabic] ... So they are what's breaking.<br>_Mm-mm, no. [speaks Arabic] ... So they are what's breaking._ | yikharrabu → (plain) بيخربوا | make-X verb where the keys themselves stop working | B12 | medium | **missed** |
| 0911-19 | 53:43→53:47 | bitakhrobi. Bitakhrib.<br>_bitakhrobi. Bitakhrib._ | Did you?<br>_Did you?_ | bitakhrib (present) → kharabtihum (past) | present tense for 'did you break them' | B5 | medium | **missed** |
| 0911-20 | 56:29→56:55 | rah yitkhar-- rah titkharabi. / Rah atkharabt.<br>_rah yitkhar-- rah titkharabi. / Rah atkharabt._ | No two T. Why two Ts؟ شوربة is feminine. So... / one T. / اه، راح تخربيها.<br>_No two T. Why two Ts? Shoraba is feminine. So... / one T. / aah, raa7 تخربيها._ | راح تتخربي → راح تخربيها | extra t- (reflexive shape) and no -ha for feminine شوربة | D4+B12 | high | yes |
| 0911-21 | 57:29→57:32 | rah yikhrab.<br>_rah yikhrab._ | Yes, بس we're talking about شوربة. So...<br>_Yes, Bass we're talking about Shoraba. So..._ | راح يخرب → راح تخرب | masculine verb for feminine شوربة | NEW-B18 | high | **missed** |

### 2026-09-14

_read all 1041 lines (996 spoken turns + 45 chat) 00:02-1:02:40. Medi often in Latin script (12:00-23:30, 40:00-53:50); STT garbles Amal's اخترت as اشتريت; 43:59-45:38 Medi away._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0914-01 | 02:58→03:09 | اختارت، uh، اختارت أدل...<br>_5taret, uh, 5taret adall..._ | اشتريت. ما فتاك، اشتريت.<br>_shtarait. ma فتاك, shtarait._ | اختارت → اخترت | used the she-form past of اختار for 'I chose' | B5 | medium | **missed** |
| 0914-02 | 03:26→03:32 | اختارت أدل بيتي.<br>_5taret adall baiti._ | في بيتي.<br>_Fi baiti._ | أدل بيتي → أدل في بيتي | left out the preposition after ضل (stay at home) | D1 | high | **missed** |
| 0914-03 | 05:17→05:22 | هدرت-- أنا هدرت؟ / أنا هدرت<br>_هدرت-- Ana هدرت? / Ana هدرت_ | حضرتها.<br>_حضرتها._ | أنا حضرت → حضرتها | no object ending for 'I attended it' (the game) | D4 | low | **missed** |
| 0914-04 | 06:44→06:51 | ص-خطار-- اختار-اختارينا--<br>_ص-خطار-- E5tar-اختارينا--_ | اخترنا.<br>_اخترنا._ | اختارينا → اخترنا | wrong past we-form of a hollow verb | B5 | high | **missed** |
| 0914-05 | 08:15→08:18 | The es-es-اسمي.<br>_The es-es-esmi._ | أسماء.<br>_asmaa2._ | اسمي → أسماء | wrong plural of اسم | A9 | medium | yes |
| 0914-06 | 08:35→08:51 | سهلي-- سهلات.<br>_سهلي-- سهلات._ | We will say the nouns it's easy to remember them. So it's easy. We don't need to tie it back to أسماء. / So just سهل to remember them.<br>_We will say the nouns it's easy to remember them. So it's easy. We don't need to tie it back to asmaa2. / So just Sahel to remember them._ | سهلات → سهل (نتذكرهم) | made 'easy' agree with the fronted plural instead of impersonal سهل + pointer | C2+A8 | medium | **missed** |
| 0914-U-01 | 09:14→09:21 | So أتذكرهم.<br>_So أتذكرهم._ | صح. mm-hmm. So it's either you or we. 'Cause it's general.<br>_sa7. mm-hmm. So it's either you or we. 'Cause it's general._ | أتذكرهم → نتذكرهم | I-form in a general statement; needs we/you | NEW-B18 | medium | **missed** |
| 0914-08 | 14:11→14:53 | abel ma tistallehi shu. ... iserti.<br>_abel ma tistallehi shu. ... iserti._ | صح. Or how do I use into here? / And what do I add to the verb?<br>_sa7. Or how do I use into here? / And what do I add to the verb?_ | shu kasarti → illi kasartih | used shu instead of illi and no pointer ending | C7+C2 | low | **missed** |
| 0914-07 | 14:34→14:38 | uh, en-enkis-enkistri.<br>_uh, en-enkis-enkistri._ | You broke. You broke the thing that you have to fix. Not you were broken.<br>_You broke. You broke the thing that you have to fix. Not you were broken._ | انكسرتي → كسرتي | used the get-X (n-) verb instead of the plain break-X | B12 | high | **missed** |
| 0914-09 | 16:28→16:30 | Eid El Sadeeki.<br>_Eid El Sadeeki._ | Hands.<br>_Hands._ | Eid (hand) → Edayn (min idain) | singular where 'one of the hands' needs the dual/plural | A9 | medium | **missed** |
| 0914-10 | 16:37→16:40 | Edayn El Sadeeki.<br>_Edayn El Sadeeki._ | صديقي. No L 'cause there's ي.<br>_sadeeqi. No L 'cause there's ي._ | El Sadeeki → صديقي | el- on a noun that already has a possessive ending | A4 | high | **missed** |
| 0914-11 | 17:28→17:47 | enkeser, enkeseru. / enkeser.<br>_enkeser, enkeseru. / enkeser._ | One feminine. / Mm. Feminine.<br>_One feminine. / Mm. Feminine._ | enkeser / enkeseru → enkeserat | verb didn't agree with وحدة (one feminine hand) | NEW-B18 | high | **missed** |
| 0914-12 | 18:13→18:15 | Lama, uh, leb-lebena-<br>_Lama, uh, leb-lebena-_ | We were playing. Where is the were? / كنّا. / نلعب.<br>_We were playing. Where is the were? / kunna. / نلعب._ | lebena (we played) → كنّا نلعب | plain past for 'we were playing'; needs كان + present | B7 | high | **missed** |
| 0914-13 | 23:46→23:49 | El darajat hararah.<br>_El darajat hararah._ | درجة الحرارة.<br>_Daraja el-7araara._ | El darajat hararah → درجة الحرارة | el- on the first word of an idafa instead of the second | A2 | high | yes |
| 0914-14 | 26:13→26:20 | الـ مفضل لي-- أو just مفضل لي. Right? No El.<br>_el Mufaddal li-- Aw just Mufaddal li. Right? No El._ | المفضل عندي.<br>_el-Mufaddal 3endi._ | مفضل لي → المفضل عندي | wrong preposition (لي) and dropped el- on المفضل | D1+A1 | medium | **missed** |
| 0914-15 | 31:54→32:03 | شو بينزعج-- شو بين-بينزعجك؟<br>_shu byenze3ej-- shu Bein-byenze3jak?_ | شو بيزعجك؟ It's annoying you. مش...<br>_shu byez3ejak? It's annoying you. mesh..._ | شو بينزعجك → شو بيزعجك | get-X (n-) verb where the thing annoys you | B12 | high | **missed** |
| 0914-16 | 32:49→34:05 | ممكن... uh, تزعجنا.<br>_Mumken... uh, tez3ejna._ | زعجناها. ... It's neither. It's just زعجنا. Only the I and you male take the it.<br>_زعجناها. ... It's neither. It's just za3ajna. Only the I and you male take the it._ | تزعجنا → زعجناها | t- prefix on the past we-form, and no -ها object | B5+D4 | high | yes |
| 0914-17 | 35:06→35:17 | بينزعج-- Uh, no, بتنزعج، بتنزعجوني.<br>_byenze3ej-- Uh, no, btenze3ej, btenze3juni._ | You annoy me. / Yes, you guys annoy me. مش be annoyed by.<br>_You annoy me. / Yes, you guys annoy me. mesh be annoyed by._ | بتنزعجوني → بتزعجوني | get-X (n-) verb where 'you annoy me' needs the plain verb | B12 | high | **missed** |
| 0914-18 | 36:52→36:55 | bezaj,<br>_bezaj,_ | Gets annoyed.<br>_Gets annoyed._ | bezaj (annoys) → bienzaj (gets annoyed) | plain verb where 'gets annoyed' needs the n- form | B12 | low | **missed** |
| 0914-19 | 40:16→40:18 | so in besit, in besiti be wa'ati.<br>_so in besit, in besiti be wa'ati._ | Your time. / انبسط بوقتك.<br>_Your time. / Enbese6 bwa2tak._ | بوقتي → بوقتك | my-ending where 'your time' was needed | A4 | medium | yes |
| 0914-20 | 41:06→41:10 | Babtatik?<br>_Babtatik?_ | ماضي. / بسطتك.<br>_Maadi. / basa6tek._ | babsetek (present) → بسطتك | present for 'did I make you happy' | B5 | high | **missed** |
| 0914-21 | 43:20→43:24 | آآآ، انبسطتي قهوتك؟<br>_aaa, enbasa6ti 2ahwetak?_ | في كمان. في إشي ناقص. / بس قهوتك. What does it need? / بقهوتك.<br>_Fi Kamaan. Fi eshi ناقص. / Bass 2ahwetak. What does it need? / bi-2ahwtak._ | انبسطتي قهوتك → انبسطتي بقهوتك | dropped انبسط's fixed preposition بـ | D2 | high | yes |
| 0914-22 | 45:50→45:53 | آه، أنا أريجا، بارجا.<br>_aaah, Ana أريجا, بارجا._ | Mm-mm. رجعت. أنا رجعت.<br>_Mm-mm. رجعت. Ana رجعت._ | بارجع → رجعت | present verb for 'I'm back'; Arabic uses the past | B5 | medium | **missed** |
| 0914-23 | 47:49→47:52 | um, they made us happy with the بسطنا.<br>_um, they made us happy with the بسطنا._ | لا، لا. We were happy with them. يعني we got happy.<br>_la, la. We were happy with them. Ya3ni we got happy._ | بسطنا → انبسطنا | make-X verb where 'we got happy' needs the n- form | B12 | medium | **missed** |
| 0914-24 | 50:30→50:32 | inti fitbasti.<br>_inti fitbasti._ | إنتي تنبسطي.<br>_inti تنبسطي._ | fitbasti → بتنبسطي | wrong present shape of the n- verb | B12 | low | **missed** |
| 0914-25 | 53:45→53:48 | Ma, uh, il, il hiflek.<br>_Ma, uh, il, il hiflek._ | بالحفلة.<br>_b-el-7afle._ | il hiflek → بالحفلة | dropped انبسط's preposition بـ | D2 | high | yes |
| 0914-26 | 55:36→55:39 | هو بينبسط مشاويك.<br>_Huwwe byinbisit مشاويك._ | be مش a weird.<br>_be mesh a weird._ | بينبسط مشاويك → بينبسط بمشاويرك | dropped the بـ after انبسط (and wrong plural of مشوار) | D2+A9 | low | **missed** |
| 0914-27 | 56:31→56:44 | هي، uh، بتنسط-- بتنبسط.<br>_heyye, uh, بتنسط-- btinbisit._ | Did she make you happy؟ / did.<br>_Did she make you happy? / did._ | بتنبسط → بسطتك | get-X present where 'did she make you happy' needs make-X past | B5+B12 | medium | **missed** |
| 0914-28 | 58:10→58:38 | بن...<br>_بن..._ | There's a verb before it. / you added a be. You wanted to add a be. / him.<br>_There's a verb before it. / you added a be. You wanted to add a be. / him._ | بن(بسط) → نبسطه | b- on the verb after جربنا, and no -ه object | B2+D4 | medium | **missed** |

### 2026-09-15

_read all 1097 turns 00:36-1:07:03; Medi's Arabic often Latin-script STT; no untranscribed gaps_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0915-01 | 05:32→05:40 | uh نفس الـ امبارح.<br>_uh Nafs el embare7._ | Yeah, we don't say that yesterday. Just yesterday is its own...<br>_Yeah, we don't say that yesterday. Just yesterday is its own..._ | الـ امبارح → امبارح | put el- on imbaare7 | A1 | high | **missed** |
| 0915-02 | 06:18→06:21 | Aji.<br>_Aji._ | أجا.<br>_aja._ | أجي → أجا | wrong past form of 'came' | B5 | medium | **missed** |
| 0915-03 | 06:26→06:30 | Aja min beiti wu,<br>_Aja min beiti wu,_ | ألا، أجا على.<br>_Illa, aja 'ala._ | أجا من → أجا على / أجا عندي | wrong preposition with aja (came to) | D2 | high | **missed** |
| 0915-04 | 12:37→12:45 | بتكسر. ما بتكسري.<br>_btekser. ma btekseri._ | ما تكسري.<br>_ma tekseri._ | ما بتكسري → ما تكسري | kept b- in a negative command | B11 | high | **missed** |
| 0915-05 | 13:18→13:22 | كسرتوا.<br>_كسرتوا._ | كسرته.<br>_كسرته._ | كسرتوا → كسرته | 'I broke it' came out like 'you (pl) broke' | B5+D4 | low | **missed** |
| 0915-06 | 15:22→15:35 | شو كسرهم. No. شو نكس-- uh, انكسرهم.<br>_shu kasarhom. No. shu نكس-- uh, انكسرهم._ | شو كسرهم؟<br>_shu kasarhom?_ | انكسرهم → كسرهم | used the get-broken (in-) form with an object | B12 | high | **missed** |
| 0915-07 | 16:22→16:25 | شي. شي.<br>_shi. shi._ | تكسري. What's plural of أشي إشي؟ ... تكسري أشياء.<br>_tekseri. What's plural of eshi eshi? ... tekseri أشياء._ | شي → أشياء | singular 'thing' for 'things' | A9 | high | **missed** |
| 0915-08 | 17:12→17:20 | اكسرو. اكسرو؟ Oh, ما تكسرو.<br>_ekseru. ekseru? Oh, ma teksru._ | ما تكسره. ... Well, I wrote تكسري.<br>_ma تكسره. ... Well, I wrote tekseri._ | ما تكسرو → ما تكسري(ه) | masculine negative command for a woman | B11 | low | **missed** |
| 0915-25 | 1:00:01→1:00:08 | Zakaretik. ... Zakaretno.<br>_Zakaretik. ... Zakaretno._ | I reminded him. ... Zakarto.<br>_I reminded him. ... Zakarto._ | ذكرتك / ذكرتنو → ذكّرته | wrong object ending for 'him' | D4 | medium | yes |
| 0915-26 | 1:01:26→1:01:30 | it zakara, uh, it zakarooni.<br>_it zakara, uh, it zakarooni._ | Didn't. Very, very, very right.<br>_Didn't. Very, very, very right._ | اتذكروني → ما اتذكروني | dropped ma for 'didn't' | C4 | medium | **missed** |
| 0915-27 | 1:02:25→1:02:32 | ma hazakar. Ma id zakar.<br>_ma hazakar. Ma id zakar._ | Ma bietzakar.<br>_Ma bietzakar._ | ما يتذكر → ما بيتذكر | dropped b- on a plain present | B1 | high | yes |
| 0915-28 | 1:02:40→1:03:02 | Uh, Asayam?<br>_Uh, Asayam?_ | Asma. As it's general, so what do we add? ... Il asma.<br>_Asma. As it's general, so what do we add? ... Il asma._ | أسامي / أسماء → الأسماء | no el- on a general noun | A1 | high | **missed** |
| 0915-29 | 1:05:26→1:05:40 | el kul,<br>_el kul,_ | الكل؟ ... كل الكلمات؟ كل شي. You could say كل شي.<br>_El-kul? ... kul الكلمات? kul shi. You could say kul shi._ | الكل → كل شي | el-kul for 'everything' | A11 | medium | yes |
| 0915-09 | 20:51→20:54 | qasarat.<br>_qasarat._ | Kasat.<br>_Kasat._ | كاسرات → كاسات | wrong plural of kaase (cup) | A9 | high | **missed** |
| 0915-10 | 27:31→27:35 | واحدة ال-- واحد الولاد.<br>_wa7de el-- Wa7ad el-wlad._ | واحد of the children ... or of them. One of them. / منهم.<br>_Wa7ad of the children ... or of them. One of them. / minhom._ | واحد الولاد → واحد منهم / واحد من الولاد | left out min in 'one of' | D1 | medium | **missed** |
| 0915-11 | 29:44→29:45 | راي.<br>_Ra2ey._ | رأيي.<br>_ra2yi._ | راي → رأيي | no 'my' ending on ra2y | A4 | medium | **missed** |
| 0915-12 | 31:39→31:42 | طيرنا، طيرنا.<br>_طيرنا, طيرنا._ | should change. present. مدارع. ... نغير.<br>_should change. present. mudaare3. ... نغير._ | طيرنا / بنغير → نغير | after laazem needs the bare present verb | B2 | medium | **missed** |
| 0915-13 | 33:23→33:29 | تغير، تغير.<br>_et8ayyar, et8ayyar._ | very close. بس السيارة، السيارة feminine or masculine؟ غيرت.<br>_very close. Bass el-Seyyara, el-Seyyara feminine or masculine? 8ayyaret._ | طيارتي تغير → طيارتي تغيرت | masculine verb for feminine tayyaara | NEW-B18 | high | **missed** |
| 0915-14 | 35:33→35:43 | Program shift feminine.<br>_Program shift feminine._ | Program is masculine.<br>_Program is masculine._ | برنامج (as feminine) → برنامج masculine → تغير | treated barnaamej as feminine | NEW-B18 | medium | yes |
| 0915-15 | 40:20→40:30 | يتغيروا.<br>_يتغيروا._ | يتغير، يتغيروا. ... لازم تغيروا would be should have been changed.<br>_يتغير, يتغيروا. ... Laazem تغيروا would be should have been changed._ | تغيروا → يتغيروا | past form after laazem | B2 | medium | **missed** |
| 0915-16 | 42:50→42:56 | ما تغير حالك.<br>_ma et8ayyar 7aalak._ | تغير أو تغيري حالك ... Make the gender consistent. / ما تغيري حالك.<br>_et8ayyar Aw t8ayyri 7aalak ... Make the gender consistent. / ma t8ayyri 7aalak._ | ما تغير حالك → ما تغيري حالك | masculine command to a woman | B11 | high | yes |
| 0915-17 | 45:19→45:35 | change, uh, بتغيير. No, بـ-بتغيير.<br>_change, uh, بتغيير. No, Bi-بتغيير._ | It did change. Why did it change? It did change.<br>_It did change. Why did it change? It did change._ | بتغير → تغير | present for 'why did it change' | B5 | high | **missed** |
| 0915-18 | 47:55→47:58 | تصوريني. That's تصوريني لو سمحتي.<br>_t9awwrini. That's t9awwrini law samahti._ | Again. ... Photograph me. You photograph me.<br>_Again. ... Photograph me. You photograph me._ | تصوريني → صوريني | present form instead of the command | B10 | medium | **missed** |
| 0915-19 | 49:41→49:42 | Kam sawar.<br>_Kam sawar._ | That's the error I was talking about. So cam takes singular.<br>_That's the error I was talking about. So cam takes singular._ | كم صور → كم صورة | plural noun after kam | E5 | high | yes |
| 0915-20 | 51:01→51:13 | wasn't it just bitsawri, bitsawri kateer?<br>_wasn't it just bitsawri, bitsawri kateer?_ | إذا بتصور أو بتتصوري.<br>_Iza bti9awwer Aw بتتصوري._ | بتصوري → بتتصوري | 'photograph' form for 'get photographed' | B12 | high | **missed** |
| 0915-21 | 54:06→54:40 | fi hada yaref ... uh, bisawar<br>_fi hada yaref ... uh, bisawar_ | No Bs either way. بيعرف يصور or بيعرف كيف يصور.<br>_No Bs either way. بيعرف يصور or بيعرف Keef يصور._ | يعرف ... بيصور → بيعرف يصور | b- missing on ya3ref and added on the second verb | B2+B1 | medium | **missed** |
| 0915-22 | 55:24→55:28 | livil-- oh my God.<br>_livil-- oh my God._ | First do the left, left past. Make it past.<br>_First do the left, left past. Make it past._ | لما ... (present) → لما لفّيت | present after lamma for a past trip | B5 | medium | **missed** |
| 0915-23 | 56:21→56:32 | How do you feel with this shuba test or...?<br>_How do you feel with this shuba test or...?_ | شو بتحس ... what do you normally feel. بس ... now? We would say شو حاسس which is progressive.<br>_shu بتحس ... what do you normally feel. Bass ... now? We would say shu حاسس which is progressive._ | شو بتحس → شو حاسس | b-verb instead of participle for a feeling right now | B15 | low | **missed** |
| 0915-24 | 59:14→59:27 | Uh, Zakarini sajibi<br>_Uh, Zakarini sajibi_ | To bring, but who's bringing? You are bringing. / I bring.<br>_To bring, but who's bringing? You are bringing. / I bring._ | تجيبي → أجيب | wrong person on the second verb ('remind me to bring') | NEW-B18 | medium | **missed** |

### 2026-09-16

_read all 1038 turns 01:17-1:09:56; untranscribed Medi Arabic at 27:01-27:45, 28:55-31:33, 1:02:47-1:08:20 ([speaking Arabic]) so fixes there rest on Amal's side only_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0916-01 | 04:40→04:51 | La-lazim, um, 'amalitha or, uh, ta'alamitha,<br>_La-lazim, um, 'amalitha or, uh, ta'alamitha,_ | كان لازم أعلمها كل شي.<br>_kaan Laazem a3allemha kul shi._ | لازم تعلمتها → كان لازم أعلمها | no kaan for 'had to', past/learn form instead of bare 'teach' | B16+B12 | high | yes |
| 0916-02 | 09:43→09:47 | this a T? بنسـ-- بنسوار أو بسوار؟<br>_this a T? بنس-- بنسوار Aw بسوار?_ | No، بصور، but صور. ... the only one that was an was بكسر، بانكسر.<br>_No, basawwer, but suwar. ... the only one that was an was bakser, بانكسر._ | بنصور → بصور / بتصور | n-form for photograph (its pair is the t-form) | B12 | medium | **missed** |
| 0916-03 | 13:41→13:49 | to behamasu ki--<br>_to behamasu ki--_ | No، it's present، بس it's one، not group of things. / شو بيحمسك؟<br>_No, it's present, Bass it's one, not group of things. / shu بيحمسك?_ | بيحمسوك → بيحمسك | plural verb for singular 'what' | NEW-B18 | medium | **missed** |
| 0916-04 | 14:10→14:20 | behamsini-- behamsni.<br>_behamsini-- behamsni._ | Made. ... Past. He made me excited.<br>_Made. ... Past. He made me excited._ | بيحمسني → حمّسني | present for 'he made me excited' | B5 | high | **missed** |
| 0916-05 | 15:39→16:03 | hamasi. ... tetamasi.<br>_hamasi. ... tetamasi._ | It's the wrong verb. It's get excited, not excite. ... No T, just one T.<br>_It's the wrong verb. It's get excited, not excite. ... No T, just one T._ | حمسي / تتحمسي → تحمّسي | causative for 'get excited', then doubled t- on the command | B12+B10 | high | **missed** |
| 0916-06 | 16:53→17:47 | Lesh mabuchit hamasi.<br>_Lesh mabuchit hamasi._ | we are using the adjective here because it's are ... Aren't you excited? Meaning now.<br>_we are using the adjective here because it's are ... Aren't you excited? Meaning now._ | ليش ما بتتحمسي → ليش مش متحمسة | habit verb instead of participle for 'aren't you excited (now)' | B15+C4 | high | **missed** |
| 0916-20 | 1:03:44→1:03:47 | Uh, so is it alawain?<br>_Uh, so is it alawain?_ | It's لوين. We added to the question to always. ... From to is la.<br>_It's لوين. We added to the question to always. ... From to is la._ | على وين / وين → لوين | 'to where' needs la- on wein | C10 | medium | **missed** |
| 0916-21 | 1:05:33→1:05:35 | Feminine, right?<br>_Feminine, right?_ | ورقة is feminine and one. ورق is plural.<br>_Waraqa is feminine and one. ورق is plural._ | ورقة → ورق | singular waraqa for 'the papers' | A9 | low | **missed** |
| 0916-22 | 1:07:08→1:07:21 | [speaking Arabic] ... What'd I say?<br>_[speaking Arabic] ... What'd I say?_ | عندنا يعني لما عندنا. ... عندهم.<br>_3inna Ya3ni Lamma 3inna. ... 3indhom._ | عندهم → عندنا | wrong person ending on 3ind (they vs we) | D3 | medium | **missed** |
| 0916-23 | 1:07:45→1:07:50 | nifarijini or nifarj-? It's nifariji, nifariji.<br>_nifarijini or nifarj-? It's nifariji, nifariji._ | فرجيهم.<br>_farjihom._ | نفرجيني → نفرجيهم | wrong object ending ('me' for 'them') | D4 | medium | yes |
| 0916-07 | 22:00→22:03 | hamasi akthar.<br>_hamasi akthar._ | Me. Excite me.<br>_Me. Excite me._ | حمسي → حمسيني | left off the -ni object | D4 | high | **missed** |
| 0916-08 | 22:46→22:48 | ziyada.<br>_ziyada._ | Let's put it at the after.<br>_Let's put it at the after._ | هم زيادة ... → هم تحمسوا زيادة | put ziyada before the verb | C9 | medium | **missed** |
| 0916-09 | 23:44→23:48 | ana kan ashtagil.<br>_ana kan ashtagil._ | قُنت.<br>_قُنت._ | كان → كنت | kaan not matched to 'I' | B6 | high | **missed** |
| 0916-10 | 24:30→24:34 | Afarjinek.<br>_Afarjinek._ | أفرجيكي.<br>_أفرجيكي._ | أفرجينك → أفرجيكي | wrong 'you (f)' object ending | D4 | high | **missed** |
| 0916-11 | 32:28→32:30 | uh, بيوجع.<br>_uh, biwajja3._ | is feminine.<br>_is feminine._ | رجله بيوجع → رجله بتوجع | masculine verb for feminine rijl | NEW-B18 | high | yes |
| 0916-12 | 35:21→35:26 | تواجعك.<br>_تواجعك._ | is did I hurt you? Did you get hurt?<br>_is did I hurt you? Did you get hurt?_ | تواجعك → تواجعتي | object ending instead of past you-f ending | B5+D4 | medium | **missed** |
| 0916-13 | 35:49→35:52 | Uh, تواجاتيني.<br>_Uh, تواجاتيني._ | No, by me. Because of me.<br>_No, by me. Because of me._ | تواجعتيني → تواجعتي مني | object -ni instead of min for 'by me' | D2 | high | yes |
| 0916-14 | 38:29→38:48 | Ma titwajaiha. ... Ma wajaiha.<br>_Ma titwajaiha. ... Ma wajaiha._ | Don't hurt her. ... Very close.<br>_Don't hurt her. ... Very close._ | ما تتوجعيها / ما وجعيها → ما توجعيها | get-hurt form for 'hurt her', then dropped the t- of 'you' | B12+B11 | medium | **missed** |
| 0916-15 | 43:38→43:45 | bidayai, bidayi. Is it bidayayi or bidayi?<br>_bidayai, bidayi. Is it bidayayi or bidayi?_ | So what upsets you? So the what is the he, and then upsets you.<br>_So what upsets you? So the what is the he, and then upsets you._ | بدايقي → بيضايقك | 'what' is the he-subject; 'you' is the object ending | D4 | medium | **missed** |
| 0916-16 | 45:38→45:43 | daya u-- daya u ni. Daya u ni.<br>_daya u-- daya u ni. Daya u ni._ | You. Did they upset you?<br>_You. Did they upset you?_ | ضايقوني → ضايقوكي | 'me' ending instead of 'you (f)' | D4 | high | **missed** |
| 0916-17 | 48:51→48:54 | So ili amalti.<br>_So ili amalti._ | عملت.<br>_3melet._ | عملتي → عملت(ي) | stem of 3amal in the past (3melti) | B5 | low | yes |
| 0916-18 | 49:24→49:46 | it daya?<br>_it daya?_ | كان بيضايق not ت 'cause it makes people upset. It upsets. (later: كان يضايق)<br>_kaan بيضايق not ت 'cause it makes people upset. It upsets. (later: kaan يضايق)_ | كان اتضايق → كان يضايق | get-upset form for 'was upsetting (others)' | B12 | high | **missed** |
| 0916-19 | 57:29→57:34 | ala al-yamin.<br>_ala al-yamin._ | La el yameen. ... Bas ana baharrek something la el yameen.<br>_La el yameen. ... Bas ana baharrek something la el yameen._ | على اليمين → لليمين | 3ala for moving something to the right | D1 | high | **missed** |

### 2026-09-17

_read all 954 turns + 41 chat lines 00:30-1:03:45; Medi's Arabic untranscribed ('[speaking Arabic]') in ~14:00-22:15 and scattered later, so 0917-08/09 rest on Amal's side only_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0917-01 | 02:26→02:29 | عندهم زباين كتير.<br>_3indhom zabaayen Kteer._ | عنا.<br>_3inna._ | عندهم → عنا | wrong person ending on 3ind (they for we) | D3 | high | yes |
| 0917-02 | 04:22→04:27 | عنده ماي بس، فيها ماي بس شوي<br>_3indo mayy Bass, fiha mayy Bass shwai_ | فيها، not عندها. فيها؟<br>_fiha, not 3indha. fiha?_ | عنده → فيها | used 3ind (has) instead of fi (in it) for contents | D1 | high | yes |
| 0917-03 | 07:02→07:10 | daiman behtr, sos behtr<br>_daiman behtr, sos behtr_ | دايمًا / بيكون صوص بحرية<br>_Dayman / bikoon 9oo9 بحرية_ | daiman behtr → دايمًا بيكون ... | left out bikoon for a habitual description | B8 | medium | **missed** |
| 0917-04 | 08:42→08:58 | سبعتاش<br>_saba3ta3sh_ | خميس. / It's Thursday first then seventeenth.<br>_خميس. / It's Thursday first then seventeenth._ | سبعتاش → الخميس، سبعتاش | date said without the weekday first | E4 | high | yes |
| 0917-05 | 10:35→10:37 | دبات<br>_دبات_ | بدا. / here you're saying جو so it has to be masculine<br>_bada. / here you're saying Jaww so it has to be masculine_ | دبات (بدأت) → بدا | feminine verb ending with masculine subject جو | NEW-B18 | medium | yes |
| 0917-06 | 10:58→10:59 | So I say دنيا الجو.<br>_So I say denia El-jaw._ | الدنيا. / Either دنيا or جو. One just one.<br>_El-denia. / Either denia or Jaww. One just one._ | دنيا الجو → الدنيا | dunya without el- (and stacked with jaww) | A1 | medium | yes |
| 0917-07 | 13:22→13:33 | أنا راح أعمله بس الـ زباين<br>_Ana raa7 a3malo Bass el zabaayen_ | إنت كنت راح تعمله.<br>_enti kunet raa7 ta3malo._ | راح أعمله → كنت راح أعمله | plain ra7 for a past plan; needs kunt ra7 (was going to) | B13 | high | yes |
| 0917-25 | 1:00:35→1:00:41 | ma tadaitini.<br>_ma tadaitini._ | Ma dday'ini or dday'ini.<br>_Ma dday'ini or dday'ini._ | ما تضايقتيني → ما تضايقيني | reflexive t- form where causative (make me upset) needed | B12 | medium | **missed** |
| 0917-26 | 1:01:25→1:01:30 | Taghiri blouzeti<br>_Taghiri blouzeti_ | Yeah. No t bas ghayiri.<br>_Yeah. No t bas ghayiri._ | تغيري → غيّري | command kept the t- prefix | B10 | high | yes |
| 0917-27 | 1:02:06→1:02:09 | wazayini.<br>_wazayini._ | Ma.<br>_Ma._ | زعجيني (no ma) → ما تزعجيني | negative command missing ma | B11 | high | yes |
| 0917-08 | 21:06→21:37 | (Medi's Arabic not transcribed)<br>_(Medi's Arabic not transcribed)_ | عم بعمل is internal clipping, so what's he made? عمل.<br>_3aam ba3mal is internal clipping, so what's he made? 3emel._ | بعمل → عمل | present form where past 3emel needed after iza | B5 | low | **missed** |
| 0917-09 | 22:06→22:49 | (Medi's Arabic not transcribed)<br>_(Medi's Arabic not transcribed)_ | تتأسفي. / All. All كل.<br>_تتأسفي. / All. All kul._ | كل حدا (probable) → الكل | used every-one form where 'all' (el-kul) was meant | A11 | low | **missed** |
| 0917-10 | 27:56→28:01 | yita'assif illi<br>_yita'assif illi_ | to you.<br>_to you._ | illi (li = to me) → lek (to you) | wrong person ending on l- (me for you) | D3 | medium | yes |
| 0917-11 | 29:59→30:09 | ma ba'dar aru ala andik-- an alda-- ando.<br>_ma ba'dar aru ala andik-- an alda-- ando._ | So either على بيتك or عندك. / No, no على عندك. Just either على or عند.<br>_So either 'ala بيتك or 3indak. / No, no 'ala 3indak. Just either 'ala or 3end._ | على عندك → عندك / على بيتك | stacked two prepositions (3ala + 3ind) | D1 | high | yes |
| 0917-12 | 32:33→32:40 | بخرب is I ruin or I make not work<br>_ba5rab is I ruin or I make not work_ | No.<br>_No._ | بخرب = I ruin → بخرب = it gets ruined; بخرّب = I ruin | mixed up plain vs doubled (ruin vs get ruined) | B12 | medium | **missed** |
| 0917-13 | 36:30→36:36 | kharab, kharabit, kharabit.<br>_kharab, kharabit, kharabit._ | خرّبتي أو خرّبت. / No، خرّب، بخرب is the internal flipping. بخرّب is not.<br>_5arrabti Aw 5arabet. / No, 5arab, ba5rab is the internal flipping. ba5rab is not._ | kharabit (خربت) → خرّبتي | no doubled middle letter for 'you ruined (something)' | B12 | high | yes |
| 0917-14 | 37:44→37:46 | kharabti, kharabti.<br>_kharabti, kharabti._ | هم.<br>_humme._ | خرّبتي → خرّبتيهم | pointer ending missing after fronted object | C2 | high | yes |
| 0917-15 | 38:00→38:02 | Were mine kanit?<br>_Were mine kanit?_ | كانوا.<br>_kaanu._ | كانت → كانوا | kaan not matched to plural subject (plans) | B6 | high | yes |
| 0917-16 | 38:22→38:25 | they were mine. So kanuli?<br>_they were mine. So kanuli?_ | كانوا إلي. / No, no, no, no.<br>_kaanu eli. / No, no, no, no._ | كانولي → كانوا إلي | fused li onto kaan instead of separate ili | D3 | high | yes |
| 0917-17 | 43:22→43:41 | بيصلح كل، كل إشي اللي، بيخربه.<br>_bi9alle7 kul, kul eshi illi, bi5arrbo._ | ما في كل إشي في الجملة. Not everything just what. so اللي بيخربه.<br>_ma Fi kul eshi Fi el-jumle. Not everything just what. so illi bi5arrbo._ | كل إشي اللي بيخربه → اللي بيخربه | added kul ishi before illi (illi alone = what) | C7 | medium | **missed** |
| 0917-18 | 44:57→45:06 | kharabt kom, kharabt kom, kharabet kom.<br>_kharabt kom, kharabt kom, kharabet kom._ | خربتهم.<br>_5arabet-hom._ | خربتكم → خربتهم | wrong object ending (you-pl for them) | D4 | high | yes |
| 0917-19 | 46:29→46:32 | Ehna abadan ma kharab na...<br>_Ehna abadan ma kharab na..._ | We never broke it tie. Break it.<br>_We never broke it tie. Break it._ | ما خربنا → ما بنخرّبه | past tense for a 'never' habit; needs b- present | B1 | medium | yes |
| 0917-20 | 47:32→47:35 | M-m, uh, oh, wait, it's matet kharab. No.<br>_M-m, uh, oh, wait, it's matet kharab. No._ | No just one thing. ما تخربوه.<br>_No just one thing. ma t5arrbu._ | matet kharab / mat kharab po → ما تخربوه | object ending: 'it' (one thing) needs -uh | D4 | medium | yes |
| 0917-U1 | 51:15→51:27 | lama khatibti tistamali or tistamali comput--<br>_lama khatibti tistamali or tistamali comput--_ | Istamel.<br>_Istamel._ | تستعملي → تستعمل | present verb person wrong (you-f for she) | NEW-B18 | medium | yes |
| 0917-21 | 54:15→54:19 | Yeah, "khawaf." "Khawaf."<br>_Yeah, "khawaf." "Khawaf."_ | Mm. Al film kan bakhawaf.<br>_Mm. Al film kan bakhawaf._ | khawaf → كان بخوّف | bare verb without b- (and without kaan) for 'was scary' | B1 | medium | yes |
| 0917-22 | 57:15→57:19 | inti bitibisti?<br>_inti bitibisti?_ | Do you get happy? This means do you get happy? / Inti mabsuta?<br>_Do you get happy? This means do you get happy? / Inti mabsuta?_ | بتنبسطي → مبسوطة | verb 'get happy' for a state; needs participle | B15 | high | yes |
| 0917-23 | 58:26→58:29 | ma bikun<br>_ma bikun_ | Ma dun-- bidun be. So ma tkun.<br>_Ma dun-- bidun be. So ma tkun._ | ما بيكون → ما تكون | negative command built with b- form instead of you-form | B11 | medium | **missed** |
| 0917-24 | 59:56→59:59 | Yeah, ma tadaitni. Ma ta- ma tadait.<br>_Yeah, ma tadaitni. Ma ta- ma tadait._ | Ma tdaya' minni.<br>_Ma tdaya' minni._ | ما تضايقتني → ما تضايق مني | past form + object instead of command form + min | D2+B11 | medium | yes |

### 2026-09-18

_read all 962 turns + 66 chat lines 00:12-1:04:26; no machine audit exists; Medi's Arabic is blank/untranscribed in 20:40-31:10 (causative-adjective drill), so rows there are low or missing; chat is on the raw Meet clock and runs ~0.5-2 min behind the spoken exchange it matches_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0918-01 | 01:45→02:00 | لا أتمرنت.<br>_la أتمرنت._ | So if you wanna say لا ... It's gonna be present. لا أتمرن. / وأتمرنت. صح.<br>_So if you wanna say la ... It's gonna be present. la أتمرن. / وأتمرنت. sa7._ | لا أتمرنت → لا أتمرن | past verb after la- (in order to); needs bare present | B3 | medium | **missed** |
| 0918-02 | 05:37→05:42 | زهرت تك.<br>_زهرت تك._ | Him. Him. / زهرته.<br>_Him. Him. / زهرته._ | زهّقتك → زهّقته | wrong object ending (you for him) | D4 | high | **missed** |
| 0918-03 | 06:49→06:52 | Zehe at, zehe as<br>_Zehe at, zehe as_ | Ze at<br>_Ze at_ | zehe-at → زهقت (zhe2at) | kept the I-form vowel in the she-form past | B5 | medium | **missed** |
| 0918-04 | 08:02→08:10 | tabe-tabe-tabu, uh, tabu tu<br>_tabe-tabe-tabu, uh, tabu tu_ | Tab tu<br>_Tab tu_ | tabu tu → تعبتوا | stacked -u on -tu for you-plural past | B5 | medium | **missed** |
| 0918-05 | 10:29→10:48 | khuffetilik?<br>_khuffetilik?_ | What do we use for worried? / You got the verb right, but what's the should preposition?<br>_What do we use for worried? / You got the verb right, but what's the should preposition?_ | خفت لك → خفت عليك | wrong preposition with 5aaf for 'worried about' | D2 | high | **missed** |
| 0918-06 | 11:43→11:51 | Khawaf. So, uh, khawaf, khawafit, khawafik<br>_Khawaf. So, uh, khawaf, khawafit, khawafik_ | This is I scared you. I got scared of you<br>_This is I scared you. I got scared of you_ | خوّفتك → خفت منك | causative (I scared you) for 'I got scared of you' | B12 | high | **missed** |
| 0918-07 | 13:13→13:17 | uh, asabulna?<br>_uh, asabulna?_ | They got angry at me. / Alay. / Asabu alay.<br>_They got angry at me. / Alay. / Asabu alay._ | عصبولنا → عصبوا عليّ | wrong preposition (l-) and wrong person (us for me) with 3assab | D2+D3 | medium | **missed** |
| 0918-08 | 14:56→15:01 | zehekti.<br>_zehekti._ | Why don't you think there's a preposition? Of it.<br>_Why don't you think there's a preposition? Of it._ | زهقتي → زهقتي منه | dropped min after zhe2 (bored of) | D2 | high | **missed** |
| 0918-09 | 15:46→15:49 | zehekti.<br>_zehekti._ | Leesh zehekti.<br>_Leesh zehekti._ | زهقتي → زهّقتيه | plain 'got bored' for 'made him bored' (per chat) | B12 | low | **missed** |
| 0918-10 | 16:07→16:17 | Ana bakhaf.<br>_Ana bakhaf._ | I get scared. I am scared. / No. It's an adjective / Ana khayef.<br>_I get scared. I am scared. / No. It's an adjective / Ana khayef._ | أنا بخاف → أنا خايف | verb 'I get scared' for the state 'I am scared' | B15 | high | **missed** |
| 0918-11 | 20:03→20:11 | kan, uh, yadahu. Yadah. Yadah.<br>_kan, uh, yadahu. Yadah. Yadah._ | Kan. Yadahak.<br>_Kan. Yadahak._ | يضحك → يضحّك | plain 'laughs' where causative 'makes laugh' needed | B12 | low | **missed** |
| 0918-12 | 27:41→27:41 | (Medi's Arabic not transcribed)<br>_(Medi's Arabic not transcribed)_ | Me. Made me tired. / That's right. It's feminine.<br>_Me. Made me tired. / That's right. It's feminine._ | (object missing) → تعّبتني | object ending 'me' missing | D4 | low | **missed** |
| 0918-U1 | 29:08→29:24 | be as, be as.<br>_be as, be as._ | Try again. / They make me bored.<br>_Try again. / They make me bored._ | (singular verb, garbled) → بيزهقوني | singular verb for plural subject (meetings) | NEW-B18 | low | **missed** |
| 0918-13 | 37:09→37:17 | inti mit-, uh, mit'asib bi<br>_inti mit-, uh, mit'asib bi_ | Bit'asib bi.<br>_Bit'asib bi._ | متعصبي → بتعصبي | participle-style m- form where b- present verb needed | B15 | medium | **missed** |
| 0918-14 | 37:19→37:21 | inti bit'asib bi<br>_inti bit'asib bi_ | Me.<br>_Me._ | بتعصبي → بتعصبيني | object ending 'me' missing on the verb | D4 | medium | **missed** |
| 0918-15 | 44:08→44:13 | daiman ma biasab mina.<br>_daiman ma biasab mina._ | No, why ma?<br>_No, why ma?_ | دايمًا ما بيعصب → دايمًا بيعصب | added ma after daayman (only abadan drags ma) | C4b | high | **missed** |
| 0918-16 | 44:18→44:28 | Daiman biasab mina.<br>_Daiman biasab mina._ | At us.<br>_At us._ | بيعصب منا → بيعصب علينا | min (because of) where 3ala (at) needed | D2 | high | **missed** |
| 0918-17 | 45:57→46:00 | shu huwa-<br>_shu huwa-_ | Let's use ili better, 'cause shu would sound like a question<br>_Let's use ili better, 'cause shu would sound like a question_ | شو → اللي | shu for 'what he did' - relative needs illi | C7 | medium | **missed** |
| 0918-18 | 51:10→51:44 | Ma tazahoni?<br>_Ma tazahoni?_ | You said it right, command, but ... You guys don't bore me. / Ni. ... first for you to just command for a group. / Ma zahni.<br>_You said it right, command, but ... You guys don't bore me. / Ni. ... first for you to just command for a group. / Ma zahni._ | ما تزهقوني → ما تزهقني | plural command ending for a single 'you' | B11 | high | **missed** |
| 0918-19 | 52:30→52:40 | id hakni. Id ha- Id hakini.<br>_id hakni. Id ha- Id hakini._ | Id haki at me. / Ili. Id hakili.<br>_Id haki at me. / Ili. Id hakili._ | اضحكيني → اضحكيلي | object ending instead of l- for 'smile at me' | D2 | high | **missed** |

### 2026-09-19

_read all 843 turns + 78 chat lines, 00:00-1:02:03. Lesson is mostly a listening drill (Amal says a verb form, Medi translates to English); most grammar fixes are comprehension of causative/reflexive, tense and person, marked '(listening drill)' in mistake. Medi's own Arabic production is only ~06:30-10:30 and a few drill lines. Several Medi lines ASR-garbled (e.g. 'Kamara', 'Tawamara' = kamaan marra)._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0919-01 | 07:50→08:02 | بتغي-- بتغير كتير. No, بتغير كتير.<br>_بتغي-- bat8ayyar Kteer. No, bat8ayyar Kteer._ | So تغير، no be. ... It changed؟<br>_So et8ayyar, no be. ... It changed?_ | بتغير → تغير | used b-present for something that already happened (weather changed) | B5 | high | **missed** |
| 0919-02 | 09:56→10:01 | بلوز، uh، أبيض. أبيض؟ بيض؟ أبيض.<br>_buluz, uh, Abyad. Abyad? baid? Abyad._ | بيضة.<br>_baida._ | بلوز أبيض → بيضة (as transcribed; feminine white) | masculine adjective on a feminine noun (blouse) | A8 | low | **missed** |
| 0919-03 | 11:34→11:55 | you took a photo or I, I take a photo? I had, had taken a photo?<br>_you took a photo or I, I take a photo? I had, had taken a photo?_ | Is it did you take a photo or did you get-- did you take a photo of yourself؟ Like, did you get photographed؟<br>_Is it did you take a photo or did you get-- did you take a photo of yourself? Like, did you get photographed?_ | took a photo → اتصورت = got photographed | (listening drill) read reflexive t- form as active 'took a photo' | B12 (listening) | medium | **missed** |
| 0919-04 | 12:58→13:02 | you are tired of me.<br>_you are tired of me._ | No that's تعبت مني. تعبتني.<br>_No that's t3ebet minni. تعبتني._ | تعبت مني (tired of me) → تعبتني (you tired me) | (listening drill) read causative + object -ni as 'tired of me' | B12+D4 (listening) | high | **missed** |
| 0919-05 | 13:07→13:09 | Do you tire me?<br>_Do you tire me?_ | مهم. بس is it present or past؟<br>_Muhem. Bass is it present or past?_ | present 'do you tire' → past 'you tired me' | (listening drill) read past تعبتني as present | B5 (listening) | medium | **missed** |
| 0919-06 | 15:50→15:54 | Why did you smile to a male or why did she smile?<br>_Why did you smile to a male or why did she smile?_ | Is it did or do؟<br>_Is it did or do?_ | past 'did you smile' → بتضحك = present 'why do you smile' | (listening drill) read b-present بتضحك as past | B1 (listening) | medium | **missed** |
| 0919-07 | 18:10→18:14 | They had fun or they enjoyed?<br>_They had fun or they enjoyed?_ | آآآ. Close بس that would be انبسطوا. انبسطوا<br>_aaa. Close Bass that would be Enbes6u. Enbes6u_ | they had fun (past) → enbes6u = enjoy! (plural command) | (listening drill) read plural command as past 'they had fun' | B10 (listening) | low | **missed** |
| 0919-08 | 22:15→22:18 | He will not, he will not bore you.<br>_He will not, he will not bore you._ | Very close. أزهقك، not يزهقك. أزهقك. ... I won't bore you.<br>_Very close. أزهقك, not يزهقك. أزهقك. ... I won't bore you._ | يزهقك (he) → أزهقك (I) | (listening drill) read a- (I) prefix as y- (he) on present verb | NEW-B18 (listening) | high | **missed** |
| 0919-09 | 24:53→24:56 | so don't be tired of me.<br>_so don't be tired of me._ | That's ما تتعبي مني. ما تعبيني.<br>_That's ma تتعبي minni. ma تعبيني._ | ما تتعبي مني → ما تعبيني (don't tire me) | (listening drill) read causative negative command as 'don't be tired of me' | B12 (listening) | high | **missed** |
| 0919-10 | 26:35→26:37 | She laughed at him.<br>_She laughed at him._ | علي.<br>_'ala._ | عليه (at him) → علي (at me) | (listening drill) confused ending -i (me) with -o (him) on 3ala | D3 (listening) | high | **missed** |
| 0919-11 | 27:44→27:55 | Who was he mad with you-- at you? I don't... This doesn't make sense.<br>_Who was he mad with you-- at you? I don't... This doesn't make sense._ | So is it ضايق or it's ضايقة to be upset؟ ... So مين ضايقك؟<br>_So is it ضايق or it's ضايقة to be upset? ... So meen ضايقك?_ | to be upset → ضايق = to upset someone | (listening drill) read causative ضايق as 'be upset' | B12 (listening) | medium | **missed** |
| 0919-12 | 32:35→32:38 | So basat is I was happy.<br>_So basat is I was happy._ | I made.<br>_I made._ | I was happy → بسطته = I made him happy | (listening drill) read causative بسط as 'got happy' | B12 (listening) | high | yes |
| 0919-13 | 38:16→38:20 | Uh, Lisa ma-- Or matahammasi Lisa.<br>_Uh, Lisa ma-- Or matahammasi Lisa._ | ما تتحمسي لسه.<br>_ma تتحمسي Lissa._ | matahammasi → ما تتحمسي | negative command form of t-verb (ma tet-) | B11 | low | **missed** |
| 0919-14 | 39:04→39:11 | Yeah, they apologized. Present tense. Can I...<br>_Yeah, they apologized. Present tense. Can I..._ | لأ. ... اتأسفوا، not بيتأسفوا.<br>_la. ... اتأسفوا, not بيتأسفوا._ | بيتأسفوا (present) → اتأسفوا (past) | called the past form اتأسفوا present tense | B5 | high | **missed** |
| 0919-15 | 39:31→39:37 | I ruined the, the s- the trip. ... Oh, khirbat. Uh, she ruined the trip.<br>_I ruined the, the s- the trip. ... Oh, khirbat. Uh, she ruined the trip._ | Are you sure؟ I ruined؟ ... No؟ That would be خربت. خربت.<br>_Are you sure? I ruined? ... No? That would be 5arabet. 5arabet._ | I/she ruined → خربت السفرة = the trip got ruined | (listening drill) read intransitive خربت as causative 'ruined' | B12 (listening) | medium | **missed** |
| 0919-16 | 42:28→42:45 | Who, yeah, who was made happy or who enjoyed from us?<br>_Who, yeah, who was made happy or who enjoyed from us?_ | With us. معنا.<br>_With us. معنا._ | from us → معنا = with us | (listening drill) wrong meaning of preposition with انبسط | D2 (listening) | medium | **missed** |
| 0919-17 | 43:17→43:21 | Uh, are you excited to a girl?<br>_Uh, are you excited to a girl?_ | Did you get excited؟<br>_Did you get excited?_ | are you excited (present) → تحمستِ = did you get excited | (listening drill) read past تحمستِ as present | B5 (listening) | medium | **missed** |
| 0919-18 | 44:45→44:47 | bizah.<br>_bizah._ | Yeah. That's boring. ... زهقان.<br>_Yeah. That's boring. ... Zah2aan._ | بيزهق (boring, verb) → زهقان (bored, participle) | gave the verb when the state word 'bored' was asked | B15 | medium | **missed** |
| 0919-19 | 50:17→50:41 | She was happy. ... I enjoyed to it.<br>_She was happy. ... I enjoyed to it._ | No، انبسطت له. ... Just the verb. I got happy له. ... For، for him.<br>_No, nbasa6et elo. ... Just the verb. I got happy elo. ... For, for him._ | she / to it → I got happy for him (انبسطت له) | (listening drill) misread person of انبسطت and meaning of له with it | D2+B5 (listening) | medium | **missed** |
| 0919-20 | 52:47→52:50 | You guys don't be annoyed.<br>_You guys don't be annoyed._ | تزعجوه، not تنزعجوا، تزعجوه. ... توه، تزعجوه.<br>_تزعجوه, not تنزعجوا, تزعجوه. ... توه, تزعجوه._ | تنزعجوا (don't be annoyed) → تزعجوه (don't annoy him) | (listening drill) read causative + object -uh as reflexive | B12+D4 (listening) | high | **missed** |
| 0919-21 | 54:19→54:22 | They made us sad.<br>_They made us sad._ | زعلوني.<br>_زعلوني._ | us → -ني = me | (listening drill) read object ending -ni as 'us' | D4 (listening) | medium | **missed** |
| 0919-22 | 56:04→56:16 | So it made me happy...<br>_So it made me happy..._ | صح، it made happy، بس is it past or present؟<br>_sa7, it made happy, Bass is it past or present?_ | it made me happy (past) → بيبسطني = it makes me happy | (listening drill) read b-present بيبسطني as past | B1 (listening) | high | **missed** |
| 0919-23 | 56:24→56:30 | Present. Oh, it makes me happy you came. Aji, you said, "It makes me happy he came."<br>_Present. Oh, it makes me happy you came. Aji, you said, "It makes me happy he came."_ | آجي. I come. It makes me happy like coming makes me happy.<br>_آجي. I come. It makes me happy like coming makes me happy._ | he came → آجي = I come | (listening drill) read آجي (I come) as 'he came' | NEW-B18 (listening) | medium | **missed** |
| 0919-24 | 58:57→59:01 | did you guys enjoy me or did you guys have f-<br>_did you guys enjoy me or did you guys have f-_ | Mhm. Have fun with.<br>_Mhm. Have fun with._ | enjoy me → انبسطت معي = have fun with me | (listening drill) dropped meaning of ma3 with انبسط | D2 (listening) | low | **missed** |
| 0919-25 | 59:39→59:57 | Did, uh, did you guys enjoy to me? Did you guys... I don't understand this one.<br>_Did, uh, did you guys enjoy to me? Did you guys... I don't understand this one._ | انبسطولي. ... They got-- they were happy for me. They got happy for me.<br>_انبسطولي. ... They got-- they were happy for me. They got happy for me._ | you guys / to me → they / for me (انبسطولي) | (listening drill) misread person (they) and -li 'for me' on the verb | D2+B5 (listening) | medium | **missed** |

### 2026-09-21

_read all 1274 turns + 57 chat lines, 00:01-1:12:04; no untranscribed gaps; 32:13-32:48 and 49:54-50:33 have overlapping/garbled lines_

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0921-01 | 02:44→02:47 | آآآ، أتعلم-- آآآ، بتعلمه؟<br>_aaa, at3allam-- aaa, bat3allamo?_ | تعلمتها.<br>_t3allamtha._ | بتعلمه → تعلمتها | present instead of past 'I learned it'; object -o for feminine word | B5+D4 | high | yes |
| 0921-02 | 07:59→08:01 | pantalón خضرا،<br>_pantalón 5adra,_ | أخضر.<br>_a5dar._ | خضرا → أخضر | feminine colour on masculine بنطلون | A8 | high | yes |
| 0921-03 | 09:00→09:02 | عندهم<br>_3indhom_ | عنا.<br>_3inna._ | عندهم → عنا | 'they have' for 'we have' - wrong ending on 3ind | D3 | high | yes |
| 0921-04 | 09:24→09:31 | تلاتين أيام.<br>_talateen ayyaam._ | تلاتين ... بعد العشرة يوم.<br>_talateen ... Ba3ed el-3ashrah Yoam._ | تلاتين أيام → تلاتين يوم | plural noun after 30 (11+ takes singular) | E1 | high | **missed** |
| 0921-05 | 10:02→10:02 | عندهم؟<br>_3indhom?_ | on them، on them، بس يعني إندم in Arabic.<br>_on them, on them, Bass Ya3ni إندم in Arabic._ | عندهم → فيهم | '3ind' for 'in them' (days we need a jacket in) | D1 | medium | **missed** |
| 0921-06 | 11:24→11:29 | بتغير.<br>_bat8ayyar._ | They change.<br>_They change._ | بتغير → بتغيروا | singular verb for 'they change' - missing plural -u | NEW-B18 | medium | **missed** |
| 0921-07 | 12:48→13:00 | أكلت الـ pizza دول<br>_Akalet el pizza دول_ | The pizza that remained. That remained from أخر الأسبوع.<br>_The pizza that remained. That remained from 2aa5er el-Usboo3._ | الـ pizza دول → الـ pizza اللي دلت | no illi before the relative clause | C7 | medium | **missed** |
| 0921-08 | 12:56→13:00 | آآآ الـ آخر الأسبوع.<br>_aaa el 2aa5er el-Usboo3._ | That remained from أخر الأسبوع.<br>_That remained from 2aa5er el-Usboo3._ | الـ آخر الأسبوع → آخر الأسبوع | el- on the first word of an idafa | A2 | high | **missed** |
| 0921-09 | 14:26→14:29 | كل الـ fire department وambulance آآآ آجوا.<br>_kul el fire department uambulance aaa aju._ | بيجو.<br>_byeju._ | آجوا → بيجو | past for a habitual present - needs b- | B1 | high | yes |
| 0921-10 | 14:43→14:44 | الـ pizza اللي دلوا<br>_el pizza illi دلوا_ | One piece. Pizza is one. ... Pizza is woman ... feminine.<br>_One piece. Pizza is one. ... Pizza is woman ... feminine._ | دلوا → دلت | plural verb ending for feminine singular pizza | NEW-B18 | high | yes |
| 0921-11 | 19:26→19:24 | ما حا-حكينا كتير مع--<br>_ma حا-7akaina Kteer ma'--_ | آه. بنحكي.<br>_aaah. bne7ki._ | حكينا → بنحكي | past instead of habitual present with b- | B1 | medium | yes |
| 0921-37 | 1:00:41→1:00:43 | il ta'am il samak bihr.<br>_il ta'am il samak bihr._ | لا، بس one L. Where do I put the L؟ It's just one.<br>_la, Bass one L. Where do I put the L? It's just one._ | الطعم السمك → طعم السمك | el- on the first word of an idafa | A2 | high | yes |
| 0921-38 | 1:03:03→1:03:19 | رزنا أحسن من الـ دنيا.<br>_ruzna a7san men el denia._ | أحسن من كل الدنيا؟ ... So أحسن رز في الدنيا، أو بالدنيا.<br>_a7san men kul El-denia? ... So a7san Ruz Fi El-denia, Aw بالدنيا._ | رزنا أحسن من الدنيا → أحسن رز في الدنيا | superlative: أحسن goes first + noun | C3 | high | **missed** |
| 0921-39 | 1:04:45→1:04:49 | بس مش عندك إيراني.<br>_Bass mesh 3indak Irani._ | ما عندكم.<br>_ma 3indkom._ | مش عندك → ما عندكم | mish before 3ind, and singular 'you' for plural | C4+D3 | high | yes |
| 0921-40 | 1:05:57→1:05:59 | So مطعم...<br>_So Ma63am..._ | The best first.<br>_The best first._ | مطعم ... (أحسن after) → أحسن مطعم | superlative أحسن must come first | C3 | medium | yes |
| 0921-41 | 1:06:00→1:06:05 | أحسن م-مطعم الإيراني،<br>_a7san م-Ma63am el-Irani,_ | Restaurants.<br>_Restaurants._ | مطعم → مطاعم | singular where plural meant | A9 | medium | **missed** |
| 0921-42 | 1:06:59→1:07:01 | يفـ-- دفدوا.<br>_يف-- دفدوا._ | بيفتحوا.<br>_بيفتحوا._ | يفتحوا → بيفتحوا | missing b- on present verb | B1 | medium | **missed** |
| 0921-12 | 22:28→22:33 | أنا راح أستانك. أستانك. يا أستانك.<br>_Ana raa7 astannaak. astannaak. ya astannaak._ | استناك.<br>_استناك._ | أستانك → استناك (astannaaki) | wrong you-ending on the verb (talking to a woman) | D4 | low | yes |
| 0921-13 | 23:58→24:00 | أديش الحق؟ ... أديش حقو؟<br>_2addaish el-7a22? ... 2addaish 7a22o?_ | قديش Its price. ... قديش حقها. Cuz it's coffee.<br>_qaddeish Its price. ... qaddeish 7a22ha. Cuz it's coffee._ | حقو → حقها | possessive -o on feminine قهوة; needs -ha | A4 | high | **missed** |
| 0921-14 | 24:37→24:54 | ما credit card ما... min<br>_ma credit card ma... min_ | أدفع. ... Which preposition? ... B. Credit card.<br>_Edfa3. ... Which preposition? ... B. Credit card._ | min credit card → بالـ credit card | 'min' instead of bi- for the means of paying | D1 | high | yes |
| 0921-15 | 25:19→25:20 | أدفع لهم.<br>_Edfa3 ilhom._ | أدفع عن. Pay for. ... بدفع عنك.<br>_Edfa3 3an. Pay for. ... badfa3 3annak._ | أدفع لهم → أدفع عن | 'pay for' takes عن, not لـ | D2 | high | yes |
| 0921-16 | 26:07→26:10 | is it just فتله or no ... فتله.<br>_is it just فتله or no ... فتله._ | Yes. تفضلي.<br>_Yes. tfaddali._ | فتله → تفضلي | masculine command to a woman - needs -i | B10 | medium | **missed** |
| 0921-17 | 28:37→28:42 | هذا الأكلة.<br>_Haada el-Akle._ | You were right هذي الأكلة. هذي is for feminine.<br>_You were right hadi el-Akle. hadi is for feminine._ | هذا → هذي | masculine هذا with feminine أكلة | A10 | high | yes |
| 0921-18 | 29:34→29:36 | Is she, is she غلط بي... بي ال or<br>_Is she, is she 8ala6 بي... بي el or_ | In it. ... فيها. ... أو فيها إشي غلط.<br>_In it. ... fiha. ... Aw fiha eshi 8ala6._ | بي ال → فيها | wrong preposition for 'something wrong in it' | D1 | high | yes |
| 0921-19 | 32:35→32:41 | Hamet, uh, hamha mura oo hamida.<br>_Hamet, uh, hamha mura oo hamida._ | خلص إنت هلأ you're now describing the taste so it's more.<br>_5alas enti Halla you're now describing the taste so it's more._ | مرّة، حامضة → مرّ، حامض | feminine adjectives but the subject is masculine طعم | A8 | medium | yes |
| 0921-U1 | 38:10→38:23 | would it be a-ana mash-mashhur bi-ut-bi atbuk without the bi, right?<br>_would it be a-ana mash-mashhur bi-ut-bi atbuk without the bi, right?_ | في. ... في or be. ... في، mm, the noun. Noun is طبخ.<br>_Fi. ... Fi or be. ... Fi, mm, the noun. Noun is taba5._ | بـ أطبخ → بالطبخ | verb after a preposition - needs the verbal noun | NEW-C11 | high | **missed** |
| 0921-20 | 40:06→40:10 | ana bazun innu hadi mish lazim.<br>_ana bazun innu hadi mish lazim._ | هذي ... مش لا-- إنه ما كان لازم، صح.<br>_hadi ... mesh la-- enno ma kaan Laazem, sa7._ | مش لازم → ما كان لازم | 'shouldn't have' needs ma kaan laazem | B16 | high | yes |
| 0921-21 | 41:01→41:05 | Bi, bibi'u, ishna bibi'?<br>_Bi, bibi'u, ishna bibi'?_ | بتبيع because شركة is<br>_بتبيع because Sharika is_ | بيبيعوا → بتبيع | he/they verb for feminine شركة | NEW-B18 | high | **missed** |
| 0921-22 | 41:06→41:09 | Bitbi'a, bitbi'a il-roz, uh,<br>_Bitbi'a, bitbi'a il-roz, uh,_ | بتبيعه.<br>_betbee3o._ | بتبيع الرز → بتبيعه | relative clause needs the pointer ending -o | C2 | medium | yes |
| 0921-23 | 41:15→41:19 | bigassel<br>_bigassel_ | بتغسل. ... أو بتغسله يعني.<br>_bet8assel. ... Aw بتغسله Ya3ni._ | بيغسل → بتغسل / بتغسله | he-form for feminine شركة; then adds pointer -o | NEW-B18+C2 | medium | yes |
| 0921-24 | 42:47→42:50 | Lama ana kasul? Wait.<br>_Lama ana kasul? Wait._ | أنا لما so. ... بكون so<br>_Ana Lamma so. ... bakoon so_ | لما أنا كسول → لما أنا بكون كسول | missing bakoon after lamma | B8 | high | yes |
| 0921-25 | 43:03→43:04 | أساهم.<br>_أساهم._ | مم، بستعمل.<br>_mm, بستعمل._ | أساهم → بستعمل | bare verb without b- ('I use') | B1 | low | **missed** |
| 0921-26 | 43:41→43:44 | أنا أعمل، أعمله،<br>_Ana E3mel, a3malo,_ | بعمله.<br>_ba3malo._ | أعمله → بعمله | missing b- on present verb | B1 | high | yes |
| 0921-27 | 44:25→44:27 | أ-أ-أطبخ، أطبخه،<br>_aa-aa-Etbu5, atbu5o,_ | بطبخه.<br>_batbu5o._ | أطبخه → بطبخه | missing b- on present verb | B1 | high | yes |
| 0921-28 | 48:59→49:03 | So أنا أساهم بالعكس المقلاة.<br>_So Ana أساهم b-el-3aks el-ma2la._ | عكس الملعقة.<br>_3aks el-ma3la2a._ | بالعكس المقلاة → عكس الملعقة | bi- + el- on the first word of an idafa (also wrong noun) | A2 | high | yes |
| 0921-29 | 49:51→49:59 | u batfukh al roz laa aktar min thalath, uh, saa.<br>_u batfukh al roz laa aktar min thalath, uh, saa._ | Three hours؟ ثلاث ساعات؟<br>_Three hours? talat saa3aat?_ | ثلاث ساعة → ثلاث ساعات | singular after 3 - needs plural | E3 | medium | yes |
| 0921-31 | 51:08→51:09 | hadi nar? ... Nar hadi? Hadir<br>_hadi nar? ... Nar hadi? Hadir_ | نار ... هادية.<br>_Naar ... Haadye._ | هادي نار → نار هادية | adjective before noun, and masculine for feminine نار | A7+A8 | high | yes |
| 0921-32 | 52:25→52:29 | Iraniyin. Ihna Iraniyin, uh,<br>_Iraniyin. Ihna Iraniyin, uh,_ | إيرانيين. ... إحنا الإيرانيين<br>_إيرانيين. ... i7na el-iraniyyeen_ | إحنا إيرانيين → إحنا الإيرانيين | needs el- ('we Iranians') | A1 | high | yes |
| 0921-33 | 53:11→53:14 | So, tahet min roz crispy. Roz min tahet.<br>_So, tahet min roz crispy. Roz min tahet._ | الرز من تحت.<br>_el-Ruz men Ta7t._ | رز من تحت → الرز من تحت | dropped el- on the known noun | A1 | medium | yes |
| 0921-34 | 56:33→56:36 | Um, 'andhum<br>_Um, 'andhum_ | عنا.<br>_3inna._ | عندهم → عنا | 'they have' for 'we have' (same slip as 09:00) | D3 | high | yes |
| 0921-35 | 56:55→56:58 | bas il ta'am mashhoor, uh, min Iran.<br>_bas il ta'am mashhoor, uh, min Iran._ | فيه.<br>_fih._ | من إيران → في إيران | 'min' for 'in Iran' | D1 | high | yes |
| 0921-36 | 57:12→57:14 | Mish anna akil bihr.<br>_Mish anna akil bihr._ | م-ما عنا.<br>_م-ma 3inna._ | مش عنا → ما عنا | mish before 3ind - needs ma | C4 | high | yes |

### 2026-09-23

_read all 790 turns + 57 chat lines, 00:52-1:04:32. GAP: Medi's track missing 00:00-~23:40 (first Medi line 23:44); only Amal's side exists there. Logged 3 Amal-only recasts from the gap (0923-01..03, low, medi_said null); skipped ambiguous ones (08:21 أكلت, 21:33 أحجز, 13:08 date). 59:08-1:02:16 dual drill + sentence: Medi's Arabic mostly '[speaking Arabic]', unreadable._

| id | time | Medi said | Amal said | wrong → right | mistake | bucket | conf | machine |
|---|---|---|---|---|---|---|---|---|
| 0923-01 | →05:06 |  | How do you make قهوة two؟ No، it's feminine، so شو.<br>_How do you make Ahweh two? No, it's feminine, so shu._ |  → قهوتين (ahwetain) | dual of a feminine noun - missing the -t- before -ain | A9+A3 | low | **missed** |
| 0923-02 | →07:58 |  | I didn't go. مش you did-- you don't go.<br>_I didn't go. mesh you did-- you don't go._ |  → ما رحت | present/negative-present used for 'I didn't go' | B5 | low | **missed** |
| 0923-03 | →08:46 |  | شو جمع إشي؟ ... أشياء، نفس الأشياء.<br>_shu Jame3 eshi? ... أشياء, Nafs الأشياء._ |  → نفس الأشياء | singular إشي where plural needed | A9 | low | **missed** |
| 0923-04 | 23:56→24:00 | أمم شووو بتسأل، آآآ بتتسأليني؟<br>_umm شووو بتسأل, aaa بتتسأليني?_ | شو بتسأليني؟<br>_shu بتسأليني?_ | بتتسأليني → بتسأليني | added reflexive t- to سأل | B12 | medium | **missed** |
| 0923-05 | 26:35→26:37 | How long will you stay with me؟<br>_How long will you stay with me?_ | With us or at our hotel، at ours. ... عنا، لا.<br>_With us or at our hotel, at ours. ... 3inna, la._ | with me → عنا = with us / at ours | (listening) read ending -na (us) as 'me' on 3ind | D3 (listening) | medium | **missed** |
| 0923-06 | 26:54→26:55 | كم يوم؟ Or كم أيام؟<br>_Kum Yoam? Or Kum ayyaam?_ | مhm. لا، كم يوم. ليش؟<br>_مhm. la, Kum Yoam. lesh?_ | كم أيام → كم يوم | offered plural after kam | E5 | high | **missed** |
| 0923-07 | 27:17→27:19 | أنا راح بدول،<br>_Ana raa7 بدول,_ | أضل.<br>_أضل._ | راح بدول → راح أضل | kept b- after ra7 | B13 | high | **missed** |
| 0923-08 | 27:26→27:30 | آآآ ثنتين أيام.<br>_aaa tentain ayyaam._ | How do I make يوم to... <br>_How do I make Yoam to... _ | ثنتين أيام → يومين | number 2 + plural instead of the dual | E1 | high | **missed** |
| 0923-09 | 34:19→34:23 | واح-واحد، واحد موظفين. Or وا-واحدة موظفة.<br>_واح-Wa7ad, Wa7ad موظفين. Or w-aa-wa7de موظفة._ | واحد. One. خلص. So you don't need say one.<br>_Wa7ad. One. 5alas. So you don't need say one._ | واحد موظفين → موظف | used 'one' (+plural) to mark a new/indefinite noun | A1 | medium | **missed** |
| 0923-10 | 35:01→35:02 | أنا طلبت الموظفين<br>_Ana 6alabet الموظفين_ | من؟<br>_men?_ | طلبت الموظفين → طلبت من الموظف | dropped the preposition min after talab | D2 | high | **missed** |
| 0923-11 | 35:03→35:08 | من موظف، موظف، موظف.<br>_men Muwazzaf, Muwazzaf, Muwazzaf._ | الموظف ولا الموظف؟<br>_el-Muwazzaf Wala el-Muwazzaf?_ | من موظف → من الموظف | missing el- on a known noun (the employee) | A1 | medium | **missed** |
| 0923-12 | 35:21→35:31 | اللي، آآآ جا ... I-I asked him to come، right؟<br>_illi, aaa جا ... I-I asked him to come, right?_ | When أزا؟ ... To come. So it's not to came. So it's to come.<br>_When أزا? ... To come. So it's not to came. So it's to come._ | جا → يجي | past verb after 'asked him to' - needs bare present | B2 | medium | **missed** |
| 0923-13 | 35:56→36:04 | بس هو أبدًا يجي. ... ما يجي. ... ما-- صح ما يجي؟<br>_Bass Huwwe Abadan يجي. ... ma يجي. ... ma-- sa7 ma يجي?_ | هو أبدًا شو؟ ... ما. It's came. He never came. ... Came past.<br>_Huwwe Abadan shu? ... ma. It's came. He never came. ... Came past._ | أبدًا يجي → أبدًا ما آجه | abadan without ma, and present for 'never came' | C4b+B5 | high | **missed** |
| 0923-14 | 36:31→36:39 | ما بحب الفطور.<br>_ma ba77eb el-Ftur._ | You didn't like.<br>_You didn't like._ | ما بحب → ما حبيت | present for a past complaint | B5 | high | **missed** |
| 0923-15 | 36:49→36:53 | الأكل الأمريكي.<br>_el-Akel el-Amriki._ | الأمريكي. ... The American food. الأكل الأمريكي.<br>_el-Amriki. ... The American food. el-Akel el-Amriki._ | (الأكل) أمريكي → الأكل الأمريكي | adjective missing el- to match its noun | A7 | low | **missed** |
| 0923-16 | 37:21→37:26 | الـ، uh، أمي الـ- الوحيد أكل.<br>_el, uh, أمي el- el-Wa7id Akel._ | الأكل الوحيد، cuz وحيد is not adjective.<br>_el-Akel el-Wa7id, cuz Wa7id is not adjective._ | الوحيد أكل → الأكل الوحيد | put adjective before the noun | A7 | high | **missed** |
| 0923-17 | 38:22→38:48 | طلبت من الـ موافظ اللي يجي، موظف اللي يجي<br>_6alabet men el موافظ illi يجي, Muwazzaf illi يجي_ | موظف اللي what؟ ... So you don't need الـ اللي. ... No اللي then. ... لا خلاص إنه يجي.<br>_Muwazzaf illi what? ... So you don't need el illi. ... No illi then. ... la خلاص enno يجي._ | اللي يجي → إنه يجي | used illi (relative) where 'that/to' (enno) was meant | C7 | high | yes |
| 0923-18 | 48:36→48:41 | Uh, no. Okay. لما الموعد الدرس.<br>_Uh, no. Okay. Lamma el-Maw3ed el-Dars._ | موعد الدرس.<br>_Maw3ed el-Dars._ | الموعد الدرس → موعد الدرس | el- on the first noun of idafa | A2 | high | yes |
| 0923-19 | 48:45→48:49 | um, بدري.<br>_um, Badri._ | لما موعد الدرس يكون بدري.<br>_Lamma Maw3ed el-Dars ykun Badri._ | لما موعد الدرس بدري → لما موعد الدرس يكون بدري | missing ykoon after lamma | B8 | high | yes |
| 0923-20 | 49:58→50:01 | الـ or موعد الدكتور السنان.<br>_el or Maw3ed el-Doktoar el-snan._ | موعد دكتور السنان. ... Doctor's dentist. So the ال is at the end.<br>_Maw3ed Doktoar el-snan. ... Doctor's dentist. So the el is at the end._ | موعد الدكتور السنان → موعد دكتور السنان | el- on the middle noun of a profession chain | A6+A5 | high | yes |
| 0923-21 | 50:39→50:55 | بيت-بيتكير، بيتكير.<br>_Bait-بيتكير, بيتكير._ | أول إشي it changed.<br>_Awal eshi it changed._ | بيتغير → تغير | present for 'the appointment changed' | B5 | high | **missed** |
| 0923-22 | 50:49→51:06 | من واحد لتنتين. ... واحدة. ... الواحد. الواحدة للتنتين.<br>_men Wa7ad لتنتين. ... wa7de. ... el-Wa7ad. الواحدة l-el-Tentain._ | ساعة دايمًا feminine. So مش واحد، شو بتصير؟ ... الوحدة. لا.<br>_Saa3a Dayman feminine. So mesh Wa7ad, shu بتصير? ... el-Wa7deh. la._ | من واحد لتنتين → من الواحدة للتنتين | clock time needs feminine number + el- | E2+A1 | high | yes |
| 0923-23 | 53:46→54:06 | chalet أ-أخوي، أخـ-أخوي مراته أخوها.<br>_chalet aa-a5uy, A5-a5uy مراته أخوها._ | So أخو مرت أخوي. إنت it's just بالعكس. صح، بس بالعكس.<br>_So أخو مرت a5uy. enti it's just b-el-3aks. sa7, Bass b-el-3aks._ | أخوي مراته أخوها → أخو مرت أخوي | built the chain backwards with extra endings | A5+A3 | high | **missed** |

## Proposed new buckets — NOT added; Medi approves one at a time

### B18 — verb matches its subject  (26 fixes)

```json
{
 "id": "B18",
 "family": "B",
 "name": "verb matches its subject",
 "one_line": "The verb's person, gender and number must match who or what is doing it.",
 "examples": [
  [
   "el-sharika illi betbi3o bet8asselo",
   "the company that sells it washes it (sharika is feminine → bet-)"
  ],
  [
   "shu bey7ammsek?",
   "what excites you? (one thing → bey-, not bey…u)"
  ],
  [
   "huwwe byenbese6",
   "he gets happy (he → bye-/bi-)"
  ]
 ],
 "why": "English verbs barely change ('I/you/they sell'). Arabic verbs change for every person: a feminine noun takes the she-form, a plural takes -u, 'I' takes a-/ba-.",
 "detail": "Past-tense endings for a pronoun subject stay in B5. B18 is (1) the present prefix/ending for the wrong person (بيعصبني not بعصبني; تستعمل not تستعملي) and (2) a verb that doesn't match a NOUN subject's gender/number (the cup انكسرت; pizza دلت; meetings بيزهقوني). A8 stays for adjectives only.",
 "tally_rule": null
}
```

Fixes: 09-04 1:02:23 بيسبط→ببسّط · 09-10 40:37 انكسر→انكسرت · 09-11 20:48 (untranscribed you-form)→بتستعمل · 09-11 30:20 (العزومة) خرب→خربت · 09-11 57:29 راح يخرب→راح تخرب · 09-14 17:28 enkeser / enkeseru→enkeserat · 09-15 33:23 طيارتي تغير→طيارتي تغيرت · 09-15 35:33 برنامج (as feminine)→برنامج masculine → تغير · 09-16 32:28 رجله بيوجع→رجله بتوجع · 09-17 10:35 دبات (بدأت)→بدا · 09-21 11:24 بتغير→بتغيروا · 09-21 14:43 دلوا→دلت · 09-21 41:01 بيبيعوا→بتبيع · 09-21 41:15 بيغسل→بتغسل / بتغسله · 08-25 13:54 تفهم→يفهم · 08-25 49:19 بعصبني→بيعصبني · 09-04 56:32 بتنبسطتي→بتنبسطي · 09-05 11:53 ما بعرف→ما منعرف · 09-05 38:49 بيزعجوني→بيزعجني · 09-05 39:36 بيزعجوني→بيزعجني · 09-10 19:58 بيزعجني→بيزعجوني / بتزعجني · 09-14 09:14 أتذكرهم→نتذكرهم · 09-15 59:14 تجيبي→أجيب · 09-16 13:41 بيحمسوك→بيحمسك · 09-17 51:15 تستعملي→تستعمل · 09-18 29:08 (singular verb, garbled)→بيزهقوني

### A12 — pronoun matches who you mean  (2 fixes)

```json
{
 "id": "A12",
 "family": "A",
 "name": "pronoun matches who you mean",
 "one_line": "Pick the pronoun for the real person: humma for 'they', heyye for 'she'.",
 "examples": [
  [
   "humma ma byi5alsu",
   "they don't finish (his family → humma, not huwwe)"
  ],
  [
   "heyye",
   "she (his fiancée → heyye, not inti)"
  ]
 ],
 "why": "In a long sentence the pronoun drifts to the last one used.",
 "detail": "2 fixes, both 08-25 (هو→هما, إنتي→هي). Spellings are from the Arabizi converter (her Doc forms), not typed by Amal in these lessons. Small — could fold into B18 instead.",
 "tally_rule": null
}
```

Fixes: 08-25 22:13 هو→هما · 08-25 31:59 إنتي→هي

### C11 — noun, not verb, after a preposition  (1 fixes)

```json
{
 "id": "C11",
 "family": "C",
 "name": "noun, not verb, after a preposition",
 "one_line": "After bi / fi / min use the noun of the action, not a verb.",
 "examples": [
  [
   "ana ma3roof bi el-tabe5 el-kabab",
   "I'm known for cooking kebab (bi + el-tabe5, not bi + a6bo5)"
  ]
 ],
 "why": "English uses '-ing' after 'for/at'. Arabic uses the action's noun (masdar): tabe5 = cooking.",
 "detail": "1 fix (09-21 38:10, Medi asked; Amal: 'the noun. Noun is طبخ'). Example is her chat line 09-21 38:32.",
 "tally_rule": null
}
```

Fixes: 09-21 38:10 بـ أطبخ→بالطبخ

## Vocabulary fixes → Word Bank (not bucketed)

| lesson | time | Medi said | Amal gave | meaning |
|---|---|---|---|---|
| 2026-08-25 | 08:50 | مش مغني، مغـ، مغـ. | مغيم · _m8ayyem_ | cloudy (مغني = singer) |
| 2026-08-25 | 09:16 | درجة الحرارة حوالين، تمنتاش. | ثمانين · _thamanin_ | eighty (said eighteen); he fixed after her 'تمنتاش؟' |
| 2026-08-25 | 22:48 | هما ما بيخلصوا اشتغلتهم. | شغلهم · _shu8lhom_ | their work (used a verb form as the noun) |
| 2026-08-25 | 25:47 | بتضل تعصب، تعصب، زمان طويل. | لوقت طويل · _la-wa2et Taweel_ | for a long time |
| 2026-08-25 | 26:16 | أنا بـ بنزبط. Is it b- بنزبطها؟ | ببسطها · _babse6ha_ | I make her happy |
| 2026-08-25 | 29:25 | بأسف | بتأسف · _bat2assaf_ | I apologize |
| 2026-08-25 | 32:19 | وقت كتير. | وقت طويل · _wa2et Taweel_ | a long time |
| 2026-08-25 | 32:27 | أنا بس بتها. | ببسطها · _babse6ha_ | I make her happy (forgot the verb) |
| 2026-08-25 | 36:06 | بنتطلع بنات أخوي | بندير بالنا على · _بندير بالنا 'ala_ | we take care of / watch (kids) |
| 2026-08-25 | 42:09 | Is, ‹isma›. | اسم · _Esem_ | noun |
| 2026-08-25 | 45:14 | do you say الكل if I wanna say in general? | بشكل عام · _بشكل 'am_ | in general |
| 2026-08-25 | 51:09 | هي ما بتعصب، آآآه، سهل كمان | بسرعة · _Bsur3a_ | quickly (said easy) |
| 2026-08-25 | 52:12 | إحنا مظلوم | رايق · _رايق_ | chill/calm (مظلوم = oppressed) |
| 2026-09-04 | 02:01 | (not transcribed) | طريقة · _Tari2a_ | way/method (vs طريق road) |
| 2026-09-04 | 02:31 | To learn would be أتأل-- | أتعلم · _at3allam_ | to learn |
| 2026-09-04 | 03:43 | I excited؟ أنا بهمس. | بتحمس · _bat7ammas_ | I get excited (بهمس = I whisper) |
| 2026-09-04 | 07:18 | il grammar. Do I know grammar? | قواعد · _قواعد_ | grammar |
| 2026-09-04 | 10:16 | an easy answer, I should say. | سهل · _Sahel_ | easy |
| 2026-09-04 | 20:38 | Muhadath-... I don't remember. | محادثة · _Mu7aadase_ | conversation |
| 2026-09-04 | 23:51 | Oh my God, bees. What was bees? | نحل · _Na7el_ | bees |
| 2026-09-04 | 26:19 | Arabiyi, aswad or- | سيء · _Sayyi2_ | bad |
| 2026-09-04 | 26:38 | getting worse so she would it be akun, | عم بصير · _3aam ba9eer_ | is becoming (not akoon) |
| 2026-09-04 | 27:46 | Bansabit? But- | مبسوط · _Mabsoo6_ | happy (adjective, not the verb) |
| 2026-09-04 | 1:01:07 | or أكثر؟ أحسن right? | أكتر · _Aktar_ | most (أحسن = best) |
| 2026-09-05 | 10:38 | nafs? | الكل · _El-kul_ | everyone |
| 2026-09-05 | 20:11 | I don't know how to say too much ... Ziyadi? | كتير / زيادة · _Kteer / Ziaadeh_ | too much / extra |
| 2026-09-05 | 23:50 | Mutab? ... No. | متعب · _Mut3eb_ | tiring |
| 2026-09-05 | 53:16 | anabanzaj, lama... | إذا · _Iza_ | if (not when) |
| 2026-09-05 | 55:16 | لما أكون شبعان | شبعان · _Shab3aan_ | full (not hot) |
| 2026-09-10 | 01:48 | كيف كان العروسة؟ عروس؟ | عرس · _عرس_ | wedding (not bride) |
| 2026-09-10 | 08:46 | Is it raki? What was electricity? | كهربا · _Kahraba_ | electricity |
| 2026-09-10 | 09:10 | مهندس كهرباء | كهربجي · _كهربجي_ | electrician |
| 2026-09-10 | 11:02 | صلاحلي, helps to me | ساعدني · _sa3adni_ | helped me (not fixed) |
| 2026-09-10 | 12:36 | اليوم دولت stayed | ضليت · _dallait_ | I stayed |
| 2026-09-10 | 23:52 | intent is, comes from ... مهم | قصد · _Qaṣd_ | intention |
| 2026-09-10 | 26:48 | شول، فيل، | بقيم · _Ba2eem_ | I remove |
| 2026-09-10 | 43:47 | كان عمرها إحداعش | إتناش · _إتناش_ | twelve (not eleven) |
| 2026-09-10 | 49:24 | إن كسر من الحرارة | خرب / خربان · _5arab / 5arbaan_ | stopped working (not physically broke) |
| 2026-09-10 | 59:16 | if you heat up food ... this verb? | بسخن · _بسخن_ | I heat up (food) |
| 2026-09-11 | 01:04 | ملايين، ملا-مليان | مليان · _Malyaan_ | full (busy) |
| 2026-09-11 | 02:20 | What was the word for review? | مراجعة / براجع · _Muraaja3a / baraaje3_ | review |
| 2026-09-11 | 06:57 | How do I say dark again؟ | عتمة · _3etme_ | darkness |
| 2026-09-11 | 09:03 | Is it Asafa؟ Is that stars؟ | (عاصفة) storm; نجمة = star · _(3aasefe) storm; Nejme = star_ | storm / star |
| 2026-09-11 | 10:54 | قربان. | خربان · _5arbaan_ | broken |
| 2026-09-11 | 12:23 | تحت الكلمة. | آخر الكلمة · _2aa5er el-kilme_ | end of the word |
| 2026-09-11 | 18:04 | صححته. | صلحته · _صلحته_ | I fixed it |
| 2026-09-11 | 25:00 | ما تفتحي | ما بتحطي · _ma bet7utti_ | put (in the fridge), not open |
| 2026-09-11 | 37:35 | ثانورك. | تنورة is skirt (he chose فستانك) · _Tannoora is skirt (he chose fustaanek)_ | skirt / dress |
| 2026-09-11 | 49:40 | just akhil and ... | (untranscribed meal/dish word) · _(untranscribed meal/dish word)_ | meal / dish |
| 2026-09-14 | 04:05 | interrupts me. I don't know how to say interrupt. | بيعطوني (STT; chat bey2aat3uni) · _بيعطوني (STT; chat bey2aat3uni)_ | they interrupt me |
| 2026-09-14 | 04:50 | do you guys use fas-فصل for ... a sports season? | موسم · _موسم_ | season (sports) |
| 2026-09-14 | 07:00 | players, like the athletes. | لاعبين · _لاعبين_ | players |
| 2026-09-14 | 07:26 | our own teams | فريق / فرقنا · _فريق / فرقنا_ | team / our teams |
| 2026-09-14 | 24:43 | م-م-من شاف، من شاف؟ | الجو ناشف · _El-jaw Naashef_ | the weather is dry |
| 2026-09-14 | 51:58 | akthar min hada. | هيك · _Heik_ | more than this (like this) |
| 2026-09-14 | 55:06 | مشاوي. | ممكن؟ (plural مشاوير only in chat) · _Mumken? (plural مشاوير only in chat)_ | outings |
| 2026-09-15 | 04:05 | مرفوف؟ What was ground؟ | مفروم · _mafroom_ | ground (meat) |
| 2026-09-15 | 06:46 | rah bad, um, metakhri | روّح · _Roo7_ | went home |
| 2026-09-15 | 08:51 | fatad means, like, you choose? | بفضّل · _Bafaddel_ | I prefer |
| 2026-09-15 | 18:18 | aqlab snenha | سنان · _snan_ | teeth (سنين = years) |
| 2026-09-15 | 26:46 | الولاد عطلوا | قاتلوا بعض · _2aatalu Ba3ad_ | they fought each other |
| 2026-09-15 | 28:13 | Do I know how to say other? | راس الثاني · _Raas الثاني_ | the other one's head |
| 2026-09-15 | 32:18 | وقت ال... flight | طيارة · _6ayyaara_ | plane / flight |
| 2026-09-15 | 39:52 | الآن | الألوان · _el-Alwaan_ | the colors |
| 2026-09-16 | 04:12 | Badat started. Badat. | بلّشت · _ballashet_ | started (everyday word) |
| 2026-09-16 | 05:30 | [speaking Arabic] | صغيرة · _z8eera_ | young/small (f) |
| 2026-09-16 | 06:27 | If I say [Arabic], it wouldn't make sense? | أخليها تصير · _أخليها تصير_ | let her become |
| 2026-09-16 | 19:28 | fi el shara | طريق · _6ariq_ | road / the way |
| 2026-09-16 | 21:02 | El safra. | السفر · _el-Safar_ | travel (safra = one trip) |
| 2026-09-16 | 25:36 |  | نكمّل · _نكمّل_ | we continue |
| 2026-09-16 | 52:30 | enno huwe, | هم · _humme_ | they |
| 2026-09-16 | 54:40 | ileshu avadi | الأسبوع الماضي · _el-Usboo3 el-Maadi_ | last week |
| 2026-09-16 | 55:29 | ma ando bilax | عكس / بالعكس · _3aks / b-el-3aks_ | opposite / on the contrary |
| 2026-09-16 | 1:00:26 | Bish-bishik? | أشياءك · _أشياءك_ | your things |
| 2026-09-17 | 04:35 | زفير ماي | خفيف · _5afeef_ | light / thin |
| 2026-09-17 | 06:32 | sijal | سجق · _سجق_ | sausage |
| 2026-09-17 | 11:25 | ما قايمة | مغيمة · _M8ayyme_ | cloudy |
| 2026-09-17 | 12:26 | زبال | غبرة · _غبرة_ | dust |
| 2026-09-17 | 17:14 | waz (Farsi) | واضح · _واضح_ | obvious / clear |
| 2026-09-18 | 01:24 | الصباح | الصبح · _el-sube7_ | (in the) morning |
| 2026-09-18 | 02:40 | معروف | مفرومة · _mafrumeh_ | minced / ground |
| 2026-09-18 | 42:31 | (asked) | نهاية · _نهاية_ | end (ma ilu nihaya = endless) |
| 2026-09-18 | 59:51 | zah- zahai | ضحّكه (tahaki) · _ضحّكه (tahaki)_ | make him laugh (he used the 'bore' verb) |
| 2026-09-19 | 06:36 | تسعة عشرين | تسعطاش (19) · _tese3ta3sh (19)_ | nineteen |
| 2026-09-19 | 07:09 | تسعش ستة | تسعطاش تسعة · _tese3ta3sh tes'ah_ | 19/9 - said month 6 for September |
| 2026-09-19 | 08:54 | أب الامبارح | قبل امبارح / أول امبارح · _2abel embare7 / Awal embare7_ | day before yesterday |
| 2026-09-19 | 09:35 | شو يعني ريحة؟ | ريحة · _ree7a_ | smell |
| 2026-09-19 | 10:25 | كمي | غامق · _8aame2_ | dark (colour) |
| 2026-09-19 | 11:43 | سكرت | صورت · _9awwaret_ | photographed |
| 2026-09-19 | 14:16 | back sir | اكسر · _ekser_ | break (physically) vs خرب ruin |
| 2026-09-19 | 16:25 | to inflict sadness (زعلت) | زهقت مش زعلت · _zahha2et mesh z3elet_ | got bored, not got sad |
| 2026-09-19 | 20:27 | What happened boring? | بيزعل، مش بيزهق · _beyza33el, mesh beyzahhe2_ | saddening, not boring |
| 2026-09-19 | 24:10 | Were you sad from what happened? | انزعجتي · _انزعجتي_ | got annoyed (not sad) |
| 2026-09-19 | 44:49 | zar-zarha, zar'a? | زهق / زهقان · _Zahhe2 / Zah2aan_ | bored |
| 2026-09-19 | 49:30 | don't be annoyed | ما تزعلوا منه · _ma تزعلوا منه_ | don't be sad/upset (not annoyed) |
| 2026-09-21 | 01:43 | شوي متوتر | مضغوط · _Mad8oo6_ | stressed |
| 2026-09-21 | 03:30 | كامل نسيتو | كليًا · _Kulliyyan_ | completely |
| 2026-09-21 | 04:12 | مرجة | نراجع / مراجعة · _nraaje3 / Muraaja3a_ | we review / review (n) |
| 2026-09-21 | 05:58 | فضاء | فصل · _fa9il_ | season |
| 2026-09-21 | 06:13 | ربيع | خريف · _5areef_ | autumn |
| 2026-09-21 | 16:22 | جايبة لي pizza | كان جاي على بالك · _kaan Jaay 'ala baalak_ | you felt like (pizza) |
| 2026-09-21 | 20:55 | pastry | كعكة / بسكوتة · _ka3ke / بسكوتة_ | pastry / biscuit |
| 2026-09-21 | 23:13 | What was price? | حق · _7a22_ | price |
| 2026-09-21 | 31:26 | Shumel | شو مال · _shu مال_ | what's wrong with |
| 2026-09-21 | 34:07 | Bihinna | بيهمنا · _بيهمنا_ | it matters to us |
| 2026-09-21 | 42:11 | yitbukhu | بيخليه يفشفش · _بيخليه يفشفش_ | makes it swell (not cook) |
| 2026-09-21 | 43:16 | the rice cooker | ماكينة الرز · _ماكينة el-Ruz_ | rice cooker |
| 2026-09-21 | 43:46 | بعمله الـ طريق طويل | الطريقة · _el-Tari2a_ | the way/method (not road) |
| 2026-09-21 | 44:43 | ثلث ساعية | ثلث ساعة · _Tult Saa3a_ | a third of an hour |
| 2026-09-21 | 46:23 | زبداية | زبدة · _Zibdeh_ | butter |
| 2026-09-21 | 46:48 | بزيد الـ- الـ زبداية | زبدة · _Zibdeh_ | butter (again) |
| 2026-09-21 | 48:33 | الـ تحت تاني | الجهة / عكس · _الجهة / 3aks_ | side / opposite end |
| 2026-09-21 | 48:59 | المقلاة | الملعقة / مغرفة · _el-ma3la2a / Ma8rafa_ | spoon / ladle |
| 2026-09-21 | 50:33 | wa'atir | واطية · _waatya_ | low (temperature) |
| 2026-09-21 | 50:56 | Sot tawil or sot asir nar? | نار هادية (مش صوت) · _Naar Haadye (mesh Soat)_ | low/calm flame |
| 2026-09-21 | 51:45 | mishtihi | مستوي · _Mistwi_ | cooked/done |
| 2026-09-21 | 51:58 | al tahet al roz | الرز من تحت · _el-Ruz men Ta7t_ | the bottom rice (vs under the rice) |
| 2026-09-21 | 53:28 | ali | مقلي · _Ma2la_ | fried |
| 2026-09-21 | 54:42 | saffron | الزعفران · _الزعفران_ | saffron |
| 2026-09-21 | 55:05 | awali is country / alam | دولة / العالم · _Dawle / el-3aalam_ | country / the world |
| 2026-09-21 | 57:57 | Sa min, sa minik? | معك حق · _ma3ak 7a22_ | you're right |
| 2026-09-21 | 1:02:14 | مخية | مقلوبة · _ma2loobe_ | maqluba (dish) |
| 2026-09-21 | 1:03:55 | للأسف | للأسف · _l-el-aasef_ | unfortunately |
| 2026-09-21 | 1:06:35 | مين بيدفع؟ | بيفتح · _بيفتح_ | opens |
| 2026-09-21 | 1:09:17 | I've been told sarlik, no? | (say: some people told me) · _(say: some people told me)_ | I've been told |
| 2026-09-21 | 1:10:54 | ma ba'rif | محادثة · _Mu7aadase_ | conversation |
| 2026-09-21 | 1:11:14 | min ikhak? | معك حق · _ma3ak 7a22_ | you're right (idiom recall) |
| 2026-09-23 | 10:10 |  | ما إله طعم (ما not مع; إله) · _ma إله 6a3em (ma not ma'; إله)_ | it has no taste |
| 2026-09-23 | 15:43 |  | خريف (not خفيف) · _5areef (not 5afeef)_ | autumn |
| 2026-09-23 | 16:12 |  | بدأ / بلش · _bada / ballash_ | started |
| 2026-09-23 | 19:02 |  | غلطة · _غلطة_ | mistake (vs خيار option) |
| 2026-09-23 | 20:28 |  | حجز / بحجز (طلب is order) · _7ajez / ba7jez (6alab is order)_ | booking / I book |
| 2026-09-23 | 22:14 |  | منظر (not منظرة) · _Manzar (not منظرة)_ | view - noun is masculine |
| 2026-09-23 | 24:56 | مم ما وايه؟ | حجز · _7ajez_ | booking |
| 2026-09-23 | 28:43 | in half hour more | كمان نص ساعة · _Kamaan Noss Saa3a_ | in half an hour |
| 2026-09-23 | 31:31 | نصيب ... نصينة؟ | نسيت / نسينا · _nseet / nseena_ | we forgot |
| 2026-09-23 | 32:17 | مصاري | cash · _cash_ | cash (just say cash) |
| 2026-09-23 | 33:25 | أنا لازم أشكي | أنا بدي أشتكي · _Ana beddi Eshki_ | I want to complain |
| 2026-09-23 | 34:49 | سألت | طلبت · _6alabet_ | asked for (not asked a question) |
| 2026-09-23 | 40:45 | بدزكر / تزكر | تذكرة، تذاكر · _Tazkara, تذاكر_ | ticket(s) |
| 2026-09-23 | 45:47 | قريبًا من السفر | قريب من السفر · _2areeb men el-Safar_ | close to (not 'soon') |
| 2026-09-23 | 46:30 | the trip | يوم السفر · _Yoam el-Safar_ | the day of the trip |
| 2026-09-23 | 55:16 | passenger? | راكب · _Raakeb_ | passenger |
| 2026-09-23 | 55:48 | driver? | سواق / شوفير · _Sawwaa2 / شوفير_ | driver |
| 2026-09-23 | 57:28 | [speaking foreign language] | نوخذ دور / بالدور · _نوخذ door / بالدور_ | take turns |
| 2026-09-23 | 58:38 | Would I say [..] | بعيد ساعتين · _Ba3eed ساعتين_ | two hours away |
| 2026-09-23 | 1:02:10 | [speaking Arabic] | أعمل or أخلص - just one · _E3mel or أخلص - just one_ | use one verb, not both |
