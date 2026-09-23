# -*- coding: utf-8 -*-
"""Generate docs/data/grammar-buckets.json - the 49 grammar buckets."""
import json, os
from collections import Counter

OUT = r"C:\dev\anees-hourly\docs\data\grammar-buckets.json"
b = []


def A(id, fam, name, one, ex, why, more, rule=None):
    b.append({"id": id, "family": fam, "name": name, "one_line": one,
              "examples": ex, "why": why, "more": more, "tally_rule": rule})


# ---------------- Family A - the noun phrase ----------------
A("A1", "A", "el- (the)",
  "`el-` marks a thing you already know; nothing marks a new one.",
  [["bait", "a house"], ["el-bait", "the house"], ["el-shams -> esh-shams", "the sun (sun letters)"]],
  "English has 'a' and 'the'. Arabic only has 'the' - leaving it off is how you say 'a'.",
  ["The sun-letter half: before s, sh, t, d, r, n, z, l the l disappears and the next letter doubles.",
   "el-shams is written with an l but said esh-shams.",
   "el-dar -> ed-dar.  el-nas -> en-nas.  el-rajol -> er-rajol.",
   "Moon letters keep the l: el-bait, el-kalb, el-walad."])

A("A2", "A", "idafa (possession)",
  "Thing first, owner second - and the first word never takes `el-`.",
  [["bait Medi", "Medi's house"], ["bab el-bait", "the door of the house"]],
  "There is no word for 'of'. You just put the two nouns next to each other.",
  ["el-bait Medi is always wrong - the first noun drops el-.",
   "The LAST noun decides whether the whole phrase is definite.",
   "bait m3allem = a teacher's house.  bait el-m3allem = the teacher's house."])

A("A3", "A", "feminine -t in idafa",
  "A feminine first word grows a `-t` before the owner.",
  [["sayyaara", "a car"], ["sayyaaret Medi", "Medi's car"]],
  "The hidden -a ending on feminine nouns wakes up as -t when something follows it.",
  ["8urfe room -> 8urfet el-noam the bedroom.",
   "madrase school -> madraset el-walad the boy's school.",
   "Only feminine nouns do this. bait Medi stays plain."])

A("A4", "A", "possessive endings",
  "Stick the owner on the end of the word.",
  [["ismi", "my name"], ["ismak", "your name (m)"], ["ismek", "your name (f)"]],
  "Instead of 'my name', Arabic says 'name-my' as one word.",
  ["The set: -i my, -ak your (m), -ek your (f), -o his, -ha her, -na our, -kom your (pl), -hom their.",
   "baiti my house, baitha her house, baithom their house."])

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

A("A10", "A", "hada / hadi",
  "This-and-that words must match the gender.",
  [["hada fe3el", "this is a verb (m)"], ["hadi kilme", "this is a word (f)"]],
  "Pick the form by the gender of the thing you are pointing at.",
  ["Near: hada (m), hadi (f), hadol (plural).",
   "Far: hadaak (m), hadeek (f).",
   "Common slip: using hada for a feminine noun."], rule="R4")

A("A11", "A", "kul: all vs every",
  "`kul` + `el-` = all of it. `kul` alone = every.",
  [["kul el-yom", "all day"], ["kul yom", "every day"]],
  "One little el- flips the whole meaning.",
  ["kul el-zlaam = all the men (a specific group).",
   "kul zalame = every man (each one separately).",
   "el-kul on its own = everybody."])

# ---------------- Family B - verbs ----------------
A("B1", "B", "present with b-",
  "Every ordinary present verb starts with b-.",
  [["ana bashrab ahwe", "I drink coffee"]],
  "The b- is the marker that says 'this is a normal present-tense verb'.",
  ["ana ba-, inta bti-, inti bti-..i, huwwe bi-, heyye bti-, i7na bni-, intu bti-..u, humme bi-..u.",
   "Drop the b- only in the cases listed in B2, B3 and B4."])

A("B2", "B", "b-drop after modals",
  "No b- after want/must/can words.",
  [["biddi ashrab", "I want to drink - right"], ["biddi bashrab", "wrong"]],
  "The first word already carries the tense, so the second verb goes bare.",
  ["Trigger words: biddi, laazem, mumkin, ba7eb, ba2dar, baballesh, bajarreb.",
   "laazem aru7 I have to go - never laazem baru7.",
   "This is your single most recorded slip."], rule="R1")

A("B3", "B", "b-drop after time words",
  "No b- after lamma, iza, ra7, 3ashaan - but KEEP it after enno.",
  [["lamma azha2", "when I get bored - right"], ["enno bashrab", "that I drink - right"]],
  "Same logic as B2 - the linking word carries the tense.",
  ["Drop after: lamma, iza, abel-ma, ba3ed-ma, ra7, la-, 3ashaan.",
   "KEEP after enno - this is the one exception that catches people.",
   "3ashaan aru7 so that I go, enno baru7 that I go."], rule="R1")

A("B4", "B", "the drop carries down a chain",
  "Once dropped, it stays dropped across u / aw / wala.",
  [["biddi ashrab u akol", "I want to drink and eat"]],
  "The second and third verbs stay bare as long as the person doing them hasn't changed.",
  ["laazem aru7 u ashuf u arja3 - all three bare.",
   "A new subject ends the chain: laazem aru7 u huwwe biji - biji gets its b- back."])

A("B5", "B", "past tense",
  "Endings on the back of the verb say who did it.",
  [["ana shribet", "I drank"], ["huwwe shirib", "he drank"]],
  "No b-, no prefix - the past is all endings.",
  ["-et I, -et you (m), -ti you (f), nothing for he, -et she, -na we, -tu you (pl), -u they.",
   "Amal's Doc has all 8 persons for each verb - 825 rows."])

A("B6", "B", "kaan = was / were",
  "Arabic has no 'was' in the present, but it does in the past.",
  [["kunt ta3baan", "I was tired"], ["kaan fi akel", "there was food"]],
  "C1 says you skip 'am/is/are'. In the past you must put kaan back.",
  ["ana ta3baan I am tired -> kunt ta3baan I was tired.",
   "kunt I, kaan he, kaanat she, kunna we, kaanu they."])

A("B7", "B", "kaan + b-verb = used to",
  "Habitual past - something you did regularly.",
  [["kunt bashte8el hon", "I used to work here"]],
  "kaan plus a normal b-verb means it happened over and over back then.",
  ["Note the b- STAYS here - this is not a drop case.",
   "kaan bishrab ahwe kul yom he used to drink coffee every day."])

A("B8", "B", "bakoon / ykoon",
  "No 'to be' in the plain present, but you need it after lamma/iza and for habits.",
  [["ana ta3baan", "I am tired (now)"], ["lamma akoon ta3baan", "when I'm tired"]],
  "This is the 'being' verb that appears only in certain slots.",
  ["Plain now: drop it - ana ta3baan.",
   "After lamma / iza: you must use it - lamma akoon, iza bikoon.",
   "For habits and the future: bakoon ta3baan ba3ed el-shu8el."], rule="R2")

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
   "Amal's Doc has 107 rows of these."])

A("B11", "B", "negative commands",
  "`ma` or `la` in front of the YOU-form.",
  [["ma tishrab", "don't drink"], ["ma tez3ejini", "don't annoy me"]],
  "You don't negate the command form - you negate the 'you do' form.",
  ["Not ma ishrab - you need ma tishrab.",
   "Feminine: ma tishrabi. Plural: ma tishrabu.",
   "Amal drills this heavily - 202 hits across 9 of your lessons."])

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
   "Amal has said this only 3 times in your recorded lessons."])

A("B15", "B", "participles",
  "State words that act like adjectives.",
  [["ana raaye7", "I'm on my way"], ["ana naasi", "I've forgotten"]],
  "Not really a verb - it describes the state you're in.",
  ["raaye7 going, naasi having forgotten, 3aaref knowing, saaken living.",
   "They take gender: raaye7 (m) / raay7a (f).",
   "Only 1 hit in all your lessons - this is your thinnest bucket."])

A("B16", "B", "kan laazem",
  "`kaan` stacked on `laazem` = had to / should have.",
  [["kaan laazem ashte8el", "I had to work"], ["ma kaan laazem", "I shouldn't have"]],
  "B6 kaan plus B2 laazem, together - and the b- still drops.",
  ["kaan laazem aru7 I had to go - never kaan laazem baru7.",
   "Negative flips the meaning to regret: ma kaan laazem a7ki I shouldn't have spoken.",
   "Amal corrected you on this live on Aug 25."])

A("B17", "B", "saarli",
  "'It's been X for me' - duration up to now.",
  [["saarli saa3a hon", "I've been here an hour"], ["min saarlha?", "how long has it been?"]],
  "Takes the PERSON ending, not a separate subject word.",
  ["saarli me, saarlak you (m), saarlek you (f), saarlo him, saarlha her.",
   "saarli sitt shhoor bat3allam 3arabi - I've been learning Arabic for six months.",
   "From your Sep 21 lesson: min saarlha inta akaltha?"])

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
   "Never: abadan ma baru7 I never go."])

A("C5", "C", "u / aw / wala",
  "and, either-or, nor/nothing.",
  [["ahwe u shay", "coffee and tea"], ["wala shi", "nothing"]],
  "Three small joining words that don't overlap the way English 'or' does.",
  ["u = and.  aw = or (a real choice).  wala = nor / not even / none.",
   "wala 7ada nobody, wala ishi nothing.",
   "Mixing up aw and wala is a recorded slip."], rule="R8")

A("C6", "C", "iza / lamma",
  "if, when - and both change the verb after them.",
  [["iza bteji, bansu6", "if you come, I'm happy"]],
  "They trigger the b-drop (B3) and often need ykoon (B8).",
  ["lamma = when (it will happen).  iza = if (it might).",
   "lamma aru7 when I go - bare verb.",
   "lamma akoon ta3baan when I'm tired - needs ykoon."])

A("C7", "C", "illi",
  "'the one that' - never changes shape.",
  [["el-bait illi ishtareto", "the house that I bought"]],
  "One word covers that / which / who, for everything.",
  ["It never changes for gender or number.",
   "The clause after it usually needs the C2 pointer ending - ishtareto not ishtarait."])

A("C8", "C", "question words",
  "The basic set.",
  [["wein raaye7?", "where are you going?"], ["shu hada?", "what's this?"]],
  "Arabic doesn't need a 'do' helper - the question word just goes first.",
  ["shu what, wein where, keef how, 2addesh how much, kam how many, lesh why, meen who, aymta when."])

A("C9", "C", "word order",
  "Normal is verb then object; front the object and C2 kicks in.",
  [["basawwi el-akel", "I make the food"], ["el-akel basawwih", "the food, I make it"]],
  "Moving something to the front is allowed - but then you owe a pointer ending.",
  ["Plain: verb, then what it acts on.",
   "Fronted: the thing first, then the verb WITH its ending."])

A("C10", "C", "preposition goes in front",
  "English leaves it dangling; Arabic never does.",
  [["min wein ishtareto?", "where did you buy it from?"], ["ma3 meen?", "with who?"]],
  "The preposition fuses to the question word and leads the sentence.",
  ["min wein from where, lawein to where, 3an shu about what.",
   "ma3 meen with who, min emta since when, min shu from what.",
   "Amal taught this out loud on Sep 16: lawein - we add it to the question, always."])

# ---------------- Family D - partners ----------------
A("D1", "D", "prepositions",
  "Small words with several jobs each.",
  [["min el-bait", "from the house"], ["3ala el-6aawle", "on the table"]],
  "Each one covers 2-4 English prepositions, so you learn them by use, not translation.",
  ["min from, 3ala on/about, fi in, ma3 with, bi by/with, la to/for.",
   "3ala alone covers on, about, against and owing."])

A("D2", "D", "verb + its fixed preposition",
  "The verb chooses it. You can't guess from English.",
  [["a6lub minhom", "I ask them"], ["5aayef min", "scared of"]],
  "Learn the verb and its preposition as one unit.",
  ["ba6lub min - ask FROM (not 'to').",
   "5aayef min - scared FROM (not 'of').",
   "mishtaa2 la missing TO, 2al2aan 3ala worried ON, mu5talef 3an different FROM.",
   "Zero hits in your lessons - nobody has drilled this set."], rule="R7")

A("D3", "D", "endings on prepositions",
  "Stick the person on the end of the preposition.",
  [["ma3i", "with me"], ["minnak", "from you"]],
  "Same idea as A4, but on prepositions instead of nouns.",
  ["ma3i with me, ma3ak with you, ma3o with him.",
   "minni from me, minnak from you, minno from him.",
   "Some double their letter: min -> minno, not mino."])

A("D4", "D", "endings on verbs",
  "The object rides on the back of the verb.",
  [["shufo", "see him"], ["bi7kilak", "he tells you"]],
  "A different set from D3 - these attach straight to the verb.",
  ["shufo see him, shufha see her, shufhom see them.",
   "bi7kili he tells me, bi7kilak he tells you.",
   "Feeds the C2 pointer rule."])

# ---------------- Family E - numbers and time ----------------
A("E1", "E", "number + noun",
  "2 has its own form; 3-10 take a plural; 11+ take a SINGULAR.",
  [["yomein", "2 days"], ["talat iyyaam", "3 days"], ["7da3sh yom", "11 day"]],
  "The rule flips twice as the number gets bigger - this is the part English never prepares you for.",
  ["Exactly 2: no number word, just the -ein ending - yomein, saa3tain.",
   "3 to 10: number + plural noun - talat iyyaam, 5ams saa3aat.",
   "11 and up: number + SINGULAR noun - 7da3sh yom, 3ishreen saa3a."])

A("E2", "E", "clock time",
  "`el-saa3a` + the feminine number.",
  [["el-saa3a tlaate u noss", "3:30"], ["el-saa3a talaat illa rube3", "2:45"]],
  "You say 'the hour three and a half', not 'three thirty'.",
  ["u noss and a half, u rube3 and a quarter, illa rube3 quarter to.",
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

A("F3", "F", "shadda (doubled letter)",
  "Hold the consonant twice as long.",
  [["sakker", "he closed"], ["bazahhe2", "I bore people"]],
  "It's the difference between B12's two verb types - audio only, never judged from spelling.",
  ["sakar sugar vs sakkar he closed.",
   "In B12 the doubling IS the grammar: bad7ak vs bada77ek."])

payload = {
    "updated": "2026-09-22",
    "source": "wiki/18-grammar-buckets.md + Medi additions B16/B17/C10 (2026-09-22)",
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
