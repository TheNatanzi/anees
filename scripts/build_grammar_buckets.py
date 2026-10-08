# -*- coding: utf-8 -*-
"""Generate docs/data/grammar-buckets.json - the grammar buckets (60 since 2026-10-02: A12, C11, C12 added) (source of truth: edit here, then run)."""
import json, os
from collections import Counter

# 2026-09-29: relative to this script's repo, so a worktree never writes into the live hourly checkout (see 278753d)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "data", "grammar-buckets.json")
b = []


def A(id, fam, name, one, ex, why, more, rule=None, taught=None):
    """taught: None (her Docs / lessons), "lesson" (Amal corrects it in lessons, scored since 2026-09-25),
    "gap" (in no Doc or lesson yet), "not-yet" (Amal 2026-09-27: not taught yet -> never scored, shown as
    "Not taught yet")."""
    row = {"id": id, "family": fam, "name": name, "one_line": one,
           "examples": ex, "why": why, "more": more, "tally_rule": rule}
    if taught:
        row["taught"] = taught
    b.append(row)


# Amal's written notes on the rules ("Mahdi's Grammar Rules notes", her Google Doc, edited 2026-09-27; Medi said
# "apply" 2026-09-29). Her words and spellings are the rule (RULES.md S1). Lines from her notes end in "(Amal)".
TAUGHT_NOTE = "Taught in lessons: the tutor corrected this %d time(s) out loud (09-24 sweep). No longer a gap rule - scored (Medi 2026-09-25)."


# ---------------- Family A - the noun phrase ----------------
A("A1", "A", "el- (the)",
  "`el-` marks a thing you already know; nothing marks a new one.",
  [["bait", "a house"], ["el-bait", "the house"], ["el-tuffaa7 zaaki", "apples are delicious (general)"],
   ["el-shita baared", "winter is cold (general)"]],
  "English has 'a' and 'the'. Arabic only has 'the' - leaving it off is how you say 'a'.",
  ["\"el\" is used for general nouns: el-tuffaa7 zaaki = apples are delicious; el-shita baared = winter is cold. (Tutor)",
   "Sun and moon letters: no need. Not a priority - do NOT mark it as an error if he doesn't use them correctly. (Tutor)",
   "So a sun/moon-letter slip (el-shams vs esh-shams) is never scored. Only el- there / not there counts."])

A("A2", "A", "idafa (possession)",
  "Thing first, owner second - and the first word never takes `el-`.",
  [["bait Medi", "Medi's house"], ["bab el-bait", "the door of the house"], ["bait u5ti", "my sister's house"]],
  "There is no word for 'of'. You just put the two nouns next to each other.",
  ["el-bait Medi is always wrong - the first noun drops el-.",
   "The LAST noun decides whether the whole phrase is definite.",
   "bait m3allem = a teacher's house.  bait el-m3allem = the teacher's house.",
   "If a noun ends with a possessive pronoun it's definite and doesn't take \"el\": bait u5ti = my sister's house; "
   "bent u5t jaarti = my neighbor's niece. (Tutor)"])

A("A3", "A", "feminine -t in idafa",
  "A feminine first word grows a `-t` before the owner.",
  [["sayyaara", "a car"], ["sayyaaret Medi", "Medi's car"]],
  "The hidden -a ending on feminine nouns wakes up as -t when something follows it.",
  ["8urfe room -> 8urfet el-noam the bedroom.",
   "madrase school -> madraset el-walad the boy's school.",
   "Only feminine nouns do this. bait Medi stays plain.",
   "Same as A2: a noun with a possessive ending is definite and takes no \"el\": bent u5t jaarti = my neighbor's niece. (Tutor)"])

A("A4", "A", "possessive endings",
  "Stick the owner on the end of the word.",
  [["ismi", "my name"], ["ismak", "your name (m)"], ["ismek", "your name (f)"], ["biddo", "he wants"],
   ["3indna", "we have"]],
  "Instead of 'my name', Arabic says 'name-my' as one word.",
  ["The set: -i my, -ak your (m), -ek your (f), -o his, -ha her, -na our, -kom your (pl), -hom their.",
   "baiti my house, baitha her house, baithom their house.",
   "Biddi and 3indi conjugate with possessive endings (they are not real verbs): biddo = he wants, 3indna = we have. (Tutor)",
   "After a vowel: -ak -> -k, -ek -> -ki, -o -> long vowel + h: kursik = your (m) chair, awa3iki = your (f) clothes, "
   "abuh = his father. (Tutor)",
   "Possessive endings also give object pronouns on verbs, except \"me\" is -ni: a3tini = give me, a3tih = give him. (Tutor)",
   "Dual -ain words: eed -> eedayy, eedaik, eedaiki, eedaikom, eedaih, eedaiha, eedaina, eedaihom. (Tutor)",
   "ijer -> ijrayy, ijraik, ijraiki, ijraikom, ijraih, ijraiha, ijraihom, ijraina. (Tutor)",
   "daan/denain -> dinayy, dinaik, dinaiki, dinaikom, dinaih, dinaiha, dinahom, dinaina. (Tutor)",
   "7awalain -> 7awalayy, 7awalaik, 7awalaiki, 7awalaikom, 7awalaih, 7awalaiha, 7awalaihom, 7awalaina. (Tutor)",
   "Not every dual works like this (no \"youmayy\"); the list grows as he learns more. (Tutor)"])

A("A5", "A", "chain possession",
  "Stack three or more nouns; only the last can take `el-`.",
  [["bab bait Medi", "the door of Medi's house"]],
  "Same rule as A2, just longer - every noun except the last stays bare.",
  ["muftaa7 bab el-bait = the key of the door of the house.",
   "You never put el- on muftaa7 or bab - only on el-bait."])

A("A6", "A", "professions",
  "Job titles are idafa too - watch where `el-` lands.",
  [["doktoar snaan", "a dentist"], ["m3allem el-3arabi", "the Arabic teacher"]],
  "A job made of two words follows A2 exactly.",
  ["doktoar snaan = a tooth-doctor, no el- anywhere = 'a dentist'.",
   "m3allem el-3arabi = the Arabic teacher - el- only on the second word."])

A("A7", "A", "noun + adjective",
  "Adjective goes AFTER. Where `el-` sits changes sentence vs phrase.",
  [["el-bait 7elu", "the house is pretty"], ["el-bait el-7elu", "the pretty house"]],
  "One el- = a full sentence. Two el- = just a name for a thing.",
  ["el-bait 7elu is a complete sentence - no word for 'is' needed (see C1).",
   "el-bait el-7elu is not a sentence, it's a label. It leaves you waiting for more.",
   "bait 7elu = a pretty house."])

A("A8", "A", "gender on adjectives",
  "Feminine noun takes a feminine adjective.",
  [["walad 7elu", "a cute boy"], ["bint 7elwa", "a cute girl"]],
  "Adjectives change shape to match the noun - usually by adding -a or -e.",
  ["akel zaaki tasty food (m), akle zaakye a tasty dish (f).",
   "If the noun ends in -a/-e it is almost always feminine."])

A("A9", "A", "plurals",
  "Some add an ending, many change shape, and two has its own form.",
  [["bait -> byoot", "house -> houses"], ["yomein", "two days"]],
  "Arabic has three plurals: regular endings, irregular reshapes, and a special 'exactly two'.",
  ["Regular: -een (people, m) and -aat (things/f) - muwazzaf -> muwazzafeen.",
   "Irregular: you memorise them - bait->byoot, bab->bwaab, shubbak->shababeek.",
   "Exactly two: add -ein - yom->yomein, saa3a->saa3tain."])

A("A10b", "A", "demonstrative keeps el-",
  "The noun after hada / hadi / hadol keeps its `el-`.",
  [["hada el-ktab", "this book"], ["hadi kilme", "this IS a word"]],
  "Keep the el- and it is a phrase. Drop it and you just made a sentence.",
  ["hada el-ktab la-Mehdi = this book is Mehdi's.",
   "hadi el-moazeh = this banana. hadi moazeh = this is a banana.",
   "Superlatives are the exception - they never take el-: hadi a2al akleh."])

A("A10", "A", "hada / hadi",
  "This-and-that words must match the gender.",
  [["hada fe3el", "this is a verb (m)"], ["hadi kilme", "this is a word (f)"]],
  "Pick the form by the gender of the thing you are pointing at.",
  ["Near: hada (m), hadi (f), hadol (plural).",
   "Far: hadaak (m), hadeek (f).",
   "Common slip: using hada for a feminine noun."], rule="R4")

A("A9b", "A", "broken plurals are patterns",
  "The irregular plurals repeat the same few shapes - learn the mould, not 200 words.",
  [["bait -> byoot", "house"], ["baab -> bwaab", "door"], ["shubbaak -> shababeek", "window"]],
  "Her Doc lists each plural as its own word, so the repeating shapes are easy to miss.",
  ["byoot / swaa2 / 3yoon all share one mould.",
   "bwaab / twaab share another.",
   "shababeek / masaajed / makaateb share a third.",
   "Not in her Docs as a lesson - this is a gap.",
   TAUGHT_NOTE % 1], taught="lesson")

A("A11", "A", "kul: all vs every",
  "`kul` + `el-` = all of it. `kul` alone = every.",
  [["kul el-yom", "all day"], ["kul yom", "every day"]],
  "One little el- flips the whole meaning.",
  ["kul el-zlaam = all the men (a specific group).",
   "kul zalame = every man (each one separately).",
   "el-kul on its own = everybody.",
   "Added 2026-10-07 (GR-30, the Oct 2 lesson): kul + noun = every; kul + el- + noun = all / the whole; el-kull = everyone (Amal 2026-10-06: 'Yes - this is the rule as I teach it')."])

# GR-30 (Medi 2026-10-07 "yes count them but wait until we add the gemini changes"; Amal 2026-10-06 "Yes - this is the rule as I
# teach it" on all six): the Oct 2 tool words, proposed as P-A13 .. P-A17 (GR-29), now scored.
A("A13", "A", "awal / oola: before or after the noun",
  "awal + noun = first; awal + el- + noun = the beginning of; after the noun: el-noun el-awal / el-oola.",
  [["awal sa3a", "the first hour"], ["awal el-sa3a", "the beginning of the hour"], ["el-saa3a el-oola", "the first hour (adjective, feminine)"]],
  "No el- in front of awal when it comes first; the el- on the noun changes the meaning to 'the beginning of'.",
  ["After the noun it is an adjective and matches the gender: el-saa3a el-oola, el-yoam el-awal.",
   "oola = the feminine of awal.",
   "Proposed from the Oct 2 lesson (GR-29); Amal 2026-10-06 'Yes - this is the rule as I teach it'; Medi 2026-10-07 'yes count them'."])
A("A14", "A", "taani: before or after the noun",
  "taani + noun = second; noun + taani = another / the second; el-noun el-taani / el-tanye; taani never takes el- in front.",
  [["taani yoam", "the second day"], ["yoam taani", "another day"], ["el-marra el-tanye", "the second time"]],
  "taani el-... means nothing: there is no 'beginning of' meaning like awal el-.",
  ["Feminine after the noun: el-marra el-tanye = the second time; marra tanye = another time.",
   "Proposed from the Oct 2 lesson (GR-29); Amal 2026-10-06 'Yes - this is the rule as I teach it'; Medi 2026-10-07 'yes count them'."])
A("A15", "A", "aa5er / a5eer: before or after the noun",
  "aa5er + noun = last; aa5er + el- + noun = the end of; after the noun the adjective a5eer / a5eera / a5eeraat.",
  [["aa5er marra", "the last time"], ["aa5er el-ijtima3", "the end of the meeting"], ["el-marra el-a5eera", "the last time (adjective)"]],
  "Before the noun it is a tool word; after the noun it is an adjective with its own form.",
  ["a5eer (m) / a5eera (f) / a5eeraat (plural): el-3ashar da2aaye2 el-a5eeraat.",
   "Proposed from the Oct 2 lesson (GR-29); Amal 2026-10-06 'Yes - this is the rule as I teach it'; Medi 2026-10-07 'yes count them'."])
A("A16", "A", "8eir: other / different, no el-",
  "8eir + noun = other / different; 8eir never takes el- in front; after the noun is rare.",
  [["8eir yoam", "another day"], ["8eir akle", "a different dish"]],
  "Only one meaning (other / different), so there is no el- version to learn.",
  ["After the noun (el-yoam el-8eir) is rare; 8eir yoam is far more common.",
   "Proposed from the Oct 2 lesson (GR-29); Amal 2026-10-06 'Yes - this is the rule as I teach it'; Medi 2026-10-07 'yes count them'."])
A("A17", "A", "nafs + el-: the same",
  "nafs + el- + noun = the same ...; never el- before nafs; nafs is never an adjective after the noun.",
  [["nafs el-ishi", "the same thing"], ["nafs el-taree2", "the same route"]],
  "The noun after nafs always has el-; el- before nafs is wrong.",
  ["nafs is only a tool word, never an adjective after the noun.",
   "Proposed from the Oct 2 lesson (GR-29); Amal 2026-10-06 'Yes - this is the rule as I teach it'; Medi 2026-10-07 'yes count them'."])

# ---------------- Family B - verbs ----------------
A("B1", "B", "present with b-",
  "Every ordinary present verb starts with b-.",
  [["ana bashrab ahwe", "I drink coffee"]],
  "The b- is the marker that says 'this is a normal present-tense verb'.",
  ["ana ba-, inta bti-, inti bti-..i, huwwe bi-, heyye bti-, i7na bni-, intu bti-..u, humme bi-..u.",
   "Drop the b- only in the cases listed in B2, B3 and B4."])

A("B2", "B", "b-drop after modals",
  "A verb followed by another verb: the second one loses its b-. Same after want/must/can words.",
  [["biddi ashrab", "I want to drink - right"], ["biddi bashrab", "wrong"], ["muhem te3raf", "it's important to know"],
   ["3ala el-a8lab niji", "we'll most likely come"]],
  "The first word already carries the tense, so the second verb goes bare.",
  ["The real rule: if a verb is followed by another verb, the second loses the b. (Tutor)",
   "Also after modal words: biddi, laazem, mumken, jaay 3abali. (Tutor)",
   "Also after a statement like it's nice / it's important / most likely: muhem te3raf = it's important to know; "
   "3ala el-a8lab niji = we'll most likely come. (Tutor)",
   "Verb + verb: ba7eb, ba2dar, baballesh, bajarreb + a bare verb.",
   "laazem aru7 I have to go - never laazem baru7.",
   "This is your single most recorded slip."], rule="R1")

A("B3", "B", "b-drop after time words",
  "No b- after lamma, ra7, ba3ed/2abel ma, la- and 3ashaan - but iza KEEPS it, and so does enno.",
  [["lamma azha2", "when I get bored - right"], ["iza bikoon 3indak", "if you have - b kept after iza"],
   ["enno bashrab", "that I drink - right"]],
  "Same logic as B2 - the linking word carries the tense.",
  ["Drop after the time words lamma, ra7, ba3ed/2abel ma, and the purpose words la- and 3ashaan. (Tutor)",
   "Iza (if) KEEPS the b. (Tutor) Keeping it after iza is never a mistake.",
   "KEEP after enno too.",
   "3ashaan aru7 so that I go, enno baru7 that I go.",
   "After kaan the b- is not scored either way - see B7. (Tutor)"], rule="R1")

A("B4", "B", "the drop carries down a chain",
  "Once dropped, it stays dropped across u / aw / wala.",
  [["biddi ashrab u akol", "I want to drink and eat"]],
  "The second and third verbs stay bare as long as the person doing them hasn't changed.",
  ["laazem aru7 u ashuf u arja3 - all three bare.",
   "A new subject ends the chain: laazem aru7 u huwwe biji - biji gets its b- back.",
   "The tutor's rule behind B2-B4: a verb followed by another verb - the second loses the b."])

A("B4b", "B", "when the b- comes back",
  "The b- returns the moment you leave the want/must clause.",
  [["ana bazonn enno ma beyhebna", "I think that he doesn't like us"]],
  "B2 and B3 take the b- away. This is the rule that puts it back.",
  ["enno starts a real new sentence, so the b- returns.",
   "A full stop restarts it too.",
   "Any clause stating a real fact rather than a wish keeps it: 3endo tilfizion ma byista5demo.",
   "Inside the gatekeeper's reach even a pointer verb stays bare."])

A("B5", "B", "past tense",
  "Endings on the back of the verb say who did it.",
  [["ana shribet", "I drank"], ["huwwe shirib", "he drank"], ["sherbat", "she drank"]],
  "No b-, no prefix - the past is all endings.",
  ["-et I, -et you (m), -ti you (f), nothing for he, -at she, -na we, -tu you (pl), -u they.",
   "The \"she\" ending is -et or -at; we're going with -at: sherbat = she drank. (Tutor) "
   "Scoring does not change: -et for she is an accent choice, not a mistake.",
   "Refer to the past-tense explanation for the patterns: middle long vowel, end vowel, short verbs, irregulars, "
   "internal flipping. (Tutor)",
   "The tutor's Doc has all 8 persons for each verb - 825 rows."])

A("B6", "B", "kaan = was / were",
  "Arabic has no 'was' in the present, but it does in the past.",
  [["kunt ta3baan", "I was tired"], ["kaan fi akel", "there was food"]],
  "C1 says you skip 'am/is/are'. In the past you must put kaan back.",
  ["ana ta3baan I am tired -> kunt ta3baan I was tired.",
   "kunt I, kaan he, kaanat she, kunna we, kaanu they."])

A("B7", "B", "kaan + verb = used to / was doing",
  "kaan + a present verb: something you used to do, or were doing (past continuous).",
  [["kunt bashte8el hon", "I used to work here"], ["kunet aqra2", "I was reading"],
   ["kaanat tetbu5", "she was cooking"]],
  "kaan plus a present verb puts it in the past: over and over back then, or going on at that moment.",
  ["Also means past continuous: kunet aqra2 = I was reading; kaanat tetbu5 = she was cooking. (Tutor)",
   "The b- after kaan: some verbs keep it, some drop it. It is NOT a rule - b- kept or dropped after kaan is never "
   "marked wrong. (Tutor)",
   "kaan bishrab ahwe kul yom he used to drink coffee every day.",
   "kaan laazem goes with this too: kaan laazem + past = should have; kaan laazem + present = should have OR had to. "
   "The tutor advises using it with the present. Scored under B16. (Tutor)",
   TAUGHT_NOTE % 1], taught="lesson")

A("B8", "B", "bakoon / ykoon",
  "No 'to be' in the plain present - but bikoon comes in for habits, for biddi/3indi in the past and future, "
  "and to mean 'probably'.",
  [["ana ta3baan", "I am tired (now)"], ["3aadatan bikoon mash8ool 3ala el-wa7de", "he's usually busy at 1:00"],
   ["kaan biddi", "I wanted"], ["bikoon m3asseb halla", "he's probably angry now"]],
  "This is the 'being' verb that appears only in certain slots.",
  ["Plain now: drop it - ana ta3baan.",
   "Habitual with usually / sometimes / every: 3aadatan bikoon mash8ool 3ala el-wa7de = he's usually busy at 1:00. (Tutor)",
   "With biddi / 3indi in the past and future it is REQUIRED: kaan biddi = I wanted; ra7 ykoon 3indi = He will have. (Tutor)",
   "With lamma / iza: lamma ykoon biddak = when you want; iza bikoon 3indak = if you have. Here it is NOT strict - "
   "leaving it out after lamma / iza is not marked wrong. (Tutor)",
   "Bikoon can also mean \"probably\": bikoon m3asseb halla = he's probably angry now; bitkoon teshte8el = she's "
   "probably working. (Tutor; her Doc's autocorrect wrote \"Bitcoin teshte8el\")",
   "To check with the tutor: she glossed ra7 ykoon 3indi as \"He will have\"; ykoon 3indi reads as \"I will have\"."], rule="R2")

A("B9", "B", "person on ykoon",
  "The ykoon form must match who you're talking about.",
  [["i7na lamma nkoon", "when we are - right"], ["i7na ykoonu", "wrong"]],
  "Easy to freeze on one form and use it for everybody.",
  ["akoon I, tkoon you, ykoon he, tkoon she, nkoon we, ykoonu they.",
   "Recorded slip: you said ykoonu ahl where it needed nkoon."], rule="R2")

A("B10", "B", "commands",
  "Telling someone to do something.",
  [["ishrab!", "drink!"], ["ruu7!", "go!"]],
  "Strip the present prefix and you're usually most of the way there.",
  ["btishrab you drink -> ishrab drink!",
   "Feminine adds -i: ishrabi. Plural adds -u: ishrabu.",
   "Refer to the explanation for all patterns: normal 3+ consonants, middle long vowel, doubled middle and short "
   "verbs, irregular ta3aal / ta3aali / ta3aalu. (Tutor)",
   "The tutor's Doc has 107 rows of these."])

A("B11", "B", "negative commands",
  "`ma` in front of the YOU-form. Never `la`.",
  [["ma tishrab", "don't drink"], ["ma tez3ejini", "don't annoy me"]],
  "You don't negate the command form - you negate the 'you do' form.",
  ["\"la\" is fus7a (MSA); spoken uses only \"ma\". (Tutor) So la + verb is a mistake.",
   "Not ma ishrab - you need ma tishrab.",
   "Feminine: ma tishrabi. Plural: ma tishrabu.",
   "The tutor drills this heavily - 202 hits across 9 of your lessons.",
   TAUGHT_NOTE % 9], taught="lesson")

A("B12", "B", "make-X vs get-X",
  "Doubling the middle letter turns 'I become' into 'I make someone'.",
  [["banbese6", "I get happy"], ["babse6ha", "I make her happy"]],
  "One is about you, the other is about what you do to somebody else.",
  ["bad7ak I laugh -> bada77ek I make people laugh.",
   "baz3al I get sad -> baza33el I make someone sad.",
   "bazha2 I get bored -> bazahhe2 I bore people.",
   "7 pairs in her Doc, plus ba3asseb."], rule="R6")

A("B13", "B", "future with ra7",
  "`ra7` plus a bare verb.",
  [["ra7 ashrab", "I'm going to drink"]],
  "ra7 does the work of 'will' / 'going to'.",
  ["The verb after ra7 drops its b- (this is a B3 case).",
   "ra7 aru7 I'll go - never ra7 baru7."])

A("B14", "B", "3am = right now",
  "`3am` plus a verb means it's happening this second.",
  [["3am bashrab", "I'm drinking right now"]],
  "English uses -ing for both habits and right-now. Arabic splits them.",
  ["bashrab ahwe = I drink coffee (generally).",
   "3am bashrab ahwe = I'm drinking coffee right now.",
   "The tutor has said this only 3 times in your recorded lessons.",
   "Not taught yet: part of the future present-progressive lesson. (Tutor) Not scored until she teaches it - "
   "corrections stay visible but do not count."], taught="not-yet")

A("B15", "B", "participles",
  "State words that act like adjectives.",
  [["ana raaye7", "I'm on my way"], ["ana naasi", "I've forgotten"]],
  "Not really a verb - it describes the state you're in.",
  ["raaye7 going, naasi having forgotten, 3aaref knowing, saaken living.",
   "They take gender: raaye7 (m) / raay7a (f).",
   "Only 1 hit in all your lessons - this is your thinnest bucket.",
   "Not taught yet: also part of the present-progressive lesson. (Tutor) Not scored until she teaches it - her "
   "corrections so far stay visible but do not count (it was scored 2026-09-25 to 2026-09-29)."], taught="not-yet")

A("B16", "B", "kan laazem",
  "`kaan` stacked on `laazem` = had to / should have.",
  [["kaan laazem ashte8el", "I had to work"], ["ma kaan laazem", "I shouldn't have"]],
  "B6 kaan plus B2 laazem, together - and the b- still drops.",
  ["kaan laazem aru7 I had to go - never kaan laazem baru7.",
   "kaan laazem + past = should have; kaan laazem + present = should have OR had to. The tutor advises using it with the "
   "present. (Tutor, under B7)",
   "Negative flips the meaning to regret: ma kaan laazem a7ki I shouldn't have spoken.",
   "The tutor corrected you on this live on Aug 25."])

A("B17", "B", "sarli",
  "'It's been X for me' - duration up to now.",
  [["sarli saa3a hon", "I've been here an hour"], ["2adaish sarlak?", "how long have you been...?"]],
  "Takes the PERSON ending, not a separate subject word.",
  ["sarli me, sarlak you (m), sarlek you (f), sarlo him, sarlha her.",
   "It's preferred and more natural to put the duration right after sarli. (Tutor)",
   "sarli sitt shhoor bat3allam 3arabi - I've been learning Arabic for six months.",
   "Fixed 2026-09-29: the old second example (min saarlha?) was wrong - it is 2adaish sarlak. (Tutor)"])

A("B18", "B", "verb matches its subject",
  "The verb's person, gender and number must match who or what is doing it.",
  [["el-sharika illi betbi3o bet8asselo", "the company that sells it washes it (sharika is feminine -> bet-)"],
   ["shu bey7ammsek?", "what excites you? (one thing -> singular verb)"], ["huwwe byenbese6", "he gets happy (he -> bye-)"]],
  "English verbs barely change ('I/you/they sell'). Arabic verbs change for every person: a feminine noun takes "
  "the she-form, a plural takes -u, 'I' takes a-/ba-.",
  ["Present tense: the prefix/ending must be the right person - bey3asseb-ni (it annoys me), not ba3asseb-ni; "
   "testa3mel (she uses), not testa3meli.",
   "A noun subject decides the form: the cup enkasarat (feminine), meetings bey-zah2u-ni (plural).",
   "Past-tense endings for ana/inta/hiyye stay in B5; adjectives stay in A8.",
   "Found 26 times in the 2026-09-24 sweep of all 13 lessons. Added by Medi 2026-09-25."])

# GR-18 proposals Medi approved 2026-10-02 ("yes yes all yes"): A12, C11, C12 (data/lesson-work/full-audit/proposed-buckets.json)
A("A12", "A", "pronoun matches who you mean",
  "Pick the pronoun for the real person: humma for 'they', heyye for 'she'.",
  [["humma ma byi5alsu", "they don't finish (his family -> humma, not huwwe)"], ["heyye", "she (his fiancee -> heyye, not inti)"]],
  "In a long sentence the pronoun drifts to the last one used.",
  ["Proposed by the 09-24 sweep (NEW-A12) from 08-25 22:13 and 31:59; approved by Medi 2026-10-02 (GR-18).",
   "A verb ending that does not match its subject stays in B18; this rule is the pronoun word itself."])

# ---------------- Family C - sentence glue ----------------
A("C1", "C", "no word for 'to be'",
  "Arabic drops am / is / are in the plain present.",
  [["ana ta3baan", "I am tired"], ["el-bait 7elu", "the house is pretty"]],
  "You just put the two parts side by side. Nothing goes between them.",
  ["huwwe doktoar - he is a doctor.",
   "Put kaan back for the past (B6) and ykoon after lamma/iza (B8)."])

A("C2", "C", "the pointer rule",
  "Move the object to the front and the verb grows an ending pointing back.",
  [["aktar eshi basawwih", "the thing I do most"]],
  "The -h on the end is the 'it' you already mentioned at the front.",
  ["el-akel illi taba5to - the food that I cooked; -o points back to the food.",
   "Endings: -o him/it, -ha her/it (f), -hom them.",
   "Forgetting the ending is one of your recorded slips."], rule="R5")

A("C3", "C", "comparatives",
  "`a7san`, `aktar`, `a2al` - and never `el-` in front.",
  [["a7san 6ari2a", "the best way"], ["aktar min heik", "more than that"]],
  "The same word covers 'better' and 'best'. Context tells you which.",
  ["a7san better/best, aktar more/most, a2al less/least, aswa2 worse/worst.",
   "Never el-a7san - that's the recorded slip."], rule="R3")

A("C4", "C", "saying no",
  "`ma` before verbs, `mish` before nouns and adjectives.",
  [["ma bashrab", "I don't drink"], ["mish ta3baan", "not tired"]],
  "Two different 'not' words, picked by what comes after.",
  ["Verb -> ma: ma baru7 I don't go.",
   "Adjective or noun -> mish: mish zaaki not tasty.",
   "Never: abadan ma baru7 I never go.",
   TAUGHT_NOTE % 6], taught="lesson")

A("C4b", "C", "words that drag a ma along",
  "`abadan` is not enough on its own - the verb still needs `ma`. And after `abel` it is always `abel ma` + a bare present verb.",
  [["ana abadan ma baru7", "I never go"], ["abel ma aaji", "before I came"]],
  "Two different -ma's that pull opposite ways on the b-.",
  ["abadan ma baru7 - keeps the b-, because abadan is real negation.",
   "After abel it's always ma + the present verb with no b-, even when the English is past: abel ma aaji = before I came. (Tutor)",
   "abel ma yiju (before they come) - that -ma is part of the conjunction, not negation.",
   "ba3ed-ma teshra7i (after you explain) - same, and the b- drops.",
   "Other words / prepositions take ma as well; the tutor will explain them later. (Tutor)"])

A("C5", "C", "u / aw / willa / wala",
  "and, or, or, nor/nothing.",
  [["ahwe u shay", "coffee and tea"], ["ahwe willa shay?", "coffee or tea?"], ["wala shi", "nothing"],
   ["wala ana", "neither do I"]],
  "Small joining words that don't overlap the way English 'or' does.",
  ["u = and.  aw = or.  willa = another way to say or. (Tutor)  wala = nor / not even / none.",
   "wala 7ada nobody, wala ishi nothing, wala ana neither do I. (Tutor)",
   "The recorded slip is aw vs willa, not aw vs wala. (Tutor)"], rule="R8")

A("C6", "C", "iza / lamma",
  "if, when - conditional words. lamma drops the b- on the next verb, iza keeps it.",
  [["iza bteji, bansu6", "if you come, I'm happy"], ["iza bikoon 3indak", "if you have"],
   ["lamma ykoon biddak", "when you want"]],
  "lamma drops the b- (B3); iza keeps it. Both bring in bikoon before an adjective or biddi / 3indi (B8).",
  ["lamma = when (it will happen).  iza = if (it might).",
   "These are conditional words: they need bikoon before the adjective, or before biddi and 3indi, in their sentence. (Tutor)",
   "lamma drops the present marker b-; iza does not. (Tutor) lamma aru7 when I go - bare verb.",
   "Iza (if) KEEPS the b (Tutor): iza bteji, never iza teji.",
   "Scoring: under B8 the tutor wrote that bikoon after lamma / iza is not strict, so leaving it out is not counted "
   "(asked Medi 2026-09-30, since this note says 'require')."])

A("C7", "C", "illi",
  "'the one that' - never changes shape. No el-, no illi.",
  [["el-bait illi ishtareto", "the house that I bought"], ["seyyarti illi basoo2ha", "my car that I drive"],
   ["aktar ishi ba7ebbo", "the thing I like the most"], ["fi u8niyye ba3rafha", "there is a song that I know"]],
  "One word covers that / which / who, for everything - but only after a definite word.",
  ["No el, no illi: if the word before illi is not definite (no el- and no possessive ending), don't add illi. (Tutor)",
   "aktar ishi ba7ebbo = the thing I like the most; seyyarti illi basoo2ha = my car that I drive; "
   "fi u8niyye ba3rafha = there is a song that I know. (Tutor)",
   "It never changes for gender or number.",
   "The clause after it usually needs the C2 pointer ending - ishtareto not ishtarait."])

A("C8", "C", "question words",
  "The basic set.",
  [["wein raaye7?", "where are you going?"], ["shu hada?", "what's this?"], ["kam dars?", "how many lessons?"]],
  "Arabic doesn't need a 'do' helper - the question word just goes first.",
  ["shu what, wein where, keef how, 2adaish how much, kam how many, lesh why, meen who, aymta when.",
   "Addaish and kam both mean how much / how many; they're used differently and build the sentence differently. (Tutor)",
   "kam always takes the singular: kam dars = how many lessons. (Tutor) See E5.",
   "kam also means few: 3indi kam ishi = I have a few things. (Tutor)"])

A("C9", "C", "word order",
  "Normal is verb then object; front the object and C2 kicks in.",
  [["basawwi el-akel", "I make the food"], ["el-akel basawwih", "the food, I make it"]],
  "Moving something to the front is allowed - but then you owe a pointer ending.",
  ["Plain: verb, then what it acts on.",
   "Fronted: the thing first, then the verb WITH its ending.",
   TAUGHT_NOTE % 2], taught="lesson")

A("C10", "C", "preposition goes in front",
  "English leaves it dangling; Arabic never does.",
  [["min wein ishtareto?", "where did you buy it from?"], ["ma3 meen?", "with who?"]],
  "The preposition fuses to the question word and leads the sentence.",
  ["min wein from where, lawein to where, 3an shu about what.",
   "ma3 meen with who, min emta since when, min shu from what.",
   "The tutor taught this out loud on Sep 16: lawein - we add it to the question, always."])

A("C11", "C", "noun, not verb, after a preposition",
  "After bi / fi / min use the noun of the action, not a verb.",
  [["ana ma3roof bi el-tabe5 el-kabab", "I'm known for cooking kebab (bi + el-tabe5, not bi + a6bo5)"]],
  "English uses '-ing' after 'for/at'. Arabic uses the action's noun: tabe5 = cooking.",
  ["Amal 09-21 38:15: 'the noun. Noun is طبخ' (her chat: ana ma3roof bi el-tabe5 el-kabab).",
   "Proposed by the 09-24 sweep (NEW-C11); approved by Medi 2026-10-02 (GR-18). Which preposition a word takes stays in D2."])

A("C12", "C", "a doing verb says what was done",
  "A verb like 3amal (do / make) names what was done.",
  [["3amalna tamreen kteer", "we did a lot of exercise (not just 3amalna kteer)"]],
  "English 'we did a lot' is fine; the tutor kept asking 'shu 3amalna?' until the thing done was named.",
  ["08-25 59:04: he said 3amalna kteer, the tutor asked shu 3amalna? twice, he said 3amalna tamreen kteer.",
   "Proposed 2026-10-02 from a row once rejected as 'no bucket fits' (FA-0075); approved by Medi 2026-10-02 (GR-18)."])

# ---------------- Family D - partners ----------------
A("D1", "D", "prepositions",
  "Small words with several jobs each.",
  [["min el-bait", "from the house"], ["3ala el-6aawle", "on the table"]],
  "Each one covers 2-4 English prepositions, so you learn them by use, not translation.",
  ["min from, 3ala on/about, fi in, ma3 with, bi by/with, la to/for.",
   "3ala alone covers on, about, against and owing.",
   "For the fuller explanation, see the tutor's Doc \"Arabic Materials\". (Tutor)"])

A("D2", "D", "verb + its fixed preposition",
  "The verb chooses it. You can't guess from English.",
  [["a6lub minhom", "I ask them"], ["5aayef min", "scared of"]],
  "Learn the verb and its preposition as one unit.",
  ["ba6lub min - ask FROM (not 'to').",
   "5aayef min - scared FROM (not 'of').",
   "mishtaa2 la missing TO, 2al2aan 3ala worried ON, mu5talef 3an different FROM.",
   "Zero hits in your lessons - nobody has drilled this set."], rule="R7")

A("D5", "D", "preposition keeps el-",
  "Where English drops 'the', Levantine keeps it.",
  [["min el-bait", "from home"], ["bi-lseyyara", "by car"]],
  "English says 'from home' and 'by car' with no 'the'. Arabic puts it back.",
  ["bi / la / fi fuse with it: bi-l..., la-l..., fi-l...",
   "min / 3ala / ma3 keep it separate: min el-bait, 3ala el-6aawle.",
   "No el- on a name (la-Mehdi, fi America), on something already owned (ma3i, ma3 sadiqi), or when it really is indefinite (ma3 3aseer)."])

A("D3", "D", "endings on prepositions",
  "Stick the person on the end of the preposition. All take endings except bi.",
  [["ma3i", "with me"], ["minnak", "from you"], ["ili", "to me / mine"], ["fiyy", "in me"]],
  "Same idea as A4, but on prepositions instead of nouns.",
  ["All prepositions take endings except \"bi\". (Tutor)",
   "ma3i with me, ma3ak with you, ma3o with him.",
   "minni from me, minnak from you, minno from him.",
   "Some double their letter: min -> minno, not mino.",
   "la- has its own endings: ili, ilak, ilek, ilkom, ilo, ilha, ilhom, ilna. (Tutor)",
   "fi is like the others with small changes: fiyy, fik, fiki, fikom, fiyyo, fiha, fihom, fina. (Tutor)"])

A("D4", "D", "endings on verbs",
  "The object rides on the back of the verb.",
  [["shufo", "see him"], ["bi7kilak", "he tells you"]],
  "A different set from D3 - these attach straight to the verb.",
  ["shufo see him, shufha see her, shufhom see them.",
   "bi7kili he tells me, bi7kilak he tells you.",
   "Feeds the C2 pointer rule."])

A("D6", "D", "iyyaa - the second object",
  "A verb carries only one pronoun; a second one rides on `iyyaa`.",
  [["ba36ii-k iyyaa", "I give it to you"], ["jeeb-li iyyaa", "bring it to me"]],
  "You cannot stack two object endings on one verb, so the second gets its own word.",
  ["ba36ii-k = I give you. ba36ii-k iyyaa = I give it to you.",
   "jeeb-li = bring me. jeeb-li iyyaa = bring it to me.",
   "Absent from both her Docs - confirmed against the live Doc 2026-09-22."], taught="gap")

# ---------------- Family E - numbers and time ----------------
A("E1", "E", "number + noun",
  "2 has its own form; 3-10 take a plural; 11+ take a SINGULAR.",
  [["yomein", "2 days"], ["talat iyyaam", "3 days"], ["5ames da2aaye2", "5 minutes"], ["7da3sh yom", "11 day"]],
  "The rule flips twice as the number gets bigger - this is the part English never prepares you for.",
  ["Exactly 2: no number word, just the -ein ending - yomein, saa3tain.",
   "3 to 10: the number without its -e / -a ending + the plural noun: 5ames da2aaye2 = 5 minutes. (Tutor)",
   "talat iyyaam, 5ams saa3aat.",
   "11 and up: number + SINGULAR noun - 7da3sh yom, 3ishreen saa3a.",
   TAUGHT_NOTE % 3], taught="lesson")

A("E2", "E", "clock time",
  "`el-saa3a` + the feminine number.",
  [["el-saa3a tlaate u noss", "3:30"], ["talaat u tult", "3:20"], ["el-saa3a talaat illa rube3", "2:45"]],
  "You say 'the hour three and a half', not 'three thirty'.",
  ["u noss and a half, u rube3 and a quarter, u tult twenty past, illa rube3 quarter to.",
   "tult = the twenty-minute mark: talaat u tult = 3:20. (Tutor)",
   "illa also means except. (Tutor)",
   "u talateen and thirty, for exact minutes."])

A("E3", "E", "time units, two-of and many-of",
  "Each unit has three forms.",
  [["d2ee2a / d2ee2tain / d2aaye2", "minute / two minutes / minutes"]],
  "One, exactly two, and many - the middle one is the A9 dual.",
  ["saa3a / saa3tain / saa3aat - hour.",
   "yom / yomein / iyyaam - day.",
   "shahr / shahrein / shhoor - month."])

A("E4", "E", "calendar",
  "Days, months, and 'on Monday'.",
  [["yom el-itnein", "Monday"], ["el-jum3a", "Friday"]],
  "Days are just 'day the-second', 'day the-third' and so on.",
  ["el-itnein Monday (day 2), el-talaata Tuesday, el-arb3a Wednesday.",
   "el-jum3a Friday, el-sabet Saturday, el-a7ad Sunday."])

A("E5", "E", "kam + singular",
  "After `kam` (how many) the noun is always singular - never plural.",
  [["kam soora?", "how many pictures?"], ["kam yoam?", "how many days?"], ["kam dars?", "how many lessons?"],
   ["3indi kam ishi", "I have a few things"]],
  "English asks 'how many' with a plural noun. Levantine keeps the noun singular after kam, even though the answer is many.",
  ["kam soora sawwarti? = how many pictures did you take? (not kam suwar)",
   "The answer then follows E1: talat suwar (3-10 plural), 12 soora (11+ singular).",
   "kam also means few: 3indi kam ishi = I have a few things. (Tutor)",
   "Added by Medi 2026-09-24."])

# ---------------- Family F - sound ----------------
A("F1", "F", "the seven hard letters",
  "Sounds English doesn't have - scored as pronunciation, not grammar.",
  [["ne6la3", "we go out - not 'nitla'"]],
  "Dropping them makes a different word, or no word at all.",
  ["2 = hamza glottal stop, 3 = ayn, 7 = ha, 5 = kha, 6 = ta, 8 = ghayn, 9 = sad.",
   "Your recorded slips are mostly ayn, ta and ghayn."], rule="R9")

A("F2", "F", "vowel length",
  "Holding a vowel longer changes the word.",
  [["saam / sam", "fasted / poison"]],
  "Arabic treats a long vowel and a short one as two different letters.",
  ["Written Arabic doesn't mark short vowels, so this can only be judged by ear.",
   "In Arabizi a doubled letter means hold it: saam vs sam."])

A("F3", "F", "causative verbs: 3 forms",
  "One root, two sides - doing it to someone vs it happening to you - made 3 ways: doubled middle, n-, or t-.",
  [["ba3allem / bat3allam", "I teach / I learn"], ["baz3ej / banze3ej", "I annoy / I get annoyed"],
   ["ba8ayyer / bat8ayyar", "I change (something) / I change"]],
  "Tutor: this card explains causative verbs instead of shadda. The doubled middle letter is one of the three forms.",
  ["Doubled middle, then t- for the 'it happens to me' side: ba3allem teach -> bat3allam learn; "
   "ba8ayyer change -> bat8ayyar be changed. (Tutor)",
   "n- for the 'it happens to me' side: baz3ej annoy -> banze3ej be annoyed. (Tutor)",
   "Replaces the old shadda card (Amal 2026-09-30). make-X / get-X slips are scored under B12; this card is "
   "still not scored on its own (family F)."])

payload = {
    "updated": "2026-10-02",
    "source": "wiki/18-grammar-buckets.md + Medi additions B16/B17/C10 (2026-09-22) + Amal's written notes (2026-09-27, applied 2026-09-29; her 2026-09-30 notes C4b-F3 applied 2026-09-30) + Medi-approved GR-18 proposals A12/C11/C12 (2026-10-02)",
    "families": {"A": "The noun phrase", "B": "The verb system", "C": "Sentence glue",
                 "D": "Words that pick their partner", "E": "Numbers and time",
                 "F": "Sound shape (pronunciation, not grammar)"},
    "count": len(b),
    "buckets": b,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)

print("wrote", len(b), "buckets ->", OUT)
print(Counter(x["family"] for x in b))
print("mapped to a tally rule:", sum(1 for x in b if x["tally_rule"]))
