# 05 — Palestinian Arabic Specifics: Dialect, Diglossia, Arabizi, and the Farsi Advantage
*Date 2026-09-03. Terms: MSA = Modern Standard Arabic (written/news register). Dialect = spoken variety. Diglossia = one community using two varieties for different jobs. Arabizi = Arabic in Latin letters + digits.*

### 1. Diglossia and dialect-first learning
MSA-first "neither reflects the sociolinguistic reality nor gives communicative skills" ([Georgetown Press, *Arabic as One Language*](https://press.georgetown.edu/Book/Arabic-as-One-Language)); Al-Batal 2017 collects 16 chapters of program data for the *integrated approach*; nobody argues dialect harms MSA ([OUP review](https://academic.oup.com/applij/article-abstract/41/6/1017/5108482)). Shiri 2013 (N=371): study abroad shifted learners toward dialect ([DOI](https://doi.org/10.1111/flan.12058)). Palmer 2007: "Teaching only the standard variety is a disservice."
**Medi's case is easier:** speech only, native tutor. Skipping MSA costs news/formal writing only. Palestinian shares ~50% common words with MSA ([Wikipedia](https://en.wikipedia.org/wiki/Levantine_Arabic)) so MSA resources are usable with a spoken-form check.
**Pitfalls:** dictionaries/ASR are MSA-trained; MSA grammar (case endings, dual verbs) absent from speech; tutors drift to MSA when asked for the "proper" form. Ask Amal for the *street* form explicitly.

### 2. Palestinian vs the rest of Levantine
Levantine (~60M) is a continuum; Palestinian = South Levantine with Jordanian ([Wikipedia](https://en.wikipedia.org/wiki/Palestinian_Arabic)):

| Variety | ق | ك | ث ذ ظ | Markers |
|---|---|---|---|---|
| **Urban** (Jerusalem, Nablus, Haifa, Jaffa) | ʔ (Arabizi **2**) | k | t/d/z | closest to Damascus/Beirut |
| **Rural** (central West Bank) | emphatic k | **ch** | kept | keeps feminine plural |
| **Hebron area, Gaza** | **g** | k or ch | Gaza t/d | mixes urban + Bedouin |
| **Bedouin** (Negev, Galilee) | q or g | k | kept | Hijazi/Syrian-desert types |
| **'48 / Galilee towns** | ʔ in towns | less ch | mixed | Hebrew loanwords |

Palestinian markers: *ʔiši* "thing" (vs Syrian *ši*); negation adds **-sh** (*ma baʕrifsh*).
**What Amal is probably teaching:** urban Palestinian (ق=2, ك=k, no ch). Ask her once: "Do you say *2alb*, *galb* or *kalb* for heart at home?" Record on her profile.
**"One dialect" = ** one phonology (urban), one negation (*ma…sh*), one set of function words (*hēk, hōn, halla2, kamān, ʔiši, bidd-*). Regional synonyms stored but tagged.
References: Shahin, "Palestinian Arabic" (Brill EALL); Cowell, *Reference Grammar of Syrian Arabic* (Georgetown 1964); Elihay, *Speaking Arabic* (4 vols) + *Olive Tree Dictionary* [editions unverified].

### 3. Structured resources (ranked for this program)
| # | Resource | Cost | Palestinian? | Exportable | Source |
|---|---|---|---|---|---|
| 1 | **Maknuune** (CAMeL/Birzeit) | Free CC-BY-4.0; 36k entries, 17k lemmas, script + phonological transcription + gloss + plurals | **Yes** | **Yes, open data** — the seed | [arXiv 2210.12985](https://arxiv.org/abs/2210.12985) |
| 2 | **Curras/Currasat** (Birzeit SINA) | Free (registration) | **Yes** | Partial | [Jarrar 2016](https://doi.org/10.1007/s10579-016-9370-7), [sina.birzeit.edu/curras](https://sina.birzeit.edu/curras/) |
| 3 | **learnlevantine.com** | $10/mo, $50/yr, $100 life; 2,785-word dictionary, 1,000-verb conjugator, variant flags | Tagged | No export (scrapable, check ToS) | [site](https://learnlevantine.com/) |
| 4 | **Living Arabic Project** | Free web | Levantine | No API | [site](https://livingarabic.com/) |
| 5 | **Playaling** | $15.99/mo; Palestinian sub-filter, 1,000+ videos | **Yes** | Transcript PDFs | [site](https://playaling.com/) |
| 6 | Elihay *Speaking Arabic* + *Olive Tree Dictionary* | ~$40-60/vol [unverified] | **Yes** | Paper/OCR | Minerva |
| 7 | Isleem *Colloquial Palestinian Arabic* | Paper [unverified] | **Yes** | Paper | — |
| 8 | Lingualism Palestinian titles | PDF ~$10-20 [titles unverified] | Claimed | PDF | [site](https://lingualism.com/) |
| 9 | Talk in Arabic | Sub | Levantine | No | [site](https://talkinarabic.com/) |
| 10 | Mango Levantine | ~$8-12/mo [unverified] | Syrian-leaning | No | — |
| 11 | ArabicPod101 | Freemium | Mostly MSA/Egyptian | No | [site](https://www.arabicpod101.com/) |
| 12 | Flinn 2026, Levantine word list (Iowa State thesis) | Free | Levantine | Likely [403] | [DOI](https://doi.org/10.31274/td-20260223-102) |

Conflict note: first research batch found an Overworded Levantine 3,000-word CSV; this pass could not confirm the site. Verify before use.
**Recommendation:** seed from Maknuune; frequency from Curras/Flinn; verb tables from learnlevantine; listening input from Playaling tagged Palestinian.

### 4. Arabizi
History: late-1990s chat workaround; digits shaped like letters ([Wikipedia](https://en.wikipedia.org/wiki/Arabic_chat_alphabet)). Stable core: 2=ء 3=ع 7=ح 5=خ 9=ص 6=ط. Variation: 8=غ mostly Levant (else *gh*); 2 doubles for ق in urban Levant; Gulf/Jordan use g/q; ة written a/e/ah/eh inconsistently.
Pedagogy research thin: Shweiry 2024 ([Springer](https://doi.org/10.1007/978-981-97-8594-0)) [paywalled]. Consensus: fine as a bridge for voice-first learners **if consistent**; inconsistent Arabizi silently teaches wrong vowels. For Medi (reads Persian script): Arabizi carries *pronunciation*, script carries *identity/lookup*.
Conversion tools: Shazal, Usman & Habash 2020 80.6% word accuracy ([ACL](https://aclanthology.org/2020.wanlp-1.15/)); Atar (Talafha 2021) 79% ([DOI](https://doi.org/10.11591/ijece.v11i3.pp2327-2334)); CAMeL Tools has no Arabizi module ([GitHub](https://github.com/CAMeL-Lab/camel_tools)); arabizi.io keyboard, no API. → ~80% accuracy means every machine conversion is a suggestion, never an auto-write.

**Canonical Arabizi spec for the word bank:**
| Sound | Canonical | Never |
|---|---|---|
| ء / urban ق | **2** (store `qaf_origin` flag) | q, k |
| ع | **3** | ', aa |
| ح | **7** | h |
| خ | **5** | kh |
| غ | **8** | gh |
| ط | **6** | t |
| ص | **9** | s |
| ض | **9'** | d |
| ظ | **6'** | z |
| ث / ذ | t / d (urban), s / z (learned words) | th, dh |
| ش | **sh** | ch, $ |
| ج | **j** | g |
| long vowels | aa ii uu; ē ō = ee oo | — |
| shadda | double the consonant (*sitt, kullo*) | apostrophe |
| ة | -e after front vowels, -a after back (*madrase, sa3a*); idafa → -et/-at | ah, eh |
| ال + sun letter | as spoken (*ish-shams*); `article` field separate | el-, al- |
| clitics | hyphen: *bidd-i, b-yiktob, ma-ba3rif-sh* | — |

Canonical = what Amal *says* in urban Palestinian; native-texted variants go in `variants[]`.

### 5. The Farsi advantage (and its traps)
**Script:** Persian = Arabic alphabet + پ چ ژ گ. Normalize ی/ک vs ي/ك codepoints; Arabic ة vs Persian ه/ت.
**Vocabulary:** ~40% of Persian words are Arabic-origin [headline figure unverified]; imported as frozen forms, roots not productive. Instant recognition of *kitāb, madrase, waqt, sā3a, mumkin, lāzim, shukran*. Drift table (confirm each with Amal before flagging):

| Word | Persian | Palestinian | Trap |
|---|---|---|---|
| تعارف ta'ārof | ritual politeness | *ta3āruf* = getting acquainted | false friend |
| حرف harf | word/talk | *7arf* = a letter; "talk" = *7aki* | false friend |
| فامیل fāmil | relatives | *3ēle / ahl* | false friend |
| نفر nafar | person counter | counter is *wā7ad/shakhs* | false friend |
| صحبت sohbat | conversation | *9u7be* = company/friendship | false friend |
| میوه mive | fruit | *fawākih* | Persian-only |
| قابل ghābel | worthy/able | *2ābil* = about to / capable | ق sound |
| غلط ghalat | wrong | *ghala6* | ط pronunciation |
| کلمه kalame | word | *kilme* | vowels |
| ادب adab · زحمت zahmat · مشغول mashghul · مریض mariz · خدمت khedmat · جواب javāb | same | same | fine |

**Phonology — Persian collapses what Arabic distinguishes** ([Wikipedia](https://en.wikipedia.org/wiki/Persian_phonology)): ق=غ, ت=ط, س=ص=ث, ز=ذ=ض=ظ, ح=ه, ع=ء; no vowel length; no initial clusters. **Predictable errors:** (1) ع → glottal/dropped; (2) ح → h (*7abibi → habibi*); (3) emphatics flattened, flattening the vowel (*9ēf* summer → *sēf* sword); (4) ق → gh; (5) long/short vowel merger (*kātab* vs *katab*); (6) epenthetic *e* (*ktāb → ketāb*); (7) final-syllable stress; (8) Persian /æ/ for short a. No published study of Persian-L1 Arabic learners found; list derived from phonology contrast [unverified].
**Grammar mismatches:** no gender, no dual, no agreement, SOV, ezafe not idafa, suffix plurals, *mi-* present prefix (helps: same idea as Levantine *b-*). Predictable errors: drop gender agreement; forget definite article on adjectives (*il-bēt kbīr* = "the house is big"); suffix plurals for broken plurals; verb last; ezafe *-e* for possession; miss feminine-singular agreement on non-human plurals.

### 6. Common learner errors in Levantine (all learners)
From [Levantine grammar](https://en.wikipedia.org/wiki/Levantine_Arabic_grammar), Azaz 2023, Alhawary 2017; no tagged Levantine learner corpus exists:
1. **b-prefix**: dropped in plain present, or kept after *bidd-, lāzim, mumkin, ra7*.
2. **Negation**: *ma…sh* on verbs, *mish* on nouns/adjectives; mixed up.
3. **Resumptive pronoun** in *illi* clauses (*illi shuft-o*); omitted.
4. **Gender agreement**; non-human plurals take feminine singular.
5. **Definite article on adjectives**: *il-bēt il-kbīr* vs *il-bēt kbīr*.
6. **Numbers**: 3-10 + plural, 11+ + singular; dual *-ēn*.
7. **Idafa vs taba3**; definiteness only on last noun.
8. **Suffix shapes** after vowels vs consonants.
9. **Word order** SVO; questions keep order.
10. **Vowel dropping** in fast speech restored by learner.

### 7. Speech technology (status only)
| Engine | Levantine/Palestinian | Note |
|---|---|---|
| ElevenLabs Scribe v2 | Docs show "Arabic (ara)" only, 10-20% WER tier ([docs](https://elevenlabs.io/docs/capabilities/speech-to-text)) | **Conflict:** batch-1 research found a Palestinian listing on the marketing page; Phase 0 verifies |
| Cohere Transcribe | ~40% WER Levantine | not re-verified |
| Whisper | Talafha 2023 Interspeech: deteriorates on Jordan/Palestine ([paper](https://www.isca-archive.org/interspeech_2023/talafha23_interspeech.html)) | only Palestinian eval found |
| Any | No public Palestinian benchmark | transcripts need human correction |

### Implications for our tool (10)
- Tag every word `region_variant` (urban/rural/Gaza/Galilee/Bedouin); default deck = urban Palestinian.
- Three spellings per entry: canonical Arabizi (§4 spec), normalized script, `variants[]`.
- `qaf_origin` / `kaf_origin` flags so g/ch forms are derived, never typed.
- Seed from Maknuune; import MSA gloss, plural, feminine as-is.
- `farsi_cognate` field + `false_friend` flag + Persian sense; Amal confirms before it shows.
- Ship the Persian-L1 error taxonomy (§5) + Levantine list (§6) as a fixed enum for tagging corrections.
- Log Amal's "2alb/galb/kalb" answer on her profile; sets default variant.
- Mark every entry's source (Maknuune / tutor / Playaling / learner) to filter MSA-leaning imports.
- Machine Arabizi conversion = suggestion queue, never auto-write.
- Every transcript is a draft: store audio, machine text, human-corrected text, engine name, date.
