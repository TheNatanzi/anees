# Anees Word Bank — Product Specification

Consolidated September 17, 2026. This document contains the current agreed rules. Superseded proposals have been removed; remaining gaps are listed separately and are not approved behavior. The local Word Bank page and scoring engine are implemented and tested. Live synchronization and complete lesson evidence remain outstanding; see the implementation report for current limitations.

## Overview

| Area | Agreed design |
|---|---|
| Summary | Overall Accuracy, Total Words Known, 30-Day Memory, 30-Day Words, Flashcards Week, Flashcard Acc. |
| Controls | All Words / Needs Practice, multilingual search, status/topic filters, recency options and sorting |
| Rows | Expandable word groups with separate tense or singular/plural badges |
| Evidence | Real lesson sentences and corrections, plus independent flashcard history |
| Source | Amal's vocabulary document and manual review/entry of missing words |

### Shared definitions

A **row** groups forms for display. A **scored entry** is the unit used for statuses, dashboard word counts, and accuracy denominators. References to unique words below mean these entries, not parent rows.

- Verb: Past, Present, Future, and Command each score and count separately.
- Noun: masculine/feminine share one singular entry; plural is separate.
- Verb–preposition uses have independent scores but add no extra dashboard words.
- Every metric retains its own eligibility rules; displayed/generated does not mean tested or known.
- Spoken vocabulary and flashcards are independent tracks.

## 1. Source and review workflow

### Vocabulary source

If Amal deletes a word from the source document, archive it: remove it from the active Word Bank and active totals while preserving its scores and lesson history.

When Amal changes a word's spelling in the document, update its displayed spelling while preserving its lesson clips, scores, and history, provided it is the same word. A spelling edit alone does not create a new vocabulary entry or reset progress.

The Word Bank uses Amal's Arabic Full Vocabulary List and must stay synced with it.

Source: https://docs.google.com/document/d/1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw/edit

Live synchronization is a requirement, not a claim that it has been verified or implemented in this task.

### Missing vocabulary and Amal review

Amal normally teaches the lesson and then adds vocabulary to the Vocab document. Give her time to complete that normal process before asking about missing words.

Agreed sequence:

1. Wait 24 hours after the lesson ends.
2. Sync/read the current Vocab document.
3. Prepare a review list of lesson words still missing from the document.
4. Ask Amal to determine whether each candidate was intended to enter Medi's vocabulary.

Do not ask her about missing words before the 24-hour waiting period. A word being spoken is not, by itself, approval to add it to the Word Bank. Existing gaps in the document also need to be addressed.

Amal manually enters approved missing words into the Vocab document. Anees must not add them automatically. Keep each candidate pending until Amal confirms she has entered it; then sync and verify the entry before marking the candidate resolved. Confirmation alone does not create a Word Bank entry: the document remains the source of truth.

Check available past lessons against the current Vocab document for missing words. Combine duplicate candidates into one review list for Amal. Use the same manual-entry and confirmation workflow: Amal decides whether the word belongs, enters approved words herself, confirms completion, and Anees syncs and verifies the entry before resolving the candidate. This is an agreed feature requirement; no historical scan or message to Amal has been performed in this planning session.

### Lesson panel: review requirements to revisit

When designing the lesson panel, include an after-lesson review for Amal covering possible mistranscriptions and a breakdown of vocabulary and grammar mistakes. She can review the transcript evidence and the proposed classifications, not just missing words. Keep suspected transcription problems distinguishable from confirmed learner mistakes.

Missing evidence stays null/ignored until sufficiently clarified, as specified below. Detailed lesson-panel layout and review interactions will be designed later. No review has been sent to Amal in this planning session.

## 2. Row structure and language

### Word & Forms row

Start with all word rows collapsed. Allow multiple rows to remain expanded at the same time so the learner can compare words without closing previously opened details.

Group a word's masculine, feminine, and plural forms into one expandable word row. Keep Arabizi primary and Arabic script secondary for each form.

### Language display priority

Always prioritize Arabizi throughout Anees. In the Word & Forms column, show Arabizi large and bold, with Arabic script smaller underneath. Apply this priority consistently when presenting vocabulary and forms elsewhere in the interface.

### English Translation column

Use Amal's English wording from the Vocab document. Keep distinct meanings associated with their corresponding word uses and verb–preposition combinations rather than merging them into an undifferentiated definition.

### Type & Forms labels

Display the word-type label in English, with its Arabic equivalent in smaller text underneath. This specific bilingual label treatment applies to Type & Forms; vocabulary and conjugated forms continue to prioritize Arabizi.

### Root & Pattern removed

Do not display Root or Pattern in the Word Bank. The user removed both fields; this supersedes the earlier placement instruction.

### Verb tenses

Use the first-person singular present tense (the "I" present form) as the default display name for each verb, following Amal's spelling.

Keep one expandable parent verb row, divided into Past, Present, Future, and Command. Score each tense separately and count each tense as an individual word for word-score calculations and dashboard word counts.

Each tense follows the agreed scoring system independently. Verb–preposition uses with different meanings remain separately scored within each tense; they do not themselves add extra words to the count. Arabizi remains primary throughout.

The collapsed parent verb row displays four small, labeled status badges: Past, Present, Future, and Command, each showing its independent status (including Untested). Do not replace them with one combined verb status. For example, a verb can show Past: Shaky, Present: Mastered, Future: Good, and Command: Untested; these are illustrative statuses, not learner results.

Within each tense, provide an expand button revealing applicable person forms (I, you, he/she, we, they, with relevant gender/number variants). Keep this detail collapsed in the compact view. Command shows applicable addressee forms rather than inventing first- or third-person imperative forms. Expanding person forms does not introduce separate vocabulary word counts or change the grammar/null correction rules.

### Noun-form scoring

Adjectives show their documented masculine and feminine forms together as compact slash-separated Arabizi on the main row, with smaller Arabic underneath. Include documented plurals when available. Expanded details retain scores and history without repeating the adjective words or gender list. Read both separate M/F source rows and slash-separated source forms; do not treat alternative transliterations as different genders.

Show the actual singular and plural words on the collapsed main row as well as in the expanded details, for example **Kitaab / Kutub**, with smaller Arabic underneath. Keep the separate Singular and Plural status badges alongside them. Users do not need to expand a noun to see its plural.

Collapsed noun rows show two labeled status badges: Singular and Plural. Singular represents the shared masculine/feminine score; Plural shows its independent score. Each badge can show Untested where applicable, consistent with the verb tense badges.

Keep one expandable noun row. Masculine and feminine forms share one vocabulary score and attempt history; plural has a separate score and attempt history. Both follow the agreed scoring system, and grammar-only corrections remain null attempts. Count singular (masculine/feminine combined) and plural as two separate entries in dashboard word counts, consistent with separately scored verb tenses. Each entry remains subject to the relevant metric's existing eligibility rules, including exclusion of Untested entries from accuracy.

### Filling in undocumented tense forms

The user authorizes Anees to infer/generate missing tense forms for documented verbs, following Amal's Arabizi spelling and Palestinian Arabic conventions. Do not limit the expanded verb display to tenses explicitly written in the Vocab document. This is permission to enrich an existing verb's display, not permission to add new lexical verbs automatically or write generated forms into Amal's document.

Keep the provenance of forms clear: documented by Amal versus generated/inferred. Generated forms are not evidence that Amal taught them or that the learner knows them; they remain Untested until qualifying scored use. Use documented forms and patterns to guide generation; genuine uncertainty or competing forms can be presented for Amal's review rather than described as verified.

Every expanded verb shows all four tense sections by default: Past, Present, Future, and Command, including generated forms where the document omits them. Arabizi remains primary. Where a form is genuinely inapplicable or uncertain, preserve the section without inventing a verified form.

All four tense entries of every documented verb count in All Words, including generated forms that have not appeared in the document or a lesson. The user expects to learn every tense of every verb in the bank. Unpracticed entries remain Untested until qualifying scored use; counting them does not establish mastery or include them in tested-only accuracy or Words Known. This replaces the earlier document-or-lesson-exposure gate for generated tense entries. It concerns forms of existing documented verbs, not automatic admission of new lexical words.

### Verb–preposition combinations

Only include verb–preposition combinations here when the preposition substantially changes the verb's lexical meaning, as in the user's badfa3 example. Leave routine constructions such as Ba7ki ma3 (speak with) and Ba7ki 3an (speak about) out of the separate-use display and scoring; they do not create separate vocabulary uses merely by specifying a person or topic. Routine prepositions may still appear naturally in lesson sentences. For qualifying meaning-changing combinations, show the full Arabizi combination prominently, its distinct English meaning, and Arabic script secondarily. This narrows the earlier requirement to document all common prepositions here.

Use Amal's documented combinations and meanings where available. The user believes these may already be in her materials; their location and exact content have not yet been verified.

User-provided examples to locate and verify against Amal's materials (not validated translations):

- badfa3 — user gloss: I push
- badfa3 la — user gloss: I pay
- badfa3 ann — user gloss: I pay for
- Barren / Barren 3ala — no gloss supplied

Do not silently normalize these examples or present their glosses as verified teaching content before checking the source.

#### Approved display and scoring

Keep one main verb row that expands into its distinct meaning-changing uses when applicable. Only show a uses section and use count when such combinations exist. For each qualifying use, display the full Arabizi verb–preposition combination, English meaning, independent vocabulary status, and latest-10 score when available. Arabic script remains secondary.

Selecting a use reveals Amal's explanation of when to use it, an example sentence with Arabizi first, and the user's lesson clips showing correct uses and mistakes. Source and verify the teaching content; the illustrative percentages previously shown were mock data, not learner results.

Combinations with different meanings have separate vocabulary scores within the same expanded verb row, using the agreed scoring system. If the learner intends one meaning but chooses a combination that expresses another, score the failed attempt against the intended use. A correct combination with a wrong person/conjugation is a grammar error only, not a vocabulary error.

### Overall tense status across verb uses

Pool qualifying scored attempts across a tense's verb–preposition uses in chronological order to determine that tense's overall status. Apply the agreed starting/streak rules before 10 scored attempts, then use the latest 10 pooled attempts with the agreed thresholds and two-lesson mastery requirement. Keep each use's independent score visible underneath. Each occurrence enters the pooled history once; do not average the individual use statuses or duplicate an occurrence because it also updates its use-specific history. Grammar/null and ignored attempts remain excluded. The pooled tense status drives its badge and eligibility as a known word (Good or Mastered); combinations do not add extra dashboard words.

## 3. Attempts and error classification

### Applying Amal's transcript corrections

When Amal corrects transcript evidence, update the affected original attempt at its original lesson date and chronological position; do not create a new attempt dated at review time. Recalculate affected vocabulary histories, statuses, and derived metrics using the corrected evidence and the agreed scoring rules. This includes changes between ignored/null and scored outcomes, and any affected use-specific and pooled tense histories.

### Scope and attempt scoring

These scores measure spoken vocabulary only. Flashcards do not contribute.

| Attempt | Points |
|---|---:|
| Correct word recalled independently | 1 |
| Correct with a hint or self-correction | 0.5 |
| Wrong word or unable to recall | 0 |
| Immediately repeating Amal's answer | Excluded |

Vocabulary and grammar are tracked separately. Grammar-only corrections are null vocabulary attempts. Clear mixed errors are scored for vocabulary and recorded separately for grammar. Immediate echoes are excluded; later use in a new sentence can qualify.

### Current agreed correction-comparison rule

Compare the learner's attempt with Amal's correction. Apply these agreed rules:

- If the correction changes the tense of the intended verb, classify it as grammar-only: do not lower vocabulary, and do not award success to an intended tense form that was not demonstrated.
- If the tense stays the same but Amal corrects the lexical verb/form, treat it as vocabulary/form recall and apply the agreed attempt-scoring rules to that entry.
- Exception: person, gender, agreement, or attached-pronoun corrections remain grammar-only even when the tense stays the same. The user's explicit example is bahkilik versus bahkilak: the word is known, while the grammatical addressee form is wrong. This example is recorded as the user's distinction, not as an independently verified spelling lesson.
- Amal merely repeating an already-correct answer is not an error.

### Missing evidence and explicit example corrections

If information required for scoring is missing, exclude that data rather than labeling it a memory-versus-grammar ambiguity. Do not assign a score to an incomplete attempt. Preserve the source record without inventing missing words.

The user explicitly confirmed kharab → kharabet as grammar/null. The user also described a case of not remembering masculine/feminine word form as vocabulary; the precise transcript example being referenced has not yet been identified, so do not generalize that statement to all gender corrections.

For September 11 passage #1 (everything she uses stops working), the user clarified the intended meaning and explicitly classified the mistake as grammar/null. Treat that classification as resolved by the user, not independently verified from the incomplete transcript.

### Transcript gaps in Amal's after-lesson review

Include passages with missing words needed for scoring in Amal's after-lesson review so she can clarify what was said. Explicit user-confirmed examples from September 11 are passage #3, the past-tense drill at 35:40–36:21 whose learner alternatives are missing, and passage #5, the food/dish discussion at 49:31–50:40 whose missing tutor terms prevent judging the learner's answer and independence. Both are null/ignored until reviewed and sufficiently clarified.

Until clarification, mark the affected attempt Ignore: exclude it from scores, scored-attempt counts, rolling windows, streak changes, and mastery evidence. Preserve the recording/transcript context for review. Do not guess missing words or assign a wrong-answer score.

This is a transcription-evidence review, distinct from the missing-vocabulary-document workflow. The agreed 24-hour wait applies to checking whether Amal has added new vocabulary to her document; no timing for this transcript-gap review has yet been specified. If review still cannot establish what was said, keep the attempt ignored. Review-based scoring requires sufficient evidence and the agreed scoring rules.

### Grammar-only corrections are null vocabulary attempts

For the grammar-only cases above, record a null vocabulary attempt, not 0, 0.5, or 1. 

- Do not increment the scored-attempt count or advance the word toward the 10-attempt threshold.
- Do not add the attempt to, or evict an existing attempt from, the latest-10 window.
- Do not advance or break either pre-10 streak; leave vocabulary status unchanged.
- Do not count it as qualifying full-credit evidence for the two-lesson Mastered requirement.
- It does not qualify by itself as a scored spoken attempt for the 30-Day Words or 30-Day Memory cohort, or move an Untested entry to a tested status.
- Preserve the incident and its grammar correction for grammar tracking. Null in vocabulary does not erase the event.

This is a practical scoring convention, not proof of the learner's cognitive cause. If the original form or correction cannot be established from the evidence, do not pretend the comparison is certain. For mixed corrections, apply the agreed policy below.

### Mixed vocabulary and grammar errors

When an attempt contains both a clear vocabulary error and a grammar error, score the vocabulary component normally under the agreed attempt rules and record the grammar error separately. A grammar component does not make a clear vocabulary error null. Grammar-only corrections remain null for vocabulary. Missing evidence remains ignored pending review; do not infer a vocabulary error merely from a grammar correction.

## 4. Status calculation

### Before 10 scored attempts: streak rules

#### Starting from Untested

- First attempt earns 1: Good.
- First attempt earns 0 or 0.5: Shaky.
- First two attempts both earn 0: Wrong.
- First attempt earns 1 and second earns 0 or 0.5: Shaky.
- First two attempts both earn 1: stays Good, or becomes Mastered if they occurred in separate lessons.

#### Moving up

| Transition | Requirement |
|---|---|
| Wrong → Shaky | 2 consecutive full-credit attempts |
| Shaky → Good | 2 more consecutive full-credit attempts |
| Good → Mastered | 2 more consecutive full-credit attempts across 2 separate lessons |

#### Moving down

| Transition | Requirement |
|---|---|
| Mastered → Good | 1 wrong attempt |
| Good → Shaky | 2 consecutive wrong attempts |
| Shaky → Wrong | 2 more consecutive wrong attempts |

- Each level change resets the streak. The explicit starting rules above take precedence, including the first-two-attempt exceptions.
- A full-credit attempt breaks the wrong streak; a zero-point attempt breaks the correct streak.
- A half-point attempt breaks both streaks and normally leaves the level unchanged. The special second-attempt rule takes precedence.
- One wrong attempt ordinarily leaves a Good word at Good.

While Good and awaiting the two-lesson requirement, evaluate the latest two consecutive full-credit scored attempts rather than fixed pairs. Two correct attempts in one lesson followed by another correct attempt in the next lesson qualify for Mastered on that third success: the latest two successes span separate lessons. This applies before 10 attempts and preserves the agreed streak resets on level changes and exclusion of null/ignored attempts.

### From the 10th scored attempt: latest-10 rule

At the 10th scored attempt, replace the streak rules entirely with the latest-10 system.

**Word accuracy = points earned across the latest 10 scored attempts ÷ 10 × 100.**

| Accuracy | Status |
|---|---|
| 90–100% | Mastered, subject to the two-lesson requirement |
| 75–under 90% | Good |
| 50–under 75% | Shaky |
| Under 50% | Wrong |

Each new scored attempt replaces the oldest attempt in the window. Earlier streak-based promotion and demotion rules no longer apply.

Mastered requires full-credit use in two separate lessons within those latest 10 attempts. Until that requirement is met, a word scoring at least 90% remains Good.

### Two-lesson requirement

- Count lessons in which the word is actually used; intervening lessons without the word do not count against it.
- Repetition within one lesson cannot satisfy the two-lesson requirement.
- A later mistake is scored individually; it does not automatically invalidate the entire lesson.
- Before 10 attempts, the relevant full-credit uses must meet the consecutive-correct promotion rule. From 10 onward, use the rolling percentage and evidence within that window.

## 5. Dashboard metrics and accuracy

Leave summary trend arrows and their change figures out of the first version. No comparison period or trend calculation is required for this version.

When an accuracy box has no qualifying tested entries (an empty denominator), show **—** with **No practice yet**, rather than 0%. Apply this to Overall Accuracy, 30-Day Memory, and Flashcard Acc. This is an empty-data display rule, not a change to scoring.

### Overall Accuracy box

Each unique tested word contributes points based on its current status.

| Status | Points |
|---|---:|
| Mastered | 10 |
| Good | 8 |
| Shaky | 5 |
| Wrong | 0 |

**Overall Accuracy = total status points ÷ (unique tested words × 10) × 100.**

Each unique word counts once. Untested words are excluded. This is a status-weighted score, not the raw percentage of correct spoken attempts.

Example: one word in each tested status earns 23 out of 40 points, for 57.5%.

### Total Words Known box

**Total Words Known = unique words currently rated Good + unique words currently rated Mastered.**

Shaky, Wrong, and Untested words remain in the Word Bank but do not count as known. Each unique word counts once, using its current spoken-vocabulary status.

### 30-Day Memory box

Use the Overall Accuracy formula, limited to unique words with at least one scored spoken-vocabulary attempt in the last 30 days.

**30-Day Memory = total current status points for those words ÷ (number of those unique words × 10) × 100.**

Use the same status points: Mastered 10, Good 8, Shaky 5, Wrong 0. Each qualifying word counts once. This filters the words included; it does not replace their agreed status-calculation rules or truncate their latest-10 attempt histories to 30 days. Flashcards and immediate repetition after Amal do not qualify as scored spoken practice.

### 30-Day Words box

**30-Day Words = number of unique words with at least one scored spoken-vocabulary attempt in the last 30 days, regardless of status.**

Each word counts once. Flashcards and immediate repetition after Amal do not contribute. This uses the same set of words as the 30-Day Memory box.

### Flashcards Week box

**Flashcards Week = number of unique words reviewed with flashcards in the last 7 days.**

Each word counts once, regardless of how many times it was reviewed or how many card formats were used for that word. This is not a count of all completed review attempts.

### Flashcard Acc. box

Flashcards use the same scoring system as spoken vocabulary, with an independent status for each word. Flashcard results never change spoken-vocabulary status, and spoken results never change flashcard status.

- Apply the same 1 / 0.5 / 0 attempt scoring where applicable, the same starting and streak rules before 10 scored attempts, and the same latest-10 percentage thresholds from attempt 10 onward.
- Calculate Flashcard Acc. with the same status-weighted formula: total flashcard-status points divided by (unique flashcard-tested words × 10), multiplied by 100.
- Status weights remain Mastered 10, Good 8, Shaky 5, Wrong 0. Words untested in flashcards are excluded.

For flashcards, the two-separate-lessons requirement is replaced by two separate review days. Before 10 attempts, the full-credit promotion attempts must span two review days. From attempt 10 onward, Mastered requires at least 90% plus full-credit answers on two separate review days within the latest 10 scored attempts. Otherwise a score of at least 90% remains Good.

### Card / Spoken accuracy display

Show each track's independent status-based accuracy: Wrong 0%, Shaky 50%, Good 80%, Mastered 100%. Untested displays a dash, not zero. The attempt-level latest-10 calculation determines status; the displayed percentages use the status mapping.

For grouped verb and noun rows, show Card/Spoken percentages beside each tense or noun-form scoring entry inside the expanded row. Collapsed rows show the agreed status badges without a combined parent percentage. Example display: Past · Shaky — Spoken 50% · Cards 80% (illustrative, not learner data). Masculine/feminine remain one Singular scoring entry; Plural is separate.

## 6. Search, filters, and sorting

### Needs Practice tab

Show words whose current spoken-vocabulary status is Wrong or Shaky. Flashcard status does not determine inclusion in this tab. Good, Mastered, and Untested words are excluded.

Remove the Urgent badge/tag from the design. Wrong already conveys urgency; no separate urgency label or counter is needed.

### Status-filter labels

Update status-filter counts to reflect the current search and selected topics. For example, selecting Food shows the counts of matching Food entries in each status. Continue counting independently scored entries rather than parent rows.

The number beside each status filter counts matching independently scored entries, not displayed parent rows, consistent with dashboard word-count units. Two Shaky tenses within one verb contribute 2 to the Shaky count while appearing in one parent row. Singular (masculine/feminine combined) and plural likewise contribute separately when matching. Untested counts eligible entries without a scored attempt.

For rows with multiple independently scored forms, a status filter includes the parent row when any form matches and highlights the matching status badge(s). Other forms can have different statuses; they do not prevent the row from appearing. For example, Shaky includes a verb with a Shaky past form even when its present form is Mastered. Apply this consistently to verb tense and noun singular/plural scores.

Replace Needs Work with Wrong and Learning with Shaky. Keep Good and Mastered. Add a dedicated Untested filter for document words with no scored spoken-vocabulary attempts. These labels match the agreed spoken-vocabulary scale. New remains a separate recency filter, not a proficiency status.

### Search

The Word Bank search must support Arabic, English, and Arabizi in the same search field, matching Arabic vocabulary, English translations, and Arabizi transliterations.

### New (< 7 days) filter

Show words added to the Vocab document within the last 7 days, regardless of their current status. New describes when a word was added; Untested describes whether it has a scored spoken-vocabulary attempt. These are distinct properties.

### Topic column

Allow multiple topics and multiple statuses to be selected together. Match any selected topic (OR), and any selected status (OR), requiring both groups to match (AND). For example, Food or Travel + Wrong or Shaky includes entries in either selected topic with either selected status. Preserve the existing parent-row inclusion and matching-badge highlighting rules.

Allow topic filtering using Amal's Vocab-document categories alongside status filtering. Apply both conditions together: for example, Food + Shaky shows entries in Food that match Shaky, following the agreed parent-row matching and badge-highlighting rules.

Use the categories in Amal's Vocab document as the source for each word's topic.

### Default word order

Offer a separate **Partially used** lesson-usage category for grouped words where at least one scored form entry has appeared in a lesson and at least one has not. For verbs, evaluate Past/Present/Future/Command; for nouns, evaluate Singular/Plural (masculine/feminine combined). **Not used in a lesson yet** means none of those entries has a recorded lesson occurrence. Thus partially used rows have their own category rather than being treated as entirely unused. Usage follows the agreed lesson-occurrence scope (Medi or Amal), not mastery or scored-attempt status; these categories do not change scores. No additional Fully used category has been approved.

Default the Word Bank to **Most recently used in a lesson**, newest first, rather than Vocab-document order. The user explicitly clarified the lesson-only scope. Use the most recent actual Medi-spoken lesson occurrence; flashcard activity and document edits do not determine this order.

Also offer Alphabetical, Weakest first, Strongest first, Most spoken, Newest added, and Not used in a lesson yet. Alphabetical uses the primary Arabizi display; Most spoken uses the agreed lifetime Spoke count. Not used in a lesson yet selects words without any recorded lesson occurrence, unlike Untested, which means no scored spoken-vocabulary attempt. Break ties by most recently used in a lesson first, then by the primary Arabizi display alphabetically if still tied.

For parent verb rows, Weakest first uses the weakest tested tense, and Strongest first uses the strongest tested tense. For nouns, use the weaker tested score between Singular and Plural for Weakest first, and the stronger tested score for Strongest first. Untested entries do not count as weak or strong. Entirely Untested rows appear at the bottom in both strength sorts. Break ties by most recently used in a lesson first, then by the primary Arabizi display alphabetically if still tied.

## 7. Counts, recordings, and history

### Practice column: Spoke / Heard / Cards

Align Spoke, Heard, and Cards in equal-width columns, with each count above its label. Keep Last Said in a separate column with clear spacing so its lesson/time labels do not run into the practice counters.

Collapsed grouped rows show combined Spoke / Heard / Cards totals across their forms. Expanded rows show the breakdown by verb tense or noun Singular/Plural entry. Count each qualifying occurrence once in the parent total; a use-specific record and its pooled tense record do not represent two occurrences. Preserve the existing eligibility rules for each counter.

Show lifetime totals for Spoke, Heard, and Cards. Make recent activity available in the expanded history. These totals have a lifetime time range rather than the dashboard's 30-day or 7-day ranges.

Spoke counts lifetime scored spoken-vocabulary attempts (1, 0.5, or 0). Exclude grammar/null attempts, ignored or unresolved transcription gaps, and immediate repetitions after Amal. This count is not limited to the latest 10 attempts.

Heard counts qualifying exposure when Amal uses the word in a new sentence. Exclude immediate repeats; multiple repetitions of a word within the same sentence do not add extra exposures. This measures exposure, not demonstrated comprehension.

Cards counts all lifetime completed scored flashcard attempts for the word, including retries. This differs from Flashcards Week, which counts unique words reviewed in the last 7 days.

### Last Said column

Show the most recent lesson where Medi actually said the word, with the lesson number and relative time (for example, 2 days ago). Clicking opens that occurrence in the lesson. This is a lesson-occurrence reference, not the last flashcard review.

### Expanded lesson occurrence history

Include only Medi's uses as entries in the expanded lesson history. Do not list Amal's uses as separate history entries. Each recording includes Medi's whole sentence and Amal's correction when present, rather than isolating the target word. Amal's correction is context attached to Medi's occurrence, not a separate history entry. Last Said also considers only Medi’s actual speech. Amal’s speech does not update Last Said or the default recency order.

Beside each clip, show Medi's original sentence and Amal's corrected version when present, both Arabizi-first. Preserve the original attempt rather than replacing it with the correction. Do not invent a corrected version when Amal did not provide one.

Each occurrence shows its result: Correct, Partial, Wrong, Grammar/null, or Ignored pending review. These labels communicate the scoring effect: Correct 1, Partial 0.5, Wrong 0, while Grammar/null and Ignored pending review are excluded from vocabulary scoring.

Order lesson occurrences newest first. Initially show the latest five uses, with a Show all control for older occurrences.

### Expanded flashcard review history

Keep the flashcard review history beneath the lesson occurrence history. Order reviews newest first, show the latest five initially, and provide Show all for older reviews.

Each review shows its date, question direction (Arabizi → English or English → Arabizi), Medi's answer, and result.

### Pronunciation playback

Leave standalone word/form pronunciation playback out for now. Do not add AI-generated pronunciation recordings or their speaker buttons. This does not remove the previously agreed real lesson clips and occurrence history.

## 8. Removed page elements

### Export List

Remove the Export List button from the Word Bank design.

### Daily practice goal

Remove the daily practice goal from the Word Bank footer. Keep daily practice-goal information on the Flashcards & Review page instead.

### Footer indicators

Remove the remaining Word Bank footer indicators labeled in the design discussion as Review System Ready, Privacy Audio, and Edit Saved.

## 9. Research and design references

The exact statuses, thresholds, and transitions above are agreed product decisions, not a scientifically validated scoring instrument for spontaneous Palestinian Arabic speech. Research on retrieval practice and spacing informed the requirement for evidence across lessons.

- Karpicke & Bauernschmidt (2011), spaced retrieval: https://doi.org/10.1037/a0023436
- Vaughn, Dunlosky & Rawson (2016), vocabulary and successive relearning: https://pubmed.ncbi.nlm.nih.gov/27027887/
- Rawson & Dunlosky (2011), retrieval criteria and spaced relearning: https://pubmed.ncbi.nlm.nih.gov/21707204/

Research references are retained from the discussion; this consolidation is not a new literature review. The supporting vocabulary/grammar research draft and lesson audit contain historical findings and proposals, not additional approved rules. This specification takes precedence over superseded proposals and earlier ambiguity totals.

Reference project: https://stitch.withgoogle.com/projects/7225636314948596133

User-supplied screen reference: web application/stitch/projects/7225636314948596133/screens/9c6a105645d941c5a6f19ec508a8e0a2

## 10. Remaining gaps — not yet agreed

These are unresolved details identified during consolidation, not new requirements or changes to approved decisions.

| Gap | Decision needed |
|---|---|
| Noun lexical-gender recall | Identify the user's intended lexical-form example and its boundary with grammar-only agreement corrections. |
| Inapplicable forms | Define presentation/count handling for genuinely inapplicable entries; generated verb forms now have an agreed All Words eligibility rule. |
| Lesson review workflow | Design Amal's controls, transcript-review timing, and pending/resolved states with the lesson panel. |

## 11. Acceptance examples

These illustrate agreed behavior. Scoring and browser coverage is reported separately in the implementation status.

- A first independent success makes an Untested entry Good; a partial or wrong second attempt makes it Shaky.
- A first partial attempt makes an entry Shaky, not Untested.
- From attempt 10, nine points produce Mastered only with full-credit evidence across two lessons; otherwise Good. Earlier streak demotions no longer apply.
- Grammar-only corrections change no vocabulary count, score, streak, or mastery evidence and cannot alone qualify an entry for 30-day activity.
- A clear mixed error contributes a vocabulary attempt and a separate grammar record.
- Two Shaky tenses in one verb produce one row and a Shaky filter count of 2, with both matching badges highlighted.
- Masculine/feminine share a history; plural does not inherit their score.
- Flashcard success changes only the flashcard track.
- Amal's later use updates Heard only; it cannot update Last Said or move a word up the default order. A failed recall where Medi did not say the target also cannot update Last Said. Actual grammar-only speech may update Last Said without changing vocabulary scores.
- Immediate echoes do not add scored spoken attempts.
- Missing-document candidates remain pending until Amal enters them, confirms, and synchronization verifies the entries.

- Adjective collapsed headings use compact slash-separated Arabizi (Baared / Baarda), with corresponding Arabic on the line underneath.

- Adjectives show their words and Arabic once in the main heading. Expanded details retain per-form scores and history without repeating the words or masculine/feminine list.

### Context establishes lexical meaning (Kul correction)

Identical spelling is not sufficient to assign a meaning, tense, or error. Read the learner sentence and tutor exchange. Kul meaning all/every is a separate vocabulary identity from Kul, the command eat. The user confirms his loaded kul occurrences were quantifier uses. Preserve distinct source meanings; an ambiguous homograph remains unscored until context or review establishes its sense. Do not mark a vocabulary error solely because the matched dictionary entry has the wrong meaning.


## Context review rules — 2026-09-21 (supersede earlier conflicting rules)

- Wrong-word substitution corrected by the tutor: score both the actual and intended vocabulary items 0, linked to one incident. Only actual speech affects Last said.
- Repeating the supplied correction earns no additional attempt or points.
- Self-correction before tutor help: final word earns 1 with a self-corrected note. The abandoned word receives no miss. Count the episode once.
- Asking what a word means scores the unknown target 0; question words such as shu/ya3ni are not penalized. Standalone requests to repeat/clarify are unscored.
- A word used in a new answer is not helped merely because it appeared in the tutor's question. Nearby errors or hesitation cannot transfer a miss to another word.
- A confirmed incorrect pronunciation earns 0. ASR corruption alone is not evidence of an incorrect pronunciation. User-confirmed transcript repairs preserve the original ASR alongside the corrected display.
- Highlight only supported incorrect spans in red, in sentence and expanded context. Do not color an entire sentence for one word's error.
- Source-bound review overlays are in docs/data/word-bank-review.json; changed source evidence must invalidate the overlay. Ambiguous cases remain unscored with a review reason.
- Conversation excerpts are bound to original recording hashes and lesson timestamps. Display incomplete participant coverage; a successful file request is not proof that every speaker is present.

### Prepositions — user update

Treat standalone prepositions and prepositional constructions as grammar. Exclude them from vocabulary scores, accuracy, mastery and the default Word Bank list. Preserve their source history and audio in the Grammar · prepositions view. Do not exclude nouns or verbs merely because their sentence contains a preposition; yameen/right remains vocabulary. Existing flashcard records remain intact, but preposition answers do not contribute to Word Bank vocabulary metrics.
