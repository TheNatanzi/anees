# -*- coding: utf-8 -*-
"""Sentence-length ladder: how many Arabic words per sentence Medi understands (listening) and strings together
(speaking), with difficulty tags on every sentence. Build contract: plan/SENTENCE-LADDER-SPEC-2026-09-27.md.

    python scripts/build_sentence_ladder.py              -> docs/data/sentence-ladder.json (summary)
                                                            + docs/data/sentence-ladder/<date>.json (sentences)
    python scripts/build_sentence_ladder.py --dump D     -> print lesson D's scored listening units (for hand checks)

Sources (read only, rule S2 - nothing here edits a transcript):
  docs/data/lessons/<date>.json        turns on the LESSON CLOCK (the audio the lesson page plays), chat lines typed_by
  data/lessons/<date>/words_labeled.json  word timings (08-25, 09-04, 09-05 only)
  docs/data/lessons.json               start_local, talk.window, duration
  docs/data/grammar-console.json       hand-verified corrections (rule M1) -> speaking "corrected"
  docs/data/lessons/<date>.json        vocab_errors (hand audit) -> listening misses + words supplied
  docs/data/words.json + word-bank-catalog.json  word keys (same normalisation as docs/js/word-bank-core.js)
  scripts/detect_grammar_usage.py      the 57 grammar-rule patterns (imported, unchanged)

Machine labels are guesses; Medi's swipes (supabase sentence_labels) are the ground truth the front end overlays.
Missing data -> null + a reason, never a guess.
"""
import argparse, datetime as dt, difflib, glob, hashlib, json, math, os, random, re, shutil, subprocess, sys, unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DOCS = os.path.join(REPO, "docs")
DATA = os.path.join(DOCS, "data")
RAW = os.path.join(REPO, "data", "lessons")
OUT_SUMMARY = os.path.join(DATA, "sentence-ladder.json")
OUT_DIR = os.path.join(DATA, "sentence-ladder")
sys.path.insert(0, HERE)

from arabizi import loose, fold, arabic_norm  # noqa: E402
from english_stop import ENGLISH_STOP  # noqa: E402
import detect_grammar_usage as G  # noqa: E402   (patterns only; its __main__ is not run)

VERSION = "2026-09-27"

# ------------------------------------------------------------------ thresholds (all in the spec)
AMAL_JOIN = 3.0        # s: two pieces of Amal's speech closer than this, with no real Medi turn between, are one sentence
MEDI_JOIN = 15.0       # s: Medi builds sentences with long pauses (rule S5) - his pieces join until Amal really speaks
RESCUE_GAP = 3.0       # s: Medi silent this long after her sentence, then she switches to English / rephrases = rescue
LOOKBACK_N = 3         # sentences
LOOKBACK_S = 60.0      # s
LATIN_HINT = 0.4       # an all-unknown Latin sentence counts as Arabic when >= 40% of the speaker's known Latin words nearby are Arabic
MOSTLY_EN = 0.5        # a sentence is skipped when English tokens / (Arabic + English tokens) > this
REPEAT_SIM = 0.7       # difflib ratio on normalised Arabic words = "the same sentence again" (edit distance < 0.3)
REPHRASE_SIM = 0.5
LONG_GAP = 30.0        # s with nobody talking = a break
MISSING_GAP = 240.0    # s: one side silent this long while the other has >= 15 turns = that side's audio is missing
LADDER_LAST = 20
LADDER_PCT = 0.80
LADDER_LESSONS = 2
LADDER_PER_LESSON = 10  # at most 10 of the 20 from one lesson, so the window is spread over >= 2 lessons when the data allows
EFFECT_FLOOR = 30      # decision 6: an effect is shown only when >= 30 scored sentences back it (each side of the split)

# ------------------------------------------------------------------ text
AR_CH = "ء-غف-يٱ-ۓ"
AR = re.compile("[" + AR_CH + "]")
DIAC = re.compile(r"[ً-ٰٟـ]")
BIDI = re.compile(r"[؜‎‏‪-‮⁦-⁩]")
TOKEN = re.compile(r"[ء-غـ-ٰٟ-ۓ]+(?:-{1,2}|—)?|[A-Za-z0-9'’]+(?:-[A-Za-z0-9'’]+)*(?:-{1,2}|—)?")
HOLE = re.compile(r"\[(?:speaking Arabic|speaking foreign language|foreign language|speaks Arabic|in Arabic)\]", re.I)
NOISE = re.compile(r"\[(?:background[^\]]*|beep|keyboard[^\]]*|mumbling|صوت[^\]]*|مقطوع)\]", re.I)
BRACKET = re.compile(r"\[[^\]]*\]")
PAUSE = re.compile(r"\(pause[^)]*\)")
TERMINAL = re.compile(r"[.?!؟…]+[\"'”’)]*$")
SPLIT = re.compile(r"(?<=[.?!؟…])\s+")

FILLER_LAT = {"uh", "um", "umm", "ummm", "uhm", "er", "erm", "eh", "mm", "mmm", "hmm", "hm", "ah", "ahh", "uhh", "oh", "ooh", "huh-uh"}
FILLER_AR = re.compile(r"^(?:[آاأ]{2,}|[آاأإ]?م{2,}|ه?م{2,}|ام|امم+|اه+|آه+|إم|ء*م+|ه+م+)$")


def wb_norm(s):
    """docs/js/word-bank-core.js normalize(): NFKD, marks stripped, أإآ->ا, ى->ي, lower case, non letters -> space."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = re.sub(r"[ً-ٰٟـ]", "", s)
    s = re.sub("[أإآ]", "ا", s).replace("ى", "ي").lower()
    s = "".join(c if (c.isalnum()) else " " for c in s)
    return re.sub(r"\s+", " ", s).strip()


def an(s):
    """Arabic match form (Word Bank arabic_norm: hamza forms unified, ة->ه, ى->ي, marks dropped)."""
    return arabic_norm(s)


# ------------------------------------------------------------------ word lists (hand lists, marked in the spec)
EN_AMBIGUOUS = {"al", "ma", "bin", "ben", "em", "sin", "qeem", "bien", "fill", "boat", "mad", "ai"}
EN_EXTRA = set("""
i'm i've i'll i'd you'd he'd she'd we'd they'd it'll it'd that'll there'll who's what's where's here's how's let's isn't aren't wasn't
weren't hasn't haven't hadn't doesn't don't didn't can't won't wouldn't shouldn't couldn't mustn't gonna wanna gotta kinda sorta cuz
guys guy thanks thank please sorry hello hi bye goodbye wow whoa oops whoops yay hey okay alright sure yes yeah nope mhm mmhmm
speaking arabic english farsi persian spanish language languages foreign levantine fusha arab arabs iran iranian iranians russia uae
laughs laughing chuckles chuckle sighs mumbling background noise chatter chattering beep clears throat
annoyed annoy annoys annoying annoyance broke break breaks breaking broken ruin ruined ruins ruining hurt hurts hurting excited excite
excites exciting enjoy enjoys enjoyed enjoying upset upsets upsetting apologize apologized apologizes apologizing apology scare scared
scares scary scaring bore bored bores boring tire tired tires tiring embarrass embarrassed embarrassing move moves moved moving fun
funny smile smiles smiling laugh laughed mess messed messes stress stressed stressing stressful calm worried worry worries anger angry
angering sadness saddening sad crazy weird lazy busy hungry lucky glad surprised confused confusing curious nervous emotions emotional
feeling feelings mood happy unhappy frustrated frustrating afraid proud jealous lonely
verbs verb nouns noun adjectives adjective adverb adverbs preposition prepositions pronoun pronouns feminine masculine plural singular
dual command commands conditional causative conjugation conjugations tense tenses past present future meaning meanings mean means
sentence sentences phrase phrases expression expressions vowel vowels consonant consonants letter letters syllable syllables
pronounce pronunciation accent grammar rule rules pattern patterns version form forms context example examples review reviewed
reviewing homework flashcards flashcard cards card quiz test tests practice practiced lesson lessons class teacher student
opposite inverse habitual internal physical physically general specific whole middle beginning end ending double doubled object subject
translation translate transcription recording record audio video microphone mic camera screen phone phones computer laptop internet
software program app apps website email link chat message messages whatsapp chatgpt ai tools tool system update updated upload
doctor doctors dentist hospital medicine appointment appointments body head hand hands leg legs foot feet knee stomach back hair eye eyes
ear ears nose mouth teeth tooth heart throat brain face skin arm arms finger fingers shoulder neck pain ache sick fever cold hot heat
weather rain snow sun sunny cloudy windy wind storm temperature degree degrees season spring summer fall autumn winter
food drink drinks eat eating ate cook cooking cooked taste tastes tasted crispy rice bread pizza pasta kebab sushi sausage honey tea
coffee water milk meal meals dinner lunch breakfast restaurant restaurants menu table chef waiter kitchen stove fridge oven cup cups plate
plates spoon teaspoon fork knife dish dishes vinegar salt sugar spicy sweet sour bitter fresh
house home room rooms bed door window windows floor wall building apartment street road city country countries world place places
car bus train plane flight flights trip trips travel traveling ticket tickets hotel booking reservation passenger passengers driver
chauffeur airport station map direction directions left right north south east west far near close open closed
work working worked job jobs manager boss office company company's meeting meetings project projects team customer customers business
money cash pay paid paying price prices credit bank buy bought sell sold shop shopping store market cheap expensive
family father mother mom dad brother sister son daughter wife husband kids kid children child parent parents fiance fianc fiancee
wedding party birthday friend friends people person man men woman women girl girls boy boys baby name names
clothes dress skirt shirt jacket suit shoes socks sunglasses color colors colour colours white black red blue green yellow brown pink
purple gray grey orange outfit wear wearing
time times hour hours minute minutes second seconds day days week weeks month months year years today tomorrow yesterday morning
afternoon evening night tonight weekend monday tuesday wednesday thursday friday saturday sunday january february march april may
june july august september october november december date schedule early late later soon before after during until since
one two three four five six seven eight nine ten eleven twelve twenty thirty forty fifty hundred thousand million half quarter
first second third last next previous number numbers
good bad better best worse worst easy easier easiest hard harder difficult simple simplest complex complicated clear obvious natural
normal normally usual usually important useful possible impossible necessary optional valid random common different similar same
perfect perfectly correct correctly wrong exactly actually honestly basically literally probably maybe definitely certainly surely
really totally completely quickly slowly slow fast quick quiet loud long short big small little tiny large huge full empty new old
young beautiful pretty ugly nice great awesome amazing terrible horrible fine cool warm cold dirty clean safe dangerous
think thinking thought know knew known remember remembered forget forgot forgotten understand understood learn learned learning study
studied studying say said saying tell told telling talk talked talking speak speaks spoke spoken conversation conversations discuss
discussed ask asked asking answer answered answers question questions reply explain explained describe described repeat repeated
repeating repetition continue continued stop stopped start started finish finished complete completed try tried trying help helped
helps need needed want wanted like liked love loved hate prefer preferred decide decided choose chose choice option options
find found look looked looking see saw seen watch watched watching hear heard listen listened read write wrote written
go going went gone come coming came get getting got give giving gave take taking took make making made put putting bring bringing
brought keep kept leave left stay stayed wait waiting waited live lived play playing played walk walked run drive driving sleep slept
call called check checked fix fixed fixes create created follow followed pick picked turn turned change changed changes send sent
open opens opened close closed happen happened happening mean meant feel felt seem seems sound sounds sounded
something anything nothing everything someone somebody anyone everyone nobody somewhere anywhere everywhere nowhere
thing things stuff way ways part parts point reason reasons sense idea ideas problem problems issue issues mistake mistakes error errors
matter case fact kind type sort level side lot bit piece pieces word words
and or but so because if when while although though unless whether then also too very really just only even still already yet again
the a an this that these those my your his her its our their me him us them myself yourself itself
about above across after against along among around at before behind below beneath beside between beyond by down during except for
from in inside into like near of off on onto out outside over past per through throughout to toward towards under underneath until
up upon with within without
song songs music movie movies film films game games dogs dog cat cats animal animals flower flowers tree trees
therapist therapy psychologist session sessions allergy
""".split())
EN_WORDS = (set(ENGLISH_STOP) | EN_EXTRA) - EN_AMBIGUOUS
EN_SUFFIX = re.compile(r"(?:ing|ed|tion|tions|ly|ness|ment|ments|able|ible|ful|ous|ive|ity|ies|'s|'re|'ve|'ll|'d|n't)$")

# Latin-letter Arabic function words (Medi's and the engine's spellings; the article/conjunction attach to the next word)
LAT_AR = set("""
ana inta inte inti intu into huwwe huwe huwa hiyye heyye hiya hiye i7na e7na ihna ahna ehna humme humma hume hum
shu shoo sho eish esh ya3ni yani yaani ya'ani ya3ne mish mush mesh bas kaman kamaan hek heik hake fi fee fih fiha ma3 ma3i ma3ak
min mn 3ala ala 3an la la2 laa il el al w wa u wu oo willa wala walla aw lamma lama iza itha enno inno anno illi ili yalli elli
3ashan 3ashaan ashan mishan lissa lesa ra7 rah 3am kan kaan kanet kunt kunna laazem lazem lazim lazim mumken mumkin momken biddi beddi
biddak bidna badna bedna 3indi 3endi 3ind 3indna andik halla halla2 hala hal2a lesh leesh laish lish wen wein wayn meen min kif keef
kaif 2addesh addesh 2adesh kam emta imta lawain lawen hada hadi hadol hadoal hay hayy hon hoan hina hunak tayyeb tayeb tayyib taieb
taib 6ayyeb yalla khalas 5alas tamam sa7 sah aywa aiwa ayva na3am abadan daiman dayman kteer ktir katir kateer kter shway shwayy
shwai ishi ishy shi shay kul kull akthar aktar a7san ahsan zay metl mitl ba3d ba3den ba3dain ba3dein 2abel abel mafi mafish
marhaba marhaba shukran shukr afwan inshallah habibi ya ahlan sahtein 9a7ten mabrouk mabruk yom yoam el-yom elyom
""".split())

BACKCHANNEL = {"aywa", "aiwa", "ayva", "ايوه", "ايوا", "اه", "اها", "ah", "aha", "ok", "okay", "okey", "اوكي", "yes", "yeah", "yep",
               "yup", "ya", "mm", "mmm", "mhm", "mmhmm", "hmm", "hm", "na3am", "نعم", "sure", "right", "uh-huh", "uhhuh", "oh", "ooh",
               "i", "see", "got", "it", "alright", "cool", "nice", "good", "great", "perfect", "exactly", "true", "صح", "sa7",
               "tamam", "تمام", "no", "la", "لا", "la2", "لأ", "لا", "nope", "mm-hmm", "uh", "um", "yes,", "إي", "اي", "ey"}
BACKCHANNEL_N = {an(w) for w in BACKCHANNEL if AR.search(w)} | {an(w) for w in "أيوه أيوا آه إيه إي أه".split()}
# her feedback / discourse words: an Amal sentence made only of these is not a sentence to understand
FEEDBACK = {an(w) for w in "ممتاز صح طيب برافو تمام أيوه ايوه ايوا أيوا اه آه لا لأ شاطر عظيم حلو كتير منيح يلا خلص مظبوط بالظبط بالزبط اوكي ها هاه هه نعم شو عفوا خلاص عادي يعني okay مهم ممم امم".split()} | \
           {"mumtaz", "sa7", "sah", "sahh", "tayyeb", "tayeb", "tayyib", "bravo", "tamam", "aywa", "yalla", "khalas", "helu", "7elu", "mm", "mhm"}

# function words (closed classes; Arabic script, an() form). Colloquial-only ones are the COLLOQ subset.
FN_AR = {an(w) for w in """
انا أنا انت إنت انتي إنتي انتو إنتو هو هي احنا إحنا هم همه همة
في فيه فيها فيهم من منه منها منهم مني منك على عليه عليها علي عليك عن عنه عنها مع معي معك معه معها معنا معهم ل لل الى إلى
ب بال عند عندي عندك عنده عندها عندنا عندهم عنا إلي الي إلك الك إله إلها إلنا إلهم لي لك له لها لنا لهم
و او أو ولا بس لكن يعني إنه انه إنو انو إن ان لأنه لانه لانو لأن عشان مشان منشان كرمال لما لمّا اذا إذا لو حتى تا
اللي إللي الي هاد هادا هادي هاي هدول هداك هديك هذا هذه هذي ذلك هيك هون هناك هنا
شو ايش إيش وين ليش مين كيف قديش أديش اديش امتى إمتى لوين كم أي اي
ما مش مو لا ولا مافي مافيش ماشي
كمان كتير شوي هلأ هلق هلا هلء لسا لسه لسّا بعدين بعد قبل هلقيت
عم رح راح بدي بدك بدها بده بدنا بدكم بدهم لازم ممكن كان كانت كنت كنا كانوا يكون تكون
كل بعض نفس غير زي متل مثل تبع تبعي تبعك شي إشي اشي حدا ولا اشي
يا طيب يلا خلص أه آه اه ايوه أيوه نعم
""".split()}
COLLOQ = {an(w) for w in """
شو ايش إيش ليش وين هلأ هلق هلا هلء هلقيت بدي بدك بده بدها بدنا بدكم بدهم عم رح مش كمان هيك لسا لسه لسّا قديش أديش اديش مين
إمتى امتى لوين هون هناك كتير شوي إشي اشي شي حدا مبارح امبارح بكرا بكرة منيح هاد هادا هادي هاي هدول هداك هديك اللي إللي
إنو انو يلا خلص طيب عشان مشان منشان كرمال زي متل تبع تبعي تبعك مافي مافيش جاي رايح دغري برا جوا قدام ورا هسا بعدين
""".split()}
LAT_FN = {"ana", "inta", "inte", "inti", "intu", "huwwe", "huwe", "huwa", "hiyye", "heyye", "hiya", "i7na", "e7na", "ihna", "humme",
          "shu", "shoo", "ya3ni", "yani", "mish", "mush", "bas", "kaman", "hek", "heik", "fi", "fee", "ma3", "min", "3ala", "ala",
          "3an", "la", "willa", "wala", "aw", "lamma", "lama", "iza", "enno", "inno", "illi", "ili", "3ashan", "ashan", "lissa",
          "ra7", "rah", "3am", "laazem", "lazem", "mumken", "biddi", "3indi", "halla", "halla2", "lesh", "leesh", "wen", "meen",
          "kif", "keef", "kam", "emta", "hada", "hadi", "hay", "hon", "tayyeb", "yalla", "khalas", "kteer", "ktir", "shway", "ishi",
          "shi", "kul", "zay", "metl", "ma"}
LAT_COLLOQ = {"shu", "shoo", "lesh", "leesh", "wen", "halla", "halla2", "biddi", "biddak", "bidna", "3am", "ra7", "mish", "mush",
              "kaman", "hek", "heik", "lissa", "2addesh", "addesh", "meen", "emta", "lawain", "hon", "kteer", "ktir", "shway",
              "ishi", "7ada", "mbare7", "bukra", "mni7", "hada", "hadi", "hay", "hadol", "illi", "enno", "yalla", "khalas",
              "tayyeb", "3ashan", "zay", "metl", "tab3i", "mafi"}
WH_AR = {an(w) for w in "شو ايش إيش وين ليش مين كيف قديش أديش اديش امتى إمتى لوين كم أي اي شلون".split()}
WH_LAT = {"shu", "shoo", "eish", "wen", "wein", "lesh", "leesh", "meen", "kif", "keef", "2addesh", "addesh", "kam", "emta", "imta",
          "lawain", "what", "where", "why", "who", "how", "when", "which"}
EMPH_AR = set("صضطظحعقغخ")
EMPH_LAT = set("976385q")

# fixed phrases / idioms. Seed = recurring n-grams in Amal's speech (>= 6 times in >= 3 lessons, 2026-09-27 run) that are
# fixed expressions + the everyday Levantine set phrases. an() form, matched on the normalised sentence.
IDIOMS = [an(p) for p in """
شو يعني|يعني شو|كمان مرة|كمان مره|احكي لي|احكيلي|اعطيني جملة|أعطيني جملة|كل شي|مش مشكلة|ما في مشكلة|ما في|أول إشي|اول اشي|يلا بشوفك|
أهلا وسهلا|اهلا وسهلا|عن جد|عنجد|إشي تاني|اشي تاني|كيف الجو|يعطيك العافية|يعطيكي العافية|الله يعافيك|الله يعافيكي|على راسي|
إن شاء الله|ان شاء الله|انشالله|الحمد لله|الحمدلله|صحتين|على قلبك|مع السلامة|تصبح على خير|تصبحي على خير|ولا يهمك|الله يسلمك|بالعكس|
مبروك|الله يبارك فيك|كل عام وإنت بخير|على فكرة|يا ريت|معليش|من زمان|شو القصة|مش هيك|كيف حالك|شو أخبارك|شو اخبارك|تكرم|تكرمي|
ما شاء الله|ماشالله|يا حرام|بالزبط|بالظبط|ولا إشي|ولا اشي|شو رأيك|شو رايك|على مهلك|خلص خلص|يلا يلا
""".replace("\n", "").split("|") if p.strip()]
IDIOMS = sorted(set(p for p in IDIOMS if p), key=len, reverse=True)
IDIOMS_LAT = ["shu ya3ni", "kaman marra", "mish mushkile", "ma fi", "ya3tik el3afye", "inshallah", "el7amdilla", "sa7tein",
              "3ala albak", "ma3 elsalame", "3an jad", "kif 7alak", "kif el jaw"]

# meaning / repeat / not-understand signals in Medi's reply
RX_REPEAT = re.compile(r"^\W*(?:huh|what|sorry|pardon|excuse me|ha|هه|ها|هاه|شو|shu|eh|again|come again|what\?)\W*$", re.I)
RX_REPEAT2 = re.compile(r"\b(?:say (?:that|it) again|(?:can|could) you (?:repeat|say)|repeat (?:that|it|please|the)|one more time|"
                        r"come again|what did you say|i didn'?t (?:hear|catch)|didn'?t catch|slower|more slowly|again[?؟]|"
                        r"are you saying|you'?re saying|did you say|you said\s+\S+\s*[?؟]|what\s+was\s+(?:it|that)\b|what\s+did\s+you\s+just)|"
                        r"(?<!\S)ما\s+هذا|شو\s+قلت|"
                        r"كمان مرة|(?<!\S)عيدي(?!\S)|3eedi|3idi|kaman marra|شو قلتي|شو حكيتي|shu 2olti|shu 2ulti", re.I)
# signal 2, asking: he asks what her word means
RX_MEANING = re.compile(r"(?:شوي?\s+يعني|ايش\s+يعني|إيش\s+يعني|يعني\s+شو|shu\s+ya3ni|shu\s+yani|shoo\s+ya3ni|ya3ni\s+shu|"
                        r"what\s+(?:does|do|did)\s+.{0,40}?\bmean\b(?!\s+in\s+arabic)|what'?s\s+(?:the\s+)?meaning|what\s+is\s+the\s+meaning|meaning[?؟]|"
                        r"شو\s+(?:هاد|هاي|هادا|هادي|هيدا)\s*[؟?]?$|what\s+(?:is|was)\s+(?:that|this)\s*[?؟]|what\s+was\s+the\s+last|"
                        r"what\s+do\s+you\s+mean|meaning\s+of)", re.I)
# "what's X?" counts only when X is one of her Arabic words (else it is his own translation: "what's on your face?")
RX_WHATS = re.compile(r"what(?:'s|\s+is)\s+((?:\S+\s*){1,3}?)\s*[?؟]", re.I)
# signal 2, checking a guess: "does it mean X?", "X means Y, right?" - stored, but the sentence is 'unknown', not a breakdown
RX_GUESS = re.compile(r"does\s+(?:that|it|this|.{1,25})\s+mean|is\s+(?:that|it)\s+(?:like|the same)\b|"
                      r"\bmeans?\s+.{1,30}?,?\s*(?:right|correct|yes)?\s*[?؟]|that\s+it\s+mean", re.I)
RX_DONT = re.compile(r"(?:\bi\s+(?:don'?t|do\s+not|didn'?t|did\s+not)\s+(?:understand|get\s+(?:it|that|what)|follow|catch)|"
                     r"\bnot\s+sure\s+what\s+you|\bi'?m\s+(?:lost|confused)|\bno\s+idea\b|مش\s+فاهم|مش\s+فاهمة|ما\s+فهمت|مافهمت|"
                     r"mish\s+fahem|mush\s+fahem|ma\s+fhemt|ma\s+fhimt|i\s+don'?t\s+know\s+what\s+(?:that|this|it|you)|"
                     r"what\s+are\s+you\s+(?:saying|asking))", re.I)
RX_DONT_SHORT = re.compile(r"^\W*(?:i\s+don'?t\s+know|i\s+dunno|no\s+idea|ما\s+بعرف|مش\s+عارف|ma\s+ba3ref|mish\s+3aref)\W*$", re.I)
RX_PRODUCTION = re.compile(r"how\s+do\s+(?:you|i)\s+say|what'?s\s+the\s+word\s+for|how\s+to\s+say|كيف\s+بقول|كيف\s+بحكي", re.I)
RX_NEG_START = re.compile(r"^\W*(?:لا|لأ|no|nope|la|la2|not|مش\s+هيك|مش|لا\s+لا)\b", re.I)
RX_TRANSLATE_PROMPT = re.compile(r"(?:شو\s+يعني|ايش\s+يعني|إيش\s+يعني|يعني\s+شو|shu\s+ya3ni|what\s+does\s+.{0,30}mean|"
                                 r"شو\s+معنى|what'?s\s+(?:the\s+)?meaning|meaning\??$|in\s+english)", re.I)
RX_TRANSITION = re.compile(r"^\W*(?:طيب|يلا|هلأ|هلا|هلق|خلص|okay\s+so|ok\s+so|so\s+now|now\s+let'?s|let'?s|next|tayyeb|yalla|halla|alright)\b", re.I)
# the lesson audit's hand-read 'why' says HE missed HER words (not: she misheard him, not: he could not produce a word)
RX_LISTEN_MISS = re.compile(r"\bhe\s+(?:heard|misheard|decoded|read\s+(?:her|it\s+as)|took\s+\S+\s+for|could\s+not\s+place|"
                            r"did\s+not\s+catch|didn't\s+catch|did\s+not\s+recognise|didn't\s+recognise|answered\s+about|"
                            r"could\s+not\s+give|could\s+not\s+recall\s+the\s+meaning|asked\s+the\s+meaning|did\s+not\s+know\s+\S+\s+\(|"
                            r"guessed)|\bmisheard\b|comprehension\s+miss|supplied\s+the\s+meaning|asked\s+the\s+meaning|"
                            r"quizzed\s+the\s+(?:meaning|expression)|quizzed\s+(?:him\s+)?on\b|quizzed\s+'|\bListening:|"
                            r"heard\s+'[^']+'\s+as|asked\s+whether\s+it\s+meant|asked\s+what\s+.{0,40}means", re.I)
RX_PRODUCTION_WHY = re.compile(r"how to say|asked (?:amal )?for the word|asked how|for a word he|wanted to say|"
                               r"\b(?:she|amal)\s+(?:heard|read|explicitly rejected)|asked\s+(?:if|whether)\s+he\s+meant|"
                               r"produce the arabic|could not recall it|plural of|the plural|she heard", re.I)
# a rescue in English says so: she glosses, checks, or reminds (plain English teaching talk after a pause is not a rescue)
RX_RESCUE_EN = re.compile(r"\b(?:(?:it|that|this)\s+means|meaning|i\s+said|i\s+asked|i'?m\s+asking|did\s+you\s+(?:understand|get|hear)|"
                          r"do\s+you\s+(?:understand|know|remember)|you\s+remember|remember|in\s+english|it'?s\s+like|which\s+is|"
                          r"that\s+is|so\s+i'?m\s+saying|i'?m\s+saying)\b", re.I)
RX_GLOSS = re.compile(r"\b(?:i\s+said|i\s+asked|i\s+mean|means|meaning|i'?m\s+asking)\b", re.I)


# ------------------------------------------------------------------ Word Bank index (same keys the browser has)
class Bank:
    def __init__(self, repo_docs=DATA):
        items = json.load(open(os.path.join(repo_docs, "words.json"), encoding="utf-8"))["items"]
        cat = json.load(open(os.path.join(repo_docs, "word-bank-catalog.json"), encoding="utf-8"))
        self.items = {w["key"]: w for w in items}
        self.by_ar, self.by_loose, self.by_fold = defaultdict(set), defaultdict(set), defaultdict(set)
        self.topic = {w["key"]: w.get("topic") for w in items}
        self.verb_form = {}          # an(arabic form) -> (group key, latin word, label)
        self.group_of = {}           # key -> group key
        self.group_root = {}         # group key -> root estimate
        self.group_present_lat = {}  # group key -> Amal's Arabizi of the present form (for the verb pattern)
        pron_ar = {an(w) for w in "أنا انا إنت انت إنتي انتي إنتو انتو هو هي إحنا احنا هم همه".split()}
        pron_lat = {"ana", "inta", "inti", "intu", "huwwe", "huwe", "heyye", "heiye", "hiyye", "i7na", "hume", "humme"}

        def add_ar(form, key):
            ws = [x for x in an(re.sub(r"\([^)]*\)", " ", form or "")).split() if x]
            ws = [x for x in ws if x not in pron_ar] if len(ws) > 1 else ws
            if len(ws) == 1:
                self.by_ar[ws[0]].add(key)

        def add_lat(form, key):
            ws = [x for x in re.sub(r"\([^)]*\)", " ", form or "").split() if x]
            if len(ws) > 1 and ws[0].lower().strip(".,") in pron_lat:
                ws = ws[1:]
            if len(ws) == 1:
                self.by_loose[loose(ws[0])].add(key)
                self.by_fold[fold(ws[0])].add(key)

        for w in items:
            for part in re.split(r"\s*/\s*", w.get("arabic") or ""):
                add_ar(part, w["key"])
            for f in [w.get("arabizi")] + list(w.get("aliases") or []):
                for part in re.split(r"\s*/\s*", f or ""):
                    add_lat(part, w["key"])
        for g in cat.get("groups", []):
            gk = g["key"]
            for k in g.get("keys") or [gk]:
                self.group_of[k] = gk
            for e in g.get("entries", []):
                forms = [(e.get("arabic"), e.get("word"), gk)] + [(p.get("arabic"), p.get("word"), p.get("key") or gk)
                                                                  for p in e.get("persons") or []]
                for ar_, lat_, key in forms:
                    if ar_:
                        add_ar(ar_, key)
                        if g.get("type") == "Verb":
                            ws = [x for x in an(ar_).split() if x not in pron_ar]
                            if len(ws) == 1 and lat_:
                                lw = [x for x in (lat_ or "").split() if x.lower() not in pron_lat]
                                self.verb_form.setdefault(ws[0], (gk, lw[-1] if lw else lat_, e.get("label")))
                    if lat_:
                        add_lat(lat_, key)
            if g.get("type") == "Verb":
                self.group_root[gk] = root_of(an((g.get("arabic") or "").split("/")[0]))
                pres = [e for e in g.get("entries", []) if e.get("label") == "Present"]
                self.group_present_lat[gk] = (pres[0].get("word") if pres else None) or g.get("name")
        self.roots = defaultdict(set)
        for gk, r in self.group_root.items():
            if r:
                self.roots[r].add(gk)
        # every single Arabic word the Doc knows (for clitic stripping: a stem must be a real word)
        self.lexicon = set(self.by_ar) | {w for w in G.PAST} | {w for w in G.PRESENT_STEMS}
        # present stems from the catalog's Present forms too (the detector's list only has the Doc's 'Verbs List')
        self.present_stems = set(G.PRESENT_STEMS)
        for form, keys in self.by_ar.items():          # her Doc words written 'Ana b...' are present verbs too
            if form.startswith("ب") and len(form) >= 4 and any(
                    re.match(r"ana\s+b", (self.items.get(k, {}).get("arabizi") or "").lower()) for k in keys):
                for p in ("بت", "بن", "بي", "ب"):
                    if form.startswith(p) and len(form) - len(p) >= 2:
                        self.present_stems.add(form[len(p):])
                        break
        for form, (gk, lat_, label) in self.verb_form.items():
            if label == "Present":
                for p in ("بت", "بن", "بي", "ب"):
                    if form.startswith(p) and len(form) - len(p) >= 2:
                        self.present_stems.add(form[len(p):])
                        break

    def is_b_present(self, w):
        if G.is_b_present(w):
            return True
        for p in ("بت", "بن", "بي", "ب"):
            if w.startswith(p) and len(w) - len(p) >= 2 and w[len(p):] in self.present_stems:
                return True
        return False

    def keys_ar(self, n):
        """Arabic token (an() form) -> sorted keys; tries the word, then without proclitics, then without an ending."""
        if n in self.by_ar:
            return sorted(self.by_ar[n]), "word"
        for p in ("وال", "بال", "لل", "فال", "ال", "و", "ف"):
            if n.startswith(p) and len(n) - len(p) >= 2:
                m = n[len(p):]
                if m in self.by_ar:
                    return sorted(self.by_ar[m]), "prefix"
                if "ال" + m in self.by_ar:
                    return sorted(self.by_ar["ال" + m]), "prefix"
        for s in ("هم", "كم", "ها", "نا", "ني", "كي", "ه", "ك", "ي", "و"):
            if n.endswith(s) and len(n) - len(s) >= 2 and n[:-len(s)] in self.by_ar:
                return sorted(self.by_ar[n[:-len(s)]]), "stem"
        return [], None

    def keys_lat(self, tok):
        lo = loose(tok)
        if lo in self.by_loose:
            return sorted(self.by_loose[lo]), "loose"
        fo = fold(tok)
        if fo in self.by_fold and len(fo) >= 3:
            return sorted(self.by_fold[fo]), "fold"
        return [], None


def root_of(stem):
    """Rough triliteral root of a present-tense stem in Arabic script (بتغيّر -> غير). Estimate, used only for 'known root'."""
    s = stem or ""
    for p in ("بت", "بن", "بي", "ب"):
        if s.startswith(p) and len(s) - len(p) >= 3:
            s = s[len(p):]
            break
    for p in ("است", "ان", "ت"):
        if s.startswith(p) and len(s) - len(p) >= 3:
            s = s[len(p):]
            break
    cons = [c for c in s if c not in "اويى"]
    return "".join(cons[:3]) if len(cons) >= 3 else ("".join(cons) if len(cons) == 2 else None)


_BANK = None


def bank():
    global _BANK
    if _BANK is None:
        _BANK = Bank()
    return _BANK


# ------------------------------------------------------------------ tokens
def latin_kind(tok, bk=None):
    t = tok.lower().replace("’", "'").strip("'")
    if not t:
        return "skip"
    if t in FILLER_LAT or re.fullmatch(r"(?:u+h+|u+m+|m+|h+m+|a+h+|e+h+|o+h+)", t):
        return "fill"
    if t.isdigit():
        return "num"
    if re.search(r"[a-z][2356789]|[2356789][a-z]", t):
        return "ar"
    base = t.split("-")[-1] if "-" in t else t
    if t in LAT_AR or base in LAT_AR:
        return "ar"
    if t in EN_WORDS or base in EN_WORDS:
        return "en"
    if bk is not None and bk.keys_lat(base)[0]:
        return "ar"
    if EN_SUFFIX.search(t):
        return "en"
    return "unk"


def tokenize(text, bk=None, hint=None):
    """Words of one sentence: [{w, s: 'ar'|'en'|'num'|'fill', lat: bool}], clitics kept inside their word (بيتي = 1),
    a lone و/ب/ل/الـ or Latin el/il/w/u joined to the next word, cut-off fragments (شك-شكلو, ta-tam) and immediate
    stutter repeats dropped."""
    text = BIDI.sub("", PAUSE.sub(" ", BRACKET.sub(" ", text or "")))
    raw = TOKEN.findall(text)
    out = []
    carry = ""
    for i, tok in enumerate(raw):
        cut = bool(re.search(r"(?:-{1,2}|—)$", tok))
        tok = re.sub(r"(?:-{1,2}|—)$", "", tok)
        if not tok:
            continue
        if AR.search(tok):
            n = an(tok)
            if cut:                                   # a word he broke off: محـ-- / شك-شكلو
                continue
            if FILLER_AR.match(n):
                out.append({"w": tok, "s": "fill", "lat": False})
                continue
            if n in ("و", "ب", "ل", "ف", "ال", "الـ") or tok in ("الـ", "ال"):
                carry += tok.replace("ـ", "")
                continue
            w = carry + tok
            carry = ""
            if out and out[-1]["s"] == "ar" and not out[-1]["lat"] and an(out[-1]["w"]) == an(w):
                continue                              # stutter: إحنا، إحنا
            out.append({"w": w, "s": "ar", "lat": False})
        else:
            low = tok.lower()
            if "-" in low:
                parts = low.split("-")
                if parts[0] not in ("el", "il", "al", "w", "b", "l", "bi", "fi", "3a", "wel", "bel") and \
                        len(parts) == 2 and parts[1].startswith(parts[0][:2]) and len(parts[0]) < len(parts[1]):
                    tok = tok.split("-")[-1]          # ta-tam / mush-mushkila: the cut-off first go is dropped
            if cut:
                continue
            k = latin_kind(tok, bk)
            if k == "skip":
                continue
            if k == "ar" and low in ("el", "il", "al", "w", "u", "wa", "oo", "wu", "b", "l", "bi"):
                carry += low + "-"
                continue
            w = (carry + tok) if carry and k in ("ar", "unk") else tok
            carry = "" if k in ("ar", "unk") else carry
            if out and out[-1]["s"] == k and out[-1]["lat"] and out[-1]["w"].lower() == w.lower() and k != "en":
                continue
            out.append({"w": w, "s": k, "lat": True})
    # unknown Latin tokens: Arabic when the sentence's known tokens lean Arabic; with no known tokens, follow the speaker's
    # stretch (hint = share of his/her known Latin tokens within +-120 s that are Arabic); no hint -> English
    ar_n = sum(1 for x in out if x["s"] == "ar")
    en_n = sum(1 for x in out if x["s"] == "en")
    for x in out:
        if x["s"] == "unk":
            if ar_n or en_n:
                x["s"] = "ar" if ar_n >= 1 and ar_n >= en_n else "en"
            else:
                x["s"] = "ar" if hint is not None and hint >= LATIN_HINT else "en"
            x["guess"] = True
    return out


def count_words(text, bk=None, hint=None):
    toks = tokenize(text, bk, hint)
    ar_n = sum(1 for x in toks if x["s"] == "ar")
    en_n = sum(1 for x in toks if x["s"] == "en")
    return ar_n, en_n, toks


def mostly_english(ar_n, en_n):
    return (ar_n + en_n) == 0 or en_n / (ar_n + en_n) > MOSTLY_EN


# ------------------------------------------------------------------ morphology estimates
PRON_SUFFIX = ("هم", "كم", "كن", "ها", "نا", "ني", "كي", "ه", "ك", "ي", "و")
DATIVE = ("لكم", "لهم", "لها", "لنا", "لك", "لي", "له", "لو")
FN_WITH_ENDING = {an(w) for w in "عندي عندك عنده عندها عندنا عندهم عنا معي معك معه معها معنا معهم إلي إلك إله إلها إلنا إلهم "
                                   "فيه فيها فيهم منه منها منهم مني منك عليه عليها علي عليك عنه عنها بدي بدك بده بدها بدنا بدكم بدهم "
                                   "تبعي تبعك تبعه تبعها لي لك له لها لنا لهم".split()}


def verbish(stem, bk):
    return G.is_past(stem) or bk.is_b_present(stem) or stem in bk.verb_form or stem[:1] in "بتينأا"


def clitics_ar(n, prev, bk, after_3am=False):
    """Attached pieces on one Arabic word (an() form): object/possessive endings, the dative -l- (حكيتلك), -ش, and the
    b-/bi- prefix (present or preposition); +1 after عم. Articles and و are not counted (research report: enclitics +
    b-/3am). An ending is only stripped when what is left is a real word of hers (or one of her verb forms)."""
    if n in FN_WITH_ENDING:
        return 1
    if n in FN_AR:
        return 0
    base = 1 if after_3am else 0
    cands = [n] + ([n[1:]] if n[:1] in ("و", "ف") and len(n) >= 4 else [])
    return base + max(_clitics_core(w, prev, bk) for w in cands)


def _clitics_core(w, prev, bk):
    c = 0
    real = lambda x: x in bk.lexicon or x in FN_AR or G.is_past(x) or bk.is_b_present(x)
    if w.endswith("ش") and len(w) >= 4 and (an(prev or "") == "ما" or w.startswith("ما")):
        c += 1
        w = w[:-1]
        if w.startswith("ما") and len(w) >= 5:
            w = w[2:]
    stem = w
    for s in DATIVE:
        if w.endswith(s) and len(w) - len(s) >= 3 and verbish(w[:-len(s)], bk):
            c += 1
            stem = w[:-len(s)]
            break
    else:
        for s in PRON_SUFFIX:
            st = w[:-len(s)]
            if w.endswith(s) and len(st) >= 2 and real(st):
                c += 1
                stem = st
                break
    if stem.startswith("ب") and len(stem) >= 3 and (
            stem.startswith("بال") or bk.is_b_present(stem) or (stem in bk.verb_form and bk.verb_form[stem][2] == "Present")
            or (stem not in bk.lexicon and stem[1:] in bk.lexicon)):
        c += 1
    return c


def clitics_lat(tok, prev):
    t = tok.lower()
    c = 0
    if re.match(r"^b(?:a|i|e|y|t|n)[a-z0-9']{3,}", t) and t not in LAT_AR:
        c += 1
    if t.endswith("sh") and (prev or "").lower() in ("ma", "ma'") and len(t) > 4:
        c += 1
        t = t[:-2]
    if re.search(r"(?:l(?:ak|ik|ek|i|o|ha|hom|na|kom))$", t) and len(t) > 5:
        c += 1
    elif re.search(r"(?:ni|ak|ek|ik|ha|hom|na|kom|o)$", t) and len(t) > 4 and c:
        c += 1
    return c


def syllables(tok, lat):
    if lat:
        return max(1, len(re.findall(r"[aeiouAIU]+", tok)))
    n = an(tok)
    if n.startswith("ال") and len(n) > 3:
        n = n[2:]
    return max(1, round(len(n) / 2))


def verb_form_of(present_latin):
    """Arabic verb pattern (I, II, III, V, VI, VII, VIII, X) read off Amal's Arabizi of the verb's PRESENT form in her Doc:
    a doubled consonant before a vowel = II (ba5arreb), t + doubled = V (bat8ayyar), t + C aa = VI, n- = VII (banbese6),
    C t = VIII (bashte8el), st- = X, C aa C v C = III (basaa3ed). Estimate; geminate roots (ba7ess) stay I."""
    s = (present_latin or "").lower().strip()
    s = re.sub(r"^(?:ana|inta|inti|intu|huwwe|huwe|heyye|heiye|i7na|humme|hume)\s+", "", s)
    s = s.split("/")[0].strip().split(" ")[0]
    s = s.replace("sh", "S").replace("kh", "5").replace("gh", "8").replace("th", "T")
    s = re.sub(r"^b(?:a|e|i)?(?=[a-zS5T0-9])", "", s, count=1)
    if not s:
        return None
    C = "[bcdfhjklmnpqrstvwxyzS5T2356789]"
    if re.match(r"^st", s):
        return "X"
    if re.match(r"^n" + C, s):
        return "VII"
    if re.match(r"^t" + C + r"aa", s):
        return "VI"
    if re.match(r"^t", s) and re.search(r"(" + C + r")\1[aeiou]", s):
        return "V"
    if re.match(r"^" + C + r"t[aeiou]", s):
        return "VIII"
    if re.search(r"(" + C + r")\1[aeiou]", s):
        return "II"
    if re.match(r"^" + C + r"aa" + C + r"[aeiou]" + C, s):
        return "III"
    return "I"


# ------------------------------------------------------------------ sentence tags
def sentence_tags(toks, text, bk):
    """Everything computable from the sentence itself. toks come from tokenize()."""
    ar = [x for x in toks if x["s"] == "ar"]
    en = [x for x in toks if x["s"] == "en"]
    out_tok = []
    prev = None
    after_3am = False
    nouns = fnw = clw = 0
    cl_hist = Counter()
    persons, tenses, neg = set(), set(), []
    verb_forms = []
    colloq = 0
    letters = emph = 0
    syl = 0
    for i, x in enumerate(ar):
        w = x["w"]
        lat = x["lat"]
        if lat:
            base = w.lower().split("-")[-1]
            keys, via = bk.keys_lat(base)
            is_fn = base in LAT_FN
            c = clitics_lat(w, prev)
            if base in LAT_COLLOQ:
                colloq += 1
            n_ar = None
            letters += len(re.findall(r"[a-z0-9]", base))
            emph += sum(1 for ch in base if ch in EMPH_LAT)
        else:
            n_ar = an(w)
            keys, via = bk.keys_ar(n_ar)
            is_fn = n_ar in FN_AR
            c = clitics_ar(n_ar, prev, bk, after_3am)
            if n_ar in COLLOQ:
                colloq += 1
            letters += len(n_ar)
            emph += sum(1 for ch in n_ar if ch in EMPH_AR)
        after_3am = (n_ar == "عم") or (lat and w.lower() == "3am")
        syl += syllables(w, lat)
        cl_hist["2+" if c >= 2 else str(c)] += 1
        if is_fn:
            fnw += 1
        if c >= 1:
            clw += 1
        topic = bk.topic.get(keys[0]) if keys else None
        noun = False
        if not is_fn:
            if topic and topic not in ("Past Tense", "Command Tense", "Verbs List", "Adjectives", "Sentence Toolbox",
                                       "Everyday Expressions", "Quantity / Degree", "Numbers", "Introductions and Pleasantries"):
                noun = keys[0] not in bk.group_of          # catalog groups are verbs and adjectives
            elif not keys and n_ar and (n_ar.startswith("ال") or n_ar.startswith(("بال", "وال", "لل"))) and len(n_ar) >= 4:
                noun = True
        if noun:
            nouns += 1
        # tense / person from the Doc lexicons (Latin: from the matched key's topic)
        if topic == "Past Tense":
            tenses.add("past")
        elif topic == "Command Tense":
            tenses.add("command")
        elif topic == "Verbs List":
            tenses.add("present")
        # verb pattern for catalog verbs
        vf = bk.verb_form.get(n_ar) if n_ar else None
        if vf:
            gk, latw, label = vf
            form = verb_form_of(bk.group_present_lat.get(gk) or latw)
            r = bk.group_root.get(gk)
            others = (bk.roots.get(r) or set()) - {gk}
            verb_forms.append({"w": w, "group": gk, "form": form, "root": r, "root_in_bank_other": bool(others),
                               "tense_form": label})
        rec = {"w": w, "n": wb_norm(w)}
        if keys:
            if len(keys) == 1:
                rec["k"] = keys[0]
            else:
                rec["ks"] = keys[:4]
        if is_fn:
            rec["f"] = 1
        if c:
            rec["c"] = c
        if lat:
            rec["lat"] = 1
        if x.get("guess"):
            rec["guess"] = 1
        out_tok.append(rec)
        prev = w
    # rules (the detector's own patterns, the same loop as its __main__ for Medi's turns)
    rules = rules_in(text)
    for rid, tn in (("B1", "present"), ("B5", "past"), ("B6", "past"), ("B7", "past"), ("B13", "future"), ("B10", "command"),
                    ("B14", "progressive"), ("B11", "command")):
        if rid in rules:
            tenses.add(tn)
    low = " " + " ".join(an(x["w"]) if not x["lat"] else x["w"].lower() for x in ar) + " "
    if re.search(r" (?:رح|راح|ra7|rah) ", low):
        tenses.add("future")
    if re.search(r" (?:عم|3am) ", low):
        tenses.add("progressive")
    # negation subtype
    ws = [an(x["w"]) if not x["lat"] else x["w"].lower() for x in ar]
    for i, w in enumerate(ws):
        nxt = ws[i + 1] if i + 1 < len(ws) else ""
        prv = ws[i - 1] if i else ""
        if w in ("مش", "mish", "mush", "mesh", "مو"):
            neg.append("mish")
        elif (w in ("ما", "ma") and nxt.endswith(("ش", "sh")) and len(nxt) > 3) or \
                (w.startswith(("ما", "ma")) and w.endswith(("ش", "sh")) and len(w) > 4 and w not in ("mash", "mafish")):
            neg.append("ma_sh")
        elif w in ("ما", "ma") and nxt and prv not in ("بعد", "قبل", "لما", "شو", "اللي", "كل", "ba3d", "2abel", "shu", "illi", "زي"):
            neg.append("ma")
        elif w in ("مافي", "مافيش", "mafi", "mafish"):
            neg.append("ma")
        elif w in ("لا", "la") and nxt[:1] in ("ت", "t") and len(nxt) > 2:
            neg.append("la_imperative")
    # person (non-first-person markers)
    for i, w in enumerate(ws):
        if w in {an(p) for p in ("إنت", "إنتي", "إنتو", "انت", "انتي", "انتو")} or w in ("inta", "inti", "intu", "inte"):
            persons.add("2")
        elif w in ("هو", "هي", "هم", "همه", "huwwe", "huwe", "huwa", "hiyye", "heyye", "hiya", "humme", "humma"):
            persons.add("3")
        elif w in ("انا", "ana"):
            persons.add("1s")
        elif w in ("احنا", "i7na", "e7na", "ihna", "ahna"):
            persons.add("1p")
        elif not ar[i]["lat"] and w.startswith("ب") and G.is_b_present(w):
            persons.add("2/3f" if w.startswith("بت") else "3" if w.startswith("بي") else "1p" if w.startswith("بن") else "1s")
        elif not ar[i]["lat"] and G.is_past(w):
            persons.add("2" if w.endswith(("تي", "تو", "توا")) else "1p" if w.endswith("نا") else "3" if w.endswith("وا") else "1s/2/3f" if w.endswith("ت") else "3")
        elif not ar[i]["lat"] and w.endswith(("ك", "كي", "كم")) and len(w) >= 4 and w not in FN_AR:
            persons.add("2")
    non_first = any(p in ("2", "3", "2/3f") for p in persons)
    # question type
    first = ws[0] if ws else ""
    is_q = bool(re.search(r"[؟?]\s*$", text.strip()))
    has_wh = any(w in WH_AR or w in WH_LAT for w in ws[:3]) or any(w in WH_AR for w in ws)
    qtype = ("wh" if has_wh else "yn") if is_q else ("wh" if first in WH_AR or first in WH_LAT else "statement")
    prompt = "meaning" if RX_TRANSLATE_PROMPT.search(text) else None
    # idioms
    normtxt = " " + " ".join(an(x["w"]) for x in ar if not x["lat"]) + " "
    lattxt = " " + " ".join(x["w"].lower() for x in ar if x["lat"]) + " "
    idioms = [p for p in IDIOMS if " " + p + " " in normtxt] + [p for p in IDIOMS_LAT if " " + p + " " in lattxt]
    en_run = run = 0
    for x in toks:
        if x["s"] == "en":
            run += 1
            en_run = max(en_run, run)
        elif x["s"] == "ar":
            run = 0
    n = len(ar)
    tags = {
        "len": n,
        "syll": syl,
        "tense": sorted(tenses) or ["none"],
        "cl_max": max([t.get("c", 0) for t in out_tok] or [0]),
        "cl_hist": {k: cl_hist.get(k, 0) for k in ("0", "1", "2+")},
        "noun_share": round(nouns / n, 2) if n else None,
        "fn_share": round(fnw / n, 2) if n else None,
        "clitic_word_share": round(clw / n, 2) if n else None,
        "fn_or_clitic_share": round(sum(1 for t in out_tok if t.get("f") or t.get("c")) / n, 2) if n else None,
        "neg": sorted(set(neg)) or ["none"],
        "persons": sorted(persons),
        "non_first": non_first,
        "verb_forms": verb_forms,
        "q": qtype,
        "prompt": prompt,
        "en_tokens": len(en),
        "en_clause": en_run >= 3,
        "idioms": idioms,
        "colloq_fn": colloq,
        "emph_density": round(emph / letters, 2) if letters else None,
    }
    return tags, out_tok, sorted(rules)


def rules_in(text):
    """The 57-rule detector exactly as scripts/detect_grammar_usage.py runs it on one of Medi's turns."""
    if not G.AR_WORD.search(text or ""):
        return set()
    txt = re.sub(r"(?:^|\s)الـ(?=\s|$|[،,.])", " ", text)
    txt = re.sub(r"\S+(--|—)", " ", txt)
    words = G.AR_WORD.findall(txt)
    found = G.word_rules(words)
    for bid in G.ids:
        if bid in G.NOT_COUNTED or bid in found:
            continue
        for pat in G.P.get(bid, []):
            if re.search(pat, txt):
                found[bid] = True
                break
    return set(found)


# ------------------------------------------------------------------ lesson loading
def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def clean_text(s):
    return re.sub(r"\s+", " ", BIDI.sub("", PAUSE.sub(" ", BRACKET.sub(" ", s or "")))).strip()


def split_pieces(text):
    parts = [p.strip() for p in SPLIT.split(text) if p.strip()]
    return [(p, bool(TERMINAL.search(p))) for p in parts]


def is_backchannel(text):
    toks = [t.lower().strip(".,!?؟،") for t in re.findall(r"[\w؀-ۿ'’-]+", clean_text(text))]
    toks = [t for t in toks if t]
    return bool(toks) and len(toks) <= 3 and all(t in BACKCHANNEL or FILLER_AR.match(an(t) or "x") or t in FILLER_LAT for t in toks)


def build_sentences(turns, words=None):
    """Turns (one speaker's engine fragments) -> sentences. Amal's pieces join across her fragments when <= AMAL_JOIN apart
    and Medi only back-channelled in between; Medi's pieces join until Amal really speaks (rule S5: he pauses to build).
    A sentence ends at . ? ! ؟ … . Times: word timings where they exist, else the turn split by characters, else the turn."""
    sents = []
    open_ = {"Amal": None, "Medi": None}
    wbys = defaultdict(list)
    for w in words or []:
        if w.get("spk") in ("Amal", "Medi") and (w.get("w") or "").strip():
            wbys[w["spk"]].append(w)
    starts = {k: [w["s"] for w in v] for k, v in wbys.items()}

    def close(spk):
        s = open_[spk]
        if s:
            s["text"] = re.sub(r"\s+", " ", " ".join(s.pop("parts"))).strip()
            sents.append(s)
            open_[spk] = None

    def spans_for(tr, pieces, t0, t1):
        if not pieces:
            return []
        spk = tr["who"]
        ws = []
        if spk in wbys:
            import bisect
            lo = bisect.bisect_left(starts[spk], t0 - 0.3)
            hi = bisect.bisect_right(starts[spk], t1 + 0.3)
            ws = wbys[spk][lo:hi]
        counts = [max(1, len(TOKEN.findall(p))) for p, _ in pieces]
        if ws and abs(len(ws) - sum(counts)) <= max(3, 0.3 * sum(counts)):
            out, i = [], 0
            scale = len(ws) / sum(counts)
            for c in counts:
                j = min(len(ws), max(i + 1, round(i + c * scale)))
                seg = ws[i:j] or ws[-1:]
                out.append((seg[0]["s"], seg[-1]["e"], "words", [(w["s"], w["e"]) for w in seg]))
                i = j
            return out
        if len(pieces) == 1:
            return [(t0, t1, "turn", None)]
        L = [max(1, len(p)) for p, _ in pieces]
        tot = sum(L)
        out, a = [], t0
        for l in L:
            b = a + (t1 - t0) * l / tot
            out.append((a, b, "turn-split", None))
            a = b
        return out

    T = [t for t in turns if t.get("who") in ("Amal", "Medi")]
    for i, tr in enumerate(T):
        who = tr["who"]
        other = "Medi" if who == "Amal" else "Amal"
        raw = tr.get("text") or ""
        hole = bool(HOLE.search(raw)) and not TOKEN.search(BRACKET.sub(" ", raw))   # "[in Arabic] winti kaman" has words
        noise = bool(NOISE.search(raw))
        text = clean_text(raw)
        t0 = float(tr["t"])
        nxt = T[i + 1]["t"] if i + 1 < len(T) else t0 + 3
        t1 = tr.get("end")
        t1 = float(t1) if t1 is not None and t1 >= t0 else min(max(nxt, t0 + 0.3), t0 + max(0.6, 0.07 * len(text)))
        pieces = split_pieces(text)
        if not pieces and not hole:
            continue
        bc = is_backchannel(text) and not hole
        o = open_[other]
        if o is not None:
            if bc and t0 - o["end"] <= (AMAL_JOIN if other == "Amal" else MEDI_JOIN):
                sents.append({"spk": who, "t": t0, "end": t1, "text": text, "mid": True, "hole": False, "noise": noise,
                              "time_src": "turn", "wt": None})
                continue
            close(other)
        mine = open_[who]
        if mine is not None and t0 - mine["end"] > (AMAL_JOIN if who == "Amal" else MEDI_JOIN):
            close(who)
        if hole and not pieces:
            close(who)
            sents.append({"spk": who, "t": t0, "end": t1, "text": "[speaking Arabic]", "mid": False, "hole": True,
                          "noise": noise, "time_src": "turn", "wt": None})
            continue
        spans = spans_for(tr, pieces, t0, t1)
        for (ptxt, term), (a, b, src, wt) in zip(pieces, spans):
            s = open_[who]
            if s is None:
                s = open_[who] = {"spk": who, "t": a, "end": b, "parts": [], "mid": False, "hole": hole, "noise": noise,
                                  "time_src": src, "wt": [] if wt is not None else None}
            s["parts"].append(ptxt)
            s["end"] = max(s["end"], b)
            s["hole"] = s["hole"] or hole
            s["noise"] = s["noise"] or noise
            if src != s["time_src"]:
                s["time_src"] = "mixed"
            if wt is not None and s["wt"] is not None:
                s["wt"].extend(wt)
            else:
                s["wt"] = None
            if term:
                close(who)
    close("Amal")
    close("Medi")
    sents.sort(key=lambda s: (s["t"], 0 if s["spk"] == "Amal" else 1))
    return sents


def missing_windows(turns, duration, window):
    """Stretches where one side's audio is missing: that side silent >= MISSING_GAP s while the other side has >= 15 turns,
    plus anything outside lessons.json talk.window."""
    out = []
    sp = defaultdict(list)
    for t in turns:
        if t.get("who") in ("Amal", "Medi") and clean_text(t.get("text")):
            sp[t["who"]].append(float(t["t"]))
    for who in ("Amal", "Medi"):
        other = sp["Medi" if who == "Amal" else "Amal"]
        pts = [0.0] + sorted(sp[who]) + [duration]
        for a, b in zip(pts, pts[1:]):
            if b - a >= MISSING_GAP and sum(1 for x in other if a < x < b) >= 15:
                out.append({"side": who, "from": round(a, 1), "to": round(b, 1), "source": "silence"})
    if window:
        w0, w1 = window
        for a, b in ((0.0, w0), (w1, duration)):
            if b - a > 30:
                # which side is missing there: the one with (almost) no turns
                ca = sum(1 for x in sp["Amal"] if a <= x < b)
                cm = sum(1 for x in sp["Medi"] if a <= x < b)
                side = "Medi" if cm < ca else "Amal"
                out.append({"side": side, "from": round(a, 1), "to": round(b, 1), "source": "talk.window"})
    return out


def in_missing(t, windows, side):
    return any(w["side"] == side and w["from"] - 1 <= t <= w["to"] + 1 for w in windows)


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def ar_words_norm(toks):
    return [an(x["w"]) if not x["lat"] else fold(x["w"].split("-")[-1]) for x in toks if x["s"] == "ar"]


# ------------------------------------------------------------------ reply reading
def reply_signals(reply_text, scored_text):
    """Signals 1-3 from Medi's reply text. Returns {name: {...}} (machine, not a guess: they are his own words)."""
    sig = {}
    rt = clean_text(reply_text)
    if not rt:
        return sig
    if RX_PRODUCTION.search(rt) and not RX_MEANING.search(rt.split("?")[0] if "?" in rt else rt):
        return sig
    first = SPLIT.split(rt)[0] if rt else ""
    if RX_REPEAT.match(first) or RX_REPEAT2.search(rt):
        sig["repeat_request"] = {"src": "machine", "guess": False, "said": rt[:160]}
    whats = [m.group(1) for m in RX_WHATS.finditer(rt)]
    whats_ar = any(AR.search(x) or any(t["s"] == "ar" for t in tokenize(x, bank())) for x in whats)
    if RX_MEANING.search(rt) or whats_ar:
        sig["meaning_question"] = {"src": "machine", "guess": False, "said": rt[:160], "kind": "ask"}
    elif RX_GUESS.search(rt):
        # he checks his own guess of the meaning: kept as evidence, but it labels the sentence 'unknown', not a breakdown
        sig["meaning_question"] = {"src": "machine", "guess": True, "said": rt[:160], "kind": "confirm-guess",
                                   "counts_as": "unknown"}
    if RX_DONT.search(rt) or (RX_DONT_SHORT.match(first) and (RX_TRANSLATE_PROMPT.search(scored_text or "") or
                                                             re.search(r"[؟?]\s*$", scored_text or ""))):
        sig["dont_understand"] = {"src": "machine", "guess": False, "said": rt[:160]}
    # an echo question: "بيهمنا؟" - his reply is 1-2 words, a question, and the words come from her sentence
    if not sig and re.search(r"[؟?]\s*$", first):
        bk = bank()
        rtoks = [x for x in tokenize(first, bk) if x["s"] == "ar"]
        stoks = set(ar_words_norm(tokenize(scored_text or "", bk)))
        if 1 <= len(rtoks) <= 2 and len(TOKEN.findall(first)) <= 3 and all((an(x["w"]) if not x["lat"] else fold(x["w"])) in stoks for x in rtoks) and \
                not all((an(x["w"]) in FN_AR or x["w"].lower() in LAT_FN) for x in rtoks):
            sig["repeat_request"] = {"src": "machine", "guess": True, "said": rt[:160], "kind": "echo"}
    return sig


CONFIRM_START = re.compile(r"^\W*(?:m+h+m+|mm-?hmm|uh-?huh|yes|yeah|exactly|correct|perfect|bravo|good|great|very good|right|"
                           r"ممتاز|أيوه|ايوه|ايوا|أيوا|صح|برافو|شاطر|عظيم|حلو|مظبوط|بالظبط|بالزبط|mumtaz|sa7|aywa|bravo)\b", re.I)


def understood_evidence(u, after_text):
    """Positive evidence that his reply answered HER sentence (research: 'a relevant content reply, or reuses the tutor's
    words'): she confirms next / he reuses one of her content words / an Arabic answer (2+ words) to her question or prompt /
    an English translation of her 'what does ... mean?'. None -> the sentence stays 'unknown'."""
    rep_ = u.get("reply") or {}
    rt = rep_.get("text") or ""
    bk = bank()
    rtoks = tokenize(rt, bk)
    r_ar = [x for x in rtoks if x["s"] == "ar"]
    r_en = [x for x in rtoks if x["s"] == "en"]
    if after_text and CONFIRM_START.search(clean_text(after_text)):
        return "she confirmed"
    mine = set()
    for x in r_ar:
        n = an(x["w"]) if not x["lat"] else fold(x["w"].split("-")[-1])
        if not ((not x["lat"] and n in FN_AR) or (x["lat"] and x["w"].lower() in LAT_FN)):
            mine.add(("n", n))
            ks, _ = bk.keys_lat(x["w"].split("-")[-1]) if x["lat"] else bk.keys_ar(n)
            mine.update(("k", k) for k in ks)
    hers = set()
    for t in u["tok"]:
        if t.get("f"):
            continue
        hers.add(("n", an(t["w"]) if not t.get("lat") else fold(t["w"].split("-")[-1])))
        hers.update(("k", k) for k in ([t["k"]] if t.get("k") else t.get("ks") or []))
    if mine & hers:
        return "reused her word"
    q = u["tags"]["q"] in ("wh", "yn") or u["tags"]["prompt"] == "meaning"
    if q and len(r_ar) >= 2:
        return "Arabic answer to her question"
    if u["tags"]["prompt"] == "meaning" and len(r_en) >= 2:
        return "English meaning for her 'what does it mean'"
    # he says her word's meaning in English: a gloss of one of her keyed words (words.json 'english') is in his reply
    en_words = {x["w"].lower().strip("'") for x in r_en}
    en_stems = {w[:5] for w in en_words if len(w) >= 3 and w not in ENGLISH_STOP}
    for t in u["tok"]:
        if t.get("f"):
            continue
        for k in ([t["k"]] if t.get("k") else t.get("ks") or []):
            gl = (bk.items.get(k) or {}).get("english") or ""
            for g in re.findall(r"[a-z]+", gl.lower()):
                if len(g) >= 3 and g not in ENGLISH_STOP and g[:5] in en_stems:
                    return "said her word's meaning in English"
    return None


RX_WHY = re.compile(r"(?i)(?:why|ليش|lesh|leesh|right\s*[?؟]|correct\s*[?؟]|صح\s*[?؟])")
QMARK_END = re.compile(r"[?؟]\s*$")


def is_bare(reply_text):
    """A bare aywa / ok / yes / mm / no reply (decision 3): unknown, not understood."""
    rt = clean_text(reply_text)
    toks = [t.lower().strip(".,!?؟،-") for t in re.findall(r"[\w؀-ۿ'’-]+", rt)]
    toks = [t for t in toks if t and not (t in FILLER_LAT or FILLER_AR.match(an(t) or "x"))]
    if not toks:
        return True
    phrase = " ".join(toks)
    if phrase in {"i see", "got it", "oh okay", "oh ok", "okay okay", "yeah yeah", "yes yes", "ok ok", "mm-hmm", "uh-huh",
                  "oh yeah", "yeah okay", "okay yeah", "yes yeah", "oh i see", "i got it", "that's right", "thats right"}:
        return True
    return len(toks) <= 2 and all(t in BACKCHANNEL or an(t) in BACKCHANNEL_N for t in toks)


def queried_words(reply_text):
    """The Arabic words his breakdown asks about (for the look-back): his reply's Arabic, minus signal/function words."""
    bk = bank()
    toks = tokenize(reply_text, bk)
    out = []
    for x in toks:
        if x["s"] != "ar":
            continue
        w = x["w"]
        if not x["lat"]:
            n = an(w)
            if n in FN_AR or n in ("يعني", "شو", "معنى"):
                continue
            out.append(("ar", n, bk.keys_ar(n)[0]))
        else:
            b = w.lower().split("-")[-1]
            if b in LAT_FN or b in ("ya3ni", "yani", "shu", "shoo"):
                continue
            out.append(("lat", fold(b), bk.keys_lat(b)[0]))
    return out


def sentence_has(sent_toks, q):
    """Does a sentence contain queried word q=(script, form, keys)? Arabic script by form (also without proclitics),
    Latin by fold, across scripts by Word Bank key."""
    kind, form, keys = q
    for t in sent_toks:
        if kind == "ar" and not t.get("lat"):
            n = an(t["w"])
            if n == form or n.endswith(form) and len(form) >= 3 and n[: len(n) - len(form)] in ("و", "ب", "ال", "بال", "وال", "لل", "ف"):
                return True
        if kind == "lat" and t.get("lat") and fold(t["w"].split("-")[-1]) == form:
            return True
        tk = [t["k"]] if t.get("k") else t.get("ks") or []
        if keys and tk and set(keys) & set(tk):
            return True
    return False


# ------------------------------------------------------------------ one lesson
def lesson_units(date, meta, bk, console, turns_doc, words=None):
    turns = turns_doc["turns"]
    duration = (meta.get("duration_min") or 0) * 60 or max(float(t["t"]) for t in turns) + 5
    window = (meta.get("talk") or {}).get("window")
    miss = missing_windows(turns, duration, window)
    sents = build_sentences(turns, words)
    start_local = meta.get("start_local")
    try:
        t_start = dt.datetime.fromisoformat(start_local) if start_local else None
    except ValueError:
        t_start = None
    chats = [t for t in turns if t.get("who") == "chat" and (t.get("typed_by") or "Amal") == "Amal"]
    for c in chats:
        c["_keys"] = set()
        c["_fold"] = set()
        for x in tokenize(c["text"], bk):
            if x["s"] == "ar":
                ks, _ = (bk.keys_lat(x["w"].split("-")[-1]) if x["lat"] else bk.keys_ar(an(x["w"])))
                c["_keys"].update(ks)
                c["_fold"].add(fold(x["w"].split("-")[-1]) if x["lat"] else an(x["w"]))
    # speech-only timeline for breaks and holes
    speech = sorted((float(t["t"]), float(t["end"]) if t.get("end") is not None else float(t["t"]) + 0.5, t["who"], t.get("text") or "")
                    for t in turns if t.get("who") in ("Amal", "Medi", "?"))
    gaps = [0.0]
    last_end = 0.0
    for a, b, _, _ in speech:
        if a - last_end >= LONG_GAP:
            gaps.append(a)
        last_end = max(last_end, b)
    hole_times = [a for a, b, w, tx in speech if HOLE.search(tx) or w == "?"]
    noise_times = [a for a, b, w, tx in speech if NOISE.search(tx)]
    medi_spans = [(a, b) for a, b, w, _ in speech if w == "Medi"]
    amal_spans = [(a, b) for a, b, w, _ in speech if w == "Amal"]

    # --- tokenise + tag every sentence (two passes: the second resolves unknown Latin words from the speaker's stretch)
    lat_known = []
    for s in sents:
        toks = tokenize(s["text"], bk)
        la = sum(1 for x in toks if x["lat"] and x["s"] == "ar" and not x.get("guess"))
        le = sum(1 for x in toks if x["lat"] and x["s"] == "en" and not x.get("guess"))
        lat_known.append((s["spk"], s["t"], la, le))
    for i, s in enumerate(sents):
        s["i"] = i
        la = sum(a for spk, t, a, e in lat_known if spk == s["spk"] and abs(t - s["t"]) <= 120)
        le = sum(e for spk, t, a, e in lat_known if spk == s["spk"] and abs(t - s["t"]) <= 120)
        s["latin_hint"] = la / (la + le) if (la + le) else None
        ar_n, en_n, toks = count_words(s["text"], bk, s["latin_hint"])
        s["ar_n"], s["en_n"], s["toks"] = ar_n, en_n, toks
        s["norm"] = ar_words_norm(toks)
    amal = [s for s in sents if s["spk"] == "Amal" and not s["mid"]]
    # repeat index + in-lesson recency (Amal's speech only)
    heard = defaultdict(list)
    topic_shift_at = [0.0] + [g for g in gaps[1:]]
    prev_amal = []
    for s in amal:
        s["repeat_index"], s["repeat_of"] = 1, None
        for p in prev_amal:
            if p["norm"] and s["norm"] and abs(len(p["norm"]) - len(s["norm"])) <= max(3, len(s["norm"])) and \
                    set(p["norm"]) & set(s["norm"]) and sim(p["norm"], s["norm"]) >= REPEAT_SIM:
                s["repeat_index"] += 1
                s["repeat_of"] = s["repeat_of"] or p["i"]
        prev_amal.append(s)
    # topic shifts: a break, or a transition word + little content overlap with the minute before vs after
    content_keys = []
    for s in amal:
        ks = set()
        for x in s["toks"]:
            if x["s"] == "ar":
                kk, _ = bk.keys_lat(x["w"].split("-")[-1]) if x["lat"] else bk.keys_ar(an(x["w"]))
                if kk and not ((not x["lat"] and an(x["w"]) in FN_AR) or (x["lat"] and x["w"].lower() in LAT_FN)):
                    ks.update(kk)
        content_keys.append((s["t"], ks))
    for j, s in enumerate(amal):
        if RX_TRANSITION.search(s["text"]):
            before = set().union(*[k for t, k in content_keys if s["t"] - 60 <= t < s["t"]] or [set()])
            after = set().union(*[k for t, k in content_keys if s["t"] <= t < s["t"] + 60] or [set()])
            if before and after and len(before & after) / len(before | after) < 0.1:
                topic_shift_at.append(s["t"])
    topic_shift_at.sort()

    def ctx_tags(s, side):
        tg = {}
        tg["secs"] = round(max(0.0, s["end"] - s["t"]), 2)
        n_all = s["ar_n"] + s["en_n"]
        dur = s["end"] - s["t"]
        tg["wps"] = round(n_all / dur, 2) if dur > 0.2 and n_all else None
        tg["rate_src"] = s["time_src"]
        wt = s.get("wt")
        if wt and len(wt) >= 2:
            pauses = [b[0] - a[1] for a, b in zip(wt, wt[1:]) if b[0] - a[1] >= 0.25]
            art = dur - sum(pauses)
            runs, r = [], 1
            for a, b in zip(wt, wt[1:]):
                if b[0] - a[1] >= 0.25:
                    runs.append(r)
                    r = 1
                else:
                    r += 1
            runs.append(r)
            tg["pause"] = {"n": len(pauses), "total_s": round(sum(pauses), 2), "max_s": round(max(pauses), 2) if pauses else 0,
                           "mean_run": round(sum(runs) / len(runs), 2), "artic_wps": round(len(wt) / art, 2) if art > 0.2 else None}
        else:
            tg["pause"] = None
        tg["minute"] = round(s["t"] / 60, 1)
        g = max([x for x in gaps if x <= s["t"]] or [0.0])
        tg["min_since_break"] = round((s["t"] - g) / 60, 1)
        if t_start:
            loc = t_start + dt.timedelta(seconds=s["t"])
            tg["local_time"] = loc.strftime("%H:%M")
            tg["hour"] = round(loc.hour + loc.minute / 60, 2)
        else:
            tg["local_time"] = tg["hour"] = None
        ts = max([x for x in topic_shift_at if x <= s["t"]] or [0.0])
        tg["turns_since_topic_shift"] = sum(1 for x in sents if ts <= x["t"] < s["t"] and not x["mid"])
        # audio trouble proxies
        other = medi_spans if side == "listen" else amal_spans
        tg["overlap_s"] = round(sum(max(0.0, min(b, s["end"]) - max(a, s["t"])) for a, b in other if a < s["end"] and b > s["t"]), 2)
        tg["near_hole"] = any(abs(h - s["t"]) <= 10 for h in hole_times)
        tg["noise_tag"] = s.get("noise") or any(abs(h - s["t"]) <= 10 for h in noise_times)
        tg["near_missing_side"] = any(w["from"] - 30 <= s["t"] <= w["to"] + 30 for w in miss)
        return tg

    def recency(s):
        """Per content word: heard from Amal earlier in this lesson (count, seconds since)."""
        first_time = 0
        since = []
        for x in s["toks"]:
            if x["s"] != "ar":
                continue
            n = an(x["w"]) if not x["lat"] else fold(x["w"].split("-")[-1])
            fn = (not x["lat"] and n in FN_AR) or (x["lat"] and x["w"].lower() in LAT_FN)
            h = [t for t in heard[n] if t < s["t"] - 0.5]
            x["_heard"] = len(h)
            if not fn:
                if not h:
                    first_time += 1
                else:
                    since.append(s["t"] - h[-1])
        return {"new_in_lesson": first_time, "min_since_heard_s": round(min(since), 1) if since else None,
                "median_since_heard_s": round(sorted(since)[len(since) // 2], 1) if since else None}

    def chat_near(s):
        best = None
        for c in chats:
            d = float(c["t"]) - s["t"]
            if -20 <= d <= (s["end"] - s["t"]) + 30:
                ov = 0
                for x in s["toks"]:
                    if x["s"] != "ar":
                        continue
                    ks, _ = bk.keys_lat(x["w"].split("-")[-1]) if x["lat"] else bk.keys_ar(an(x["w"]))
                    f = fold(x["w"].split("-")[-1]) if x["lat"] else an(x["w"])
                    if (ks and set(ks) & c["_keys"]) or f in c["_fold"]:
                        ov += 1
                if best is None or ov > best["overlap"] or (ov == best["overlap"] and abs(d) < abs(best["dt"])):
                    best = {"dt": round(d, 1), "text": c["text"][:140], "overlap": ov}
        return best

    # recency must be computed in time order over ALL Amal speech (not only scored sentences)
    for s in sents:
        if s["spk"] == "Amal" and not s["mid"]:
            s["_recency"] = recency(s)
            for x in s["toks"]:
                if x["s"] == "ar":
                    n = an(x["w"]) if not x["lat"] else fold(x["w"].split("-")[-1])
                    heard[n].append(s["t"])
        elif s["spk"] == "Medi" and not s["mid"]:
            s["_recency"] = recency(s)

    def make_unit(s, side):
        tags, tok_out, rules = sentence_tags(s["toks"], s["text"], bk)
        tags.update(ctx_tags(s, side))
        tags.update(s.get("_recency") or {})
        if side == "listen":
            tags["repeat_index"] = s.get("repeat_index", 1)
            tags["repeat_of"] = sid(date, "listen", sents[s["repeat_of"]]["t"]) if s.get("repeat_of") is not None else None
            ch = chat_near(s)
            tags["chat"] = ch
            tags["typed_in_chat"] = bool(ch and ch["overlap"] >= 1)
        tags["en_share"] = round(s["en_n"] / (s["ar_n"] + s["en_n"]), 2) if (s["ar_n"] + s["en_n"]) else None
        return {"id": sid(date, side, s["t"]), "side": side, "t": round(s["t"], 2), "end": round(s["end"], 2),
                "text": s["text"], "n": s["ar_n"], "tok": tok_out, "tags": tags, "rules": rules}

    def wordset(x):
        out = set()
        for t in x["toks"]:
            if t["s"] != "ar":
                continue
            n = an(t["w"]) if not t["lat"] else fold(t["w"].split("-")[-1])
            if (not t["lat"] and n in FN_AR) or (t["lat"] and t["w"].lower() in LAT_FN):
                continue
            out.add(("n", n))
            ks, _ = bk.keys_lat(t["w"].split("-")[-1]) if t["lat"] else bk.keys_ar(n)
            out.update(("k", k) for k in ks)
        return out

    def her_echo(s):
        """She repeats / recasts / corrects HIS last words: feedback on his speech, not new input to understand.
        (a) her content words all come from his last turns (same word, a near spelling, or the same Word Bank key);
        (b) a short 'No, X' right after him."""
        k = s["i"] - 1
        while k >= 0 and (sents[k]["mid"] or (sents[k]["spk"] == "Amal" and all(
                (an(t["w"]) if not t["lat"] else t["w"].lower()) in FEEDBACK for t in sents[k]["toks"] if t["s"] == "ar"))):
            k -= 1
        if k < 0 or sents[k]["spk"] != "Medi" or s["t"] - sents[k]["end"] > 10:
            return False
        if RX_NEG_START.search(s["text"]) and s["ar_n"] <= 4 and s["t"] - sents[k]["end"] <= 6:
            return True
        his = set()
        j = k
        while j >= 0 and sents[j]["spk"] == "Medi" and sents[k]["t"] - sents[j]["t"] <= 20:
            his |= wordset(sents[j])
            j -= 1
        mine_n = [w for w in s["norm"] if w not in FN_AR and w not in LAT_FN]
        if not mine_n or len(mine_n) > 3:
            return False
        his_n = [w for kind, w in his if kind == "n"]
        his_k = {w for kind, w in his if kind == "k"}
        for t in s["toks"]:
            if t["s"] != "ar":
                continue
            n = an(t["w"]) if not t["lat"] else fold(t["w"].split("-")[-1])
            if n not in mine_n:
                continue
            ks, _ = bk.keys_lat(t["w"].split("-")[-1]) if t["lat"] else bk.keys_ar(n)
            if not (n in his_n or any(sim(n, h) >= 0.75 for h in his_n) or (set(ks) & his_k)):
                return False
        return True

    def qualifies(s):
        if s["spk"] != "Amal" or s["mid"] or s["hole"] or s["ar_n"] < 1 or mostly_english(s["ar_n"], s["en_n"]):
            return False
        arw = [an(x["w"]) if not x["lat"] else x["w"].lower() for x in s["toks"] if x["s"] == "ar"]
        if all(w in FEEDBACK for w in arw):
            return False
        if her_echo(s):
            return False
        return not in_missing(s["t"], miss, "Medi")

    # --- exchanges
    seq = [s for s in sents if not s["mid"]]
    runs = []
    for s in seq:
        if runs and runs[-1]["spk"] == s["spk"]:
            runs[-1]["s"].append(s)
        else:
            runs.append({"spk": s["spk"], "s": [s]})
    units = {}
    order = []

    def unit_for(s, how):
        u = units.get(s["i"])
        if u is None:
            u = make_unit(s, "listen")
            u.update({"unit": how, "label": None, "signals": {}, "reply": None, "lookback": None, "scored": True})
            units[s["i"]] = u
            order.append(s["i"])
        return u

    mid_medi = [s for s in sents if s["mid"] and s["spk"] == "Medi"]
    lesson_fixes = corrections_for(date, turns_doc, [])       # the lesson audit's grammar + word fixes (not listening misses)
    amal_idx = {s["i"]: k for k, s in enumerate(amal)}
    for j, run in enumerate(runs):
        if run["spk"] != "Amal":
            continue
        floor = run["s"]
        reply = runs[j + 1] if j + 1 < len(runs) and runs[j + 1]["spk"] == "Medi" else None
        after = runs[j + 2] if j + 2 < len(runs) and runs[j + 2]["spk"] == "Amal" else None
        # rescue: her Arabic sentence, >= 3 s of Medi silence, then she switches to English or rephrases (unasked)
        for k, si in enumerate(floor[:-1]):
            sj = floor[k + 1]
            if not qualifies(si) or "..." in si["text"] or "…" in si["text"] or re.search("[-—]", si["text"])                     or RX_NEG_START.search(sj["text"]):
                continue                        # her self-repair, or 'No, ...' = she corrects him: not a rescue
            gap = sj["t"] - si["end"]
            if gap < RESCUE_GAP or any(si["end"] < m["t"] < sj["t"] for m in mid_medi):
                continue
            new_ar = {w for w in sj["norm"] if w not in FN_AR and w not in LAT_FN} - set(si["norm"])
            eng = mostly_english(sj["ar_n"], sj["en_n"]) and sj["en_n"] >= 2 and bool(RX_RESCUE_EN.search(sj["text"])) and not new_ar
            reph = sim(si["norm"], sj["norm"]) >= REPHRASE_SIM
            if eng or reph:
                u = unit_for(si, "rescue")
                u["signals"]["rescue"] = {"src": "machine", "guess": True, "gap_s": round(gap, 1),
                                          "kind": "english" if eng else "rephrase", "next": sj["text"][:140]}
        if reply is None:
            continue
        cands = [s for s in floor if qualifies(s)]
        if not cands:
            continue
        S = cands[-1]
        u = unit_for(S, "last-before-reply")
        rtext = " ".join(x["text"] for x in reply["s"][:3])
        u["reply"] = {"t": round(reply["s"][0]["t"], 2), "end": round(reply["s"][min(2, len(reply["s"]) - 1)]["end"], 2),
                      "text": rtext[:300], "hole": any(x["hole"] for x in reply["s"][:3]),
                      "latency_s": round(reply["s"][0]["t"] - S["end"], 2)}
        u["_after"] = after["s"][0]["text"] if after is not None and after["s"][0]["t"] - reply["s"][-1]["end"] <= 10 else None
        sig = reply_signals(rtext, S["text"])
        # a short question back ("Alma?", "Qwaad?") and she then says her sentence again: he did not catch it
        first_r = reply["s"][0]
        if not sig and after is not None and len(TOKEN.findall(first_r["text"])) <= 3 and QMARK_END.search(first_r["text"])                 and first_r["t"] >= S["end"] - 0.2 and not RX_WHY.search(first_r["text"]) and not CONFIRM_START.search(after["s"][0]["text"]):
            n1 = after["s"][0]
            s_content = {w for w in S["norm"] if w not in FN_AR and w not in LAT_FN}
            if n1["t"] - reply["s"][-1]["end"] <= 8 and (sim(S["norm"], n1["norm"]) >= REPHRASE_SIM or s_content & set(n1["norm"])):
                sig["repeat_request"] = {"src": "machine", "guess": True, "said": first_r["text"][:160],
                                         "kind": "short question, then she said it again"}
        # he only says her words back (a drill echo): no sign of meaning, like a bare reply
        r_words = set().union(*[wordset(x) for x in reply["s"][:3]]) if reply["s"] else set()
        r_en = sum(x["en_n"] for x in reply["s"][:3])
        u["_echo_reply"] = bool(r_words) and r_en <= 1 and r_words <= (wordset(S) | {("n", w) for w in S["norm"]})             and not QMARK_END.search(S["text"])            # جاهز؟ -> جاهز. is an answer, not an echo
        # signal 5: he answered something else and she corrects the MEANING (not grammar)
        if after is not None and not re.search(r"[؟?]\s*$", rtext.strip()) and not sig:
            n1 = after["s"][0]
            if n1["t"] - reply["s"][-1]["end"] <= 10 and RX_NEG_START.search(n1["text"]):
                look = " ".join(x["text"] for x in after["s"][:2])
                lk = ar_words_norm(tokenize(look, bk))
                content = [w for w in S["norm"] if w not in FN_AR and w not in LAT_FN]
                ties = set(lk) & set(content)
                gloss = RX_GLOSS.search(look)
                grammar = any(reply["s"][0]["t"] - 3 <= c["t"] <= n1["end"] + 5 or
                              (c.get("recast_t") and reply["s"][0]["t"] - 3 <= c["recast_t"] <= n1["end"] + 5) for c in console) or \
                    any(reply["s"][0]["t"] - 3 <= c["t"] <= n1["end"] + 5 for c in lesson_fixes)
                # he answered in Arabic: her "No" is usually about his form -> it takes a gloss to call it a meaning fix;
                # he answered in English (a translation): her "No" + her own words again is a meaning fix
                r_ar = sum(x["ar_n"] for x in reply["s"][:3])
                r_en = sum(x["en_n"] for x in reply["s"][:3])
                meaning_fix = bool(ties) and (bool(gloss) if r_ar > r_en else True)
                if meaning_fix and not grammar:
                    sig["wrong_answer"] = {"src": "machine", "guess": True, "said": n1["text"][:160]}
        u["signals"].update(sig)
        # look-back: the breakdown asks about a word from an earlier sentence -> charge that one
        if any(k in sig and sig[k].get("counts_as") != "unknown" for k in ("repeat_request", "meaning_question", "dont_understand")):
            qs = queried_words(rtext)
            if qs and not any(sentence_has(u["tok"], q) for q in qs):
                k0 = amal_idx.get(S["i"], 0)
                for back in range(1, LOOKBACK_N + 1):
                    if k0 - back < 0:
                        break
                    E = amal[k0 - back]
                    if reply["s"][0]["t"] - E["t"] > LOOKBACK_S:
                        break
                    if E["ar_n"] < 1:
                        continue
                    etok = sentence_tags(E["toks"], E["text"], bk)[1]
                    if any(sentence_has(etok, q) for q in qs):
                        ue = unit_for(E, "lookback")
                        for kname in ("repeat_request", "meaning_question", "dont_understand"):
                            if kname in sig:
                                ue["signals"][kname] = dict(sig[kname], charged_from=u["id"])
                                u["signals"].pop(kname, None)
                        ue["lookback"] = {"from": u["id"], "words": [q[1] for q in qs]}
                        u["lookback"] = {"to": ue["id"], "words": [q[1] for q in qs]}
                        break

    # hand-audit listening misses (docs/data/lessons/<date>.json vocab_errors, read by hand): strongest evidence
    for v in (turns_doc.get("vocab_errors") or []):
        why = (v.get("why") or "") + " " + (v.get("english") or "")
        if not RX_LISTEN_MISS.search(why) or RX_PRODUCTION_WHY.search(why):
            continue
        tv = float(v.get("t") or 0)
        target = an(v.get("arabic") or "")
        best = None
        for s in reversed(amal):
            if s["t"] > tv + 2:
                continue
            if tv - s["t"] > 60:
                break
            if s["ar_n"] < 1 or s["hole"] or in_missing(s["t"], miss, "Medi"):
                continue
            if target and any(an(x["w"]).endswith(target) or target.endswith(an(x["w"])) and len(an(x["w"])) >= 3
                              for x in s["toks"] if x["s"] == "ar" and not x["lat"]):
                best = s
                break
        if best is not None and not mostly_english(best["ar_n"], best["en_n"]):
            u = unit_for(best, "hand")
            u["signals"]["hand_audit"] = {"src": "hand", "guess": False, "id": v.get("audit_uid") or v.get("event_id"),
                                          "kind": v.get("kind"), "why": (v.get("why") or "")[:220], "word": v.get("arabic")}

    listen = []
    for i in sorted(order, key=lambda k: sents[k]["t"]):
        u = units[i]
        real = [k for k, v in u["signals"].items() if v.get("counts_as") != "unknown"]
        if real:
            u["label"] = "breakdown"
        elif u["signals"]:
            if u.get("_after") and CONFIRM_START.search(clean_text(u["_after"])):
                u["label"] = "understood"
                u["evidence"] = "his guess of the meaning, and she confirmed it"
            else:
                u["label"] = "unknown"
                u["why_unknown"] = "he checked a guess of the meaning"
        elif u["reply"] is None:
            u["label"] = "unknown"
            u["why_unknown"] = "no reply"
        elif u["reply"]["hole"] or is_bare(u["reply"]["text"]):
            u["label"] = "unknown"
            u["why_unknown"] = "reply not transcribed" if u["reply"]["hole"] else "bare reply (aywa/ok/yes/mm)"
            # تمام to كيفك is an answer, not a nod
            if not u["reply"]["hole"] and re.search(r"كيف|kif|keef|شلون", u["text"]) and \
                    re.search(r"تمام|tamam|منيح|mni7|الحمد", u["reply"]["text"]):
                u["label"] = "understood"
                u["evidence"] = "answered how-are-you"
                u.pop("why_unknown", None)
        elif u.get("lookback") and u["lookback"].get("to"):
            u["label"] = "unknown"
            u["why_unknown"] = "his question was about an earlier sentence"
        elif u.get("_echo_reply"):
            u["label"] = "unknown"
            u["why_unknown"] = "he only said her words back (no sign of meaning)"
        else:
            # decision 3: a content reply with no signal = understood (only a bare reply is unknown). The evidence level is
            # kept so the page can show 'strong' vs 'content reply only' (hand check 2026-09-27: see the spec).
            u["label"] = "understood"
            u["evidence"] = understood_evidence(u, u.pop("_after", None)) or "content reply only"
            # a one-word remark of hers (often a recast or an engine garble) + a reply that shows nothing = no evidence
            if u["evidence"] == "content reply only" and u["n"] <= 1 and u["tags"]["q"] == "statement" and not u["tags"]["prompt"]:
                u["label"] = "unknown"
                u["why_unknown"] = "one-word remark; his reply does not show he took it in"
        u.pop("_after", None)
        u.pop("_echo_reply", None)
        listen.append(u)

    # --- speaking: every Medi sentence with Arabic
    corr = corrections_for(date, turns_doc, console)
    speak = []
    prev_amal_s = None
    for s in sents:
        if s["spk"] == "Amal" and not s["mid"]:
            prev_amal_s = s
            continue
        if s["spk"] != "Medi" or s["mid"] or s["hole"] or s["ar_n"] < 1:
            continue
        u = make_unit(s, "speak")
        u["scored"] = True
        why = None
        if mostly_english(s["ar_n"], s["en_n"]):
            why = "mostly English"
        elif in_missing(s["t"], miss, "Amal"):
            why = "Amal's side missing (no correction could be seen)"
        elif prev_amal_s is not None and s["t"] - prev_amal_s["end"] <= 10 and s["norm"] and prev_amal_s["norm"] and \
                (sim(s["norm"], prev_amal_s["norm"]) >= 0.8 or set(s["norm"]) <= set(prev_amal_s["norm"])):
            why = "echo of Amal's sentence"
        if why:
            u["scored"] = False
            u["why_not"] = why
        u["corrections"] = []
        speak.append(u)
    # attach each correction to the Medi sentence it was about
    for c in corr:
        best, bs = None, -1
        for u in speak:
            if not (u["t"] - 3 <= c["t"] <= u["end"] + 2 or abs(u["t"] - c["t"]) <= 6):
                continue
            sc = sim(ar_words_norm(tokenize(c.get("said") or "", bk)), [x["n"] for x in u["tok"]]) + (1 if u["t"] - 1.5 <= c["t"] <= u["end"] + 1.5 else 0)
            if sc > bs:
                best, bs = u, sc
        if best is not None:
            best["corrections"].append({k: c[k] for k in ("id", "src", "rule", "signal", "kind") if c.get(k)})
    for u in speak:
        if not u["scored"]:
            u["label"] = "unknown"
        else:
            u["label"] = "corrected" if u["corrections"] else "success"
    return listen, speak, miss, len(amal)


def corrections_for(date, turns_doc, console):
    out, seen = [], set()
    for c in console:
        out.append({"id": c.get("id"), "t": float(c["t"]), "said": c.get("said"), "src": "grammar-console", "rule": c.get("bucket"),
                    "signal": c.get("signal"), "kind": "grammar"})
        seen.add(c.get("id"))
    for g in turns_doc.get("grammar_errors") or []:
        if g.get("id") in seen or g.get("t") is None:
            continue
        out.append({"id": g.get("id"), "t": float(g["t"]), "said": g.get("said"), "src": "lesson-grammar", "rule": g.get("bucket"),
                    "signal": g.get("signal"), "kind": "grammar"})
    for v in turns_doc.get("vocab_errors") or []:
        why = (v.get("why") or "") + " " + (v.get("english") or "")
        if RX_LISTEN_MISS.search(why) and not RX_PRODUCTION_WHY.search(why):
            continue                                    # a listening miss, not a slip in his sentence
        if v.get("t") is None:
            continue
        out.append({"id": v.get("audit_uid") or v.get("event_id"), "t": float(v["t"]), "said": v.get("said"),
                    "src": "lesson-vocab", "rule": None, "signal": v.get("signal") or v.get("kind"),
                    "kind": "word-supplied" if v.get("kind") == "asked" else "word"})
    return out


def sid(date, side, t):
    return f"{date}:{'L' if side == 'listen' else 'S'}:{int(round(t * 10))}"


# ------------------------------------------------------------------ ladder, effects, recipe, boost
def ladder(units, ok_label, bad_label):
    """Decision 2: good at N = >= 80% ok on the last 20 scored sentences of length N, spread over >= 2 lessons.
    Current N = highest good length with no failed length below it (a length with < 20 scored sentences does not block)."""
    by = defaultdict(list)
    for u in units:
        if u.get("scored", True) and u["label"] in (ok_label, bad_label) and u["n"] >= 1:
            by[u["n"]].append(u)
    rungs = []
    for n in sorted(by):
        xs, per = [], Counter()
        for u in sorted(by[n], key=lambda u: (u["date"], u["t"]), reverse=True):
            if per[u["date"]] < LADDER_PER_LESSON:
                xs.append(u)
                per[u["date"]] += 1
            if len(xs) == LADDER_LAST:
                break
        ok = sum(1 for u in xs if u["label"] == ok_label)
        les = sorted({u["date"] for u in xs})
        pct = ok / len(xs) if xs else None
        if len(xs) < LADDER_LAST:
            status = "not enough data"
        elif pct >= LADDER_PCT and len(les) >= LADDER_LESSONS:
            status = "good"
        elif pct >= LADDER_PCT:
            status = "one lesson only"
        else:
            status = "not yet"
        rungs.append({"len": n, "n_total": len(by[n]), "n_last": len(xs), "ok": ok, "pct": round(100 * pct, 1) if pct is not None else None,
                      "lessons": len(les), "status": status})
    N = 0
    for r in rungs:
        if r["status"] == "good":
            N = r["len"]
        elif r["status"] in ("not yet", "one lesson only"):
            break
    at = next((r for r in rungs if r["len"] == N), None)
    tgt = next((r for r in rungs if r["len"] == N + 1), None)
    return {"N": N, "target": N + 1, "pct_at_N": at["pct"] if at else None, "pct_at_target": tgt["pct"] if tgt else None,
            "n_at_target": tgt["n_last"] if tgt else 0, "rungs": rungs}


def features(u, cut):
    """Binary tags used for effects (a tag = True/False per sentence). cut = global cut points computed from the data."""
    tg = u["tags"]
    f = {}
    ten = set(tg["tense"])
    f["tense_past"] = "past" in ten
    f["tense_future"] = "future" in ten
    f["tense_command"] = "command" in ten
    f["tense_progressive"] = "progressive" in ten
    f["tense_none"] = ten == {"none"}
    f["clitic_2plus"] = tg["cl_max"] >= 2
    f["clitic_any"] = tg["cl_max"] >= 1
    f["fn_clitic_share_high"] = (tg["fn_or_clitic_share"] or 0) >= 0.5
    f["noun_share_high"] = (tg["noun_share"] or 0) >= 0.4
    neg = set(tg["neg"])
    f["neg_any"] = neg != {"none"}
    f["neg_ma_sh"] = "ma_sh" in neg
    f["neg_mish"] = "mish" in neg
    f["neg_ma"] = "ma" in neg
    f["non_first_person"] = bool(tg["non_first"])
    f["derived_verb_form"] = any(v["form"] not in ("I", None) for v in tg["verb_forms"])
    f["new_root_verb"] = any(not v["root_in_bank_other"] for v in tg["verb_forms"] if v["form"] not in ("I", None))
    f["question_yn"] = tg["q"] == "yn"
    f["question_wh"] = tg["q"] == "wh"
    f["meaning_prompt"] = tg["prompt"] == "meaning"
    f["fast"] = tg["wps"] is not None and tg["wps"] >= cut["wps_p75"]
    f["has_long_pause"] = bool(tg["pause"] and tg["pause"]["max_s"] >= 0.5)
    f["english_inside"] = tg["en_tokens"] >= 1
    f["english_clause"] = bool(tg["en_clause"])
    f["idiom"] = bool(tg["idioms"])
    f["colloquial_fn"] = tg["colloq_fn"] >= 1
    f["emphatic_dense"] = tg["emph_density"] is not None and tg["emph_density"] >= cut["emph_p75"]
    f["late_in_lesson"] = tg["minute"] >= 40
    f["long_since_break"] = tg["min_since_break"] >= 20
    f["just_after_topic_shift"] = tg["turns_since_topic_shift"] <= 3
    f["afternoon_late"] = tg.get("hour") is not None and tg["hour"] >= 15
    f["overlap"] = tg["overlap_s"] >= 0.3
    f["audio_trouble"] = bool(tg["near_hole"] or tg["noise_tag"] or tg["near_missing_side"]) or tg["overlap_s"] >= 0.3
    f["long_syllables"] = tg["syll"] >= cut["syll_p75"]
    if u["side"] == "listen":
        f["repeat"] = tg["repeat_index"] >= 2
        f["new_word_in_lesson"] = (tg.get("new_in_lesson") or 0) >= 1
        f["two_plus_new_words"] = (tg.get("new_in_lesson") or 0) >= 2
        f["typed_in_chat"] = bool(tg.get("typed_in_chat"))
    for r in u["rules"]:
        f["rule_" + r] = True
    return f


FEATURE_LABELS = {
    "tense_past": "past tense", "tense_future": "future (رح)", "tense_command": "command form", "tense_progressive": "عم (right now)",
    "tense_none": "no verb", "clitic_2plus": "a word with 2+ endings", "clitic_any": "any word with an ending",
    "fn_clitic_share_high": "half or more little words / endings", "noun_share_high": "noun-heavy",
    "neg_any": "negation", "neg_ma_sh": "ما…ش", "neg_mish": "مش", "neg_ma": "ما (alone)", "non_first_person": "you / he / she forms",
    "derived_verb_form": "derived verb form (II, V, VII…)", "new_root_verb": "derived form of a root not elsewhere in the bank",
    "question_yn": "yes/no question", "question_wh": "wh- question", "meaning_prompt": "'what does … mean?' quiz",
    "fast": "fast speech (top quarter)", "has_long_pause": "a pause ≥ 0.5 s inside (word-timed lessons)",
    "english_inside": "English word inside", "english_clause": "an English clause inside", "idiom": "fixed phrase / idiom",
    "colloquial_fn": "dialect-only little word", "emphatic_dense": "many ص ض ط ظ ح ع ق غ خ", "late_in_lesson": "after minute 40",
    "long_since_break": "20+ min since a break", "just_after_topic_shift": "just after a topic change",
    "afternoon_late": "after 15:00 local", "overlap": "both talking at once", "audio_trouble": "audio trouble nearby",
    "long_syllables": "many syllables (top quarter)", "repeat": "she said it before (repeat)",
    "new_word_in_lesson": "a word not heard earlier this lesson", "two_plus_new_words": "2+ words not heard earlier this lesson",
    "typed_in_chat": "also typed in the Meet chat",
}


def len_band(n):
    return "1-2" if n <= 2 else "3-4" if n <= 4 else "5-6" if n <= 6 else "7-9" if n <= 9 else "10+"


def mh_effects(units, ok_label, bad_label, cut):
    """Per-tag effect = Mantel-Haenszel risk difference in % understood (tag vs no tag), stratified by lesson x length band.
    JS can recompute it from the per-stratum counts kept in 'strata'. Shown only when >= 30 sentences on each side."""
    rows = [u for u in units if u.get("scored", True) and u["label"] in (ok_label, bad_label)]
    feats = [(u, features(u, cut)) for u in rows]
    names = sorted({k for _, f in feats for k in f})
    out = []
    for name in names:
        strata = defaultdict(lambda: [0, 0, 0, 0])      # ok_with, n_with, ok_without, n_without
        for u, f in feats:
            key = u["date"] + "|" + len_band(u["n"])
            ok = u["label"] == ok_label
            if f.get(name):
                strata[key][0] += ok
                strata[key][1] += 1
            else:
                strata[key][2] += ok
                strata[key][3] += 1
        n1 = sum(v[1] for v in strata.values())
        n0 = sum(v[3] for v in strata.values())
        ok1 = sum(v[0] for v in strata.values())
        ok0 = sum(v[2] for v in strata.values())
        num = den = var = 0.0
        for a, b, c, d in strata.values():
            if b and d:
                w = b * d / (b + d)
                p1, p0 = a / b, c / d
                num += w * (p1 - p0)
                den += w
                var += w * w * (p1 * (1 - p1) / b + p0 * (1 - p0) / d)
        rd = num / den if den else None
        se = math.sqrt(var) / den if den else None
        out.append({
            "tag": name, "label": FEATURE_LABELS.get(name) or (("rule " + name[5:]) if name.startswith("rule_") else name),
            "n_with": n1, "n_without": n0, "pct_with": round(100 * ok1 / n1, 1) if n1 else None,
            "pct_without": round(100 * ok0 / n0, 1) if n0 else None,
            "rd_mh": round(100 * rd, 1) if rd is not None else None,
            "ci95": [round(100 * (rd - 1.96 * se), 1), round(100 * (rd + 1.96 * se), 1)] if rd is not None and se is not None else None,
            "show": n1 >= EFFECT_FLOOR and n0 >= EFFECT_FLOOR and rd is not None,
            "strata": {k: v for k, v in strata.items()},
        })
    out.sort(key=lambda e: (not e["show"], e["rd_mh"] if e["rd_mh"] is not None else 999))
    return out


def ridge_logit(units, ok_label, bad_label, cut, names, lam=1.0):
    """All tags at once (so حكيتلك's clitics / past / person are separated): L2 logistic regression with lesson fixed effects
    and length. Precomputed here; the page shows it as 'after the other tags'. Returns {tag: odds ratio}."""
    try:
        import numpy as np
    except ImportError:
        return {}
    rows = [u for u in units if u.get("scored", True) and u["label"] in (ok_label, bad_label)]
    if len(rows) < 60 or not names:
        return {}
    dates = sorted({u["date"] for u in rows})
    cols = list(names) + ["len"] + ["lesson_" + d for d in dates[1:]]
    X = np.zeros((len(rows), len(cols) + 1))
    y = np.zeros(len(rows))
    lens = np.array([u["n"] for u in rows], float)
    mu, sd = lens.mean(), lens.std() or 1.0
    for i, u in enumerate(rows):
        f = features(u, cut)
        X[i, 0] = 1
        for j, nme in enumerate(names):
            X[i, j + 1] = 1.0 if f.get(nme) else 0.0
        X[i, len(names) + 1] = (u["n"] - mu) / sd
        if u["date"] != dates[0]:
            X[i, len(names) + 2 + dates[1:].index(u["date"])] = 1
        y[i] = 1.0 if u["label"] == ok_label else 0.0
    beta = np.zeros(X.shape[1])
    P = lam * np.eye(X.shape[1])
    P[0, 0] = 0
    for _ in range(50):
        z = X @ beta
        p = 1 / (1 + np.exp(-z))
        W = p * (1 - p)
        g = X.T @ (y - p) - P @ beta
        H = X.T @ (X * W[:, None]) + P
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-6:
            break
    return {nme: round(float(math.exp(beta[j + 1])), 2) for j, nme in enumerate(names)}


RECIPE_LEVERS = [
    # (feature, advice when it costs him, default text)
    ("tense_past", "mostly present", "mostly present"),
    ("tense_future", "mostly present", None),
    ("clitic_2plus", "≤1 ending per word", "≤1 ending per word"),
    ("new_word_in_lesson", "≤1 new word", "≤1 new word"),
    ("fast", "normal speed", "normal speed"),
    ("neg_any", "positive (no ما…ش)", None),
    ("non_first_person", "mostly I / we forms", None),
    ("derived_verb_form", "basic verb forms", None),
    ("idiom", "no idioms", None),
    ("colloquial_fn", "few dialect-only little words", None),
    ("question_wh", "yes/no questions over wh- questions", None),
    ("english_clause", "keep English out of the sentence", None),
]


def recipe(ladder_listen, effects):
    eff = {e["tag"]: e for e in effects}
    parts = [f"{ladder_listen['target']} words"]
    items = [{"lever": "length", "advice": f"{ladder_listen['target']} Arabic words", "basis": "ladder",
              "n": ladder_listen["n_at_target"], "pct": ladder_listen["pct_at_target"]}]
    seen_adv = set()
    for feat, adv, default in RECIPE_LEVERS:
        e = eff.get(feat)
        if e and e["show"] and e["rd_mh"] is not None and e["rd_mh"] <= -5:
            if adv in seen_adv:
                continue
            seen_adv.add(adv)
            items.append({"lever": feat, "advice": adv, "basis": "data", "n_with": e["n_with"], "pct_with": e["pct_with"],
                          "pct_without": e["pct_without"], "rd_mh": e["rd_mh"]})
            parts.append(adv)
        elif default and default not in seen_adv:
            seen_adv.add(default)
            items.append({"lever": feat, "advice": default, "basis": "default (not enough data, or no cost seen)",
                          "n_with": e["n_with"] if e else 0, "rd_mh": e["rd_mh"] if e else None})
            parts.append(default)
    return {"target_len": ladder_listen["target"], "text": " · ".join(parts), "items": items,
            "note": "Length from the listening ladder (N+1). A lever is 'data' when the tag cost >= 5 points of understanding "
                    "on >= 30 sentences each side (lesson x length adjusted); otherwise the default ships and says so. "
                    "'New word' here = not heard earlier in the lesson; the page refines it live with the Word Bank."}


def boost_list(listen):
    """Word keys that sank sentences he missed: the word he asked about (strong), else the keyed content words of the missed
    sentence (weak, shared 1/k)."""
    agg = {}
    for u in listen:
        if u["label"] != "breakdown":
            continue
        strong = set()
        words = (u.get("lookback") or {}).get("words") or []
        for s in u["signals"].values():
            if s.get("word"):
                words.append(an(s["word"]))
        for t in u["tok"]:
            n = an(t["w"]) if not t.get("lat") else fold(t["w"].split("-")[-1])
            if any(w and (n == w or n.endswith(w) and len(w) >= 3) for w in words):
                for k in ([t["k"]] if t.get("k") else t.get("ks") or []):
                    strong.add(k)
        weak = set()
        if not strong:
            for t in u["tok"]:
                if not t.get("f") and (t.get("k") or t.get("ks")):
                    weak.update([t["k"]] if t.get("k") else t["ks"][:1])
        for k in strong:
            a = agg.setdefault(k, {"key": k, "strong": 0, "weak": 0.0, "dates": set(), "ids": []})
            a["strong"] += 1
            a["dates"].add(u["date"])
            a["ids"].append(u["id"])
        for k in weak:
            a = agg.setdefault(k, {"key": k, "strong": 0, "weak": 0.0, "dates": set(), "ids": []})
            a["weak"] += 1 / len(weak)
            a["dates"].add(u["date"])
            a["ids"].append(u["id"])
    bk = bank()
    out = []
    for a in agg.values():
        it = bk.items.get(a["key"]) or {}
        out.append({"key": a["key"], "arabizi": it.get("arabizi"), "arabic": it.get("arabic"), "english": it.get("english"),
                    "strong": a["strong"], "weak": round(a["weak"], 2), "score": round(a["strong"] + a["weak"], 2),
                    "dates": sorted(a["dates"]), "last": max(a["dates"]), "ids": a["ids"][-6:]})
    out.sort(key=lambda x: (-x["score"], -x["strong"], x["key"]))
    return out[:60]


def rules_hear_say(listen, speak, console_all):
    names = {b["id"]: b["name"] for b in G.buckets}
    out = {}
    for rid in G.ids:
        L = [u for u in listen if rid in u["rules"]]
        Ls = [u for u in L if u["label"] in ("understood", "breakdown")]
        S = [u for u in speak if u["scored"] and rid in u["rules"]]
        corr = [c for c in console_all if c.get("bucket") == rid]
        out[rid] = {
            "name": names.get(rid),
            "hear": {"n": len(L), "understood": sum(u["label"] == "understood" for u in L),
                     "breakdown": sum(u["label"] == "breakdown" for u in L), "unknown": sum(u["label"] == "unknown" for u in L),
                     "pct": round(100 * sum(u["label"] == "understood" for u in Ls) / len(Ls), 1) if Ls else None,
                     "show": len(Ls) >= EFFECT_FLOOR,
                     "examples": [u["id"] for u in sorted(L, key=lambda u: (u["label"] != "breakdown", u["date"]), reverse=False)[:6]]},
            "say": {"uses": len(S), "corrected_any": sum(u["label"] == "corrected" for u in S),
                    "pct_ok": round(100 * sum(u["label"] == "success" for u in S) / len(S), 1) if S else None,
                    "corrections_this_rule": len(corr), "show": len(S) >= EFFECT_FLOOR,
                    "examples": [u["id"] for u in S if u["label"] == "corrected"][:6]},
        }
    return out


def swipe_picks(listen, date, audio):
    """Decision 7: 10 machine-labelled sentences of the latest lesson - 4 breakdowns, 3 unknowns, 3 understood (topped up
    from the other groups when one is short). Deterministic per lesson."""
    rng = random.Random("swipe:" + date)
    pools = {lab: [u for u in listen if u["date"] == date and u["label"] == lab] for lab in ("breakdown", "unknown", "understood")}
    want = {"breakdown": 4, "unknown": 3, "understood": 3}
    picks = []
    for lab, k in want.items():
        pool = pools[lab][:]
        rng.shuffle(pool)
        picks += pool[:k]
    rest = [u for lab in pools for u in pools[lab] if u not in picks]
    rng.shuffle(rest)
    picks += rest[: 10 - len(picks)]
    picks.sort(key=lambda u: u["t"])
    out = []
    for u in picks:
        rep = u.get("reply") or {}
        out.append({"id": u["id"], "t": u["t"], "end": u["end"], "text": u["text"], "machine_label": u["label"],
                    "signals": sorted(u["signals"]), "reply_text": rep.get("text"), "reply_end": rep.get("end"),
                    "audio": audio, "play_from": round(max(0.0, u["t"] - 0.4), 2),
                    "play_to": round(max(u["end"], rep.get("end") or u["end"]) + 0.5, 2), "clip": cut_clip(date, u, rep)})
    return out


def cut_clip(date, u, rep):
    """Same approach as build_grammar_console.cut_clip (ffmpeg atrim of the lesson audio). No ffmpeg or no audio -> None,
    and the page plays docs/lessons/<date>/audio/... from play_from to play_to."""
    adir = os.path.join(DOCS, "lessons", date, "audio")
    src = os.path.join(adir, "lesson.mp3")
    if not os.path.exists(src) or not shutil.which("ffmpeg"):
        return None
    a = max(0.0, u["t"] - 0.4)
    b = max(u["end"], (rep or {}).get("end") or u["end"]) + 0.5
    name = "sl-" + hashlib.sha1(f"{date}|{a:.1f}-{b:.1f}".encode()).hexdigest()[:16] + ".mp3"
    out = os.path.join(DOCS, "lessons", date, "clips", name)
    try:
        if not os.path.exists(out) or not os.path.getsize(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
            tmp = out + ".part.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"atrim={a:.2f}:{b:.2f},asetpts=PTS-STARTPTS",
                            "-ac", "1", "-b:a", "48k", tmp], check=True, timeout=120)
            os.replace(tmp, out)
        return f"{date}/clips/{name}"
    except Exception:
        return None


def farsi_summary():
    p = os.path.join(DATA, "farsi-cognates.json")
    if not os.path.exists(p):
        return {"file": None, "n": 0, "status": "missing"}
    d = load_json(p)
    return {"file": "data/farsi-cognates.json", "n": d.get("n"), "counts": d.get("counts"), "status": d.get("status")}


def audio_for(date):
    adir = os.path.join(DOCS, "lessons", date, "audio")
    if os.path.exists(os.path.join(adir, "lesson.mp3")):
        return [f"lessons/{date}/audio/lesson.mp3"]
    return [f"lessons/{date}/audio/{f}" for f in ("Amal.mp3", "Medi.mp3") if os.path.exists(os.path.join(adir, f))] or None


# ------------------------------------------------------------------ main build
def build(dates=None, write=True):
    bk = bank()
    meta_all = {l["date"]: l for l in load_json(os.path.join(DATA, "lessons.json"))["lessons"]}
    gc = load_json(os.path.join(DATA, "grammar-console.json"))
    console_all = [c for r in gc["rules"] for c in r.get("candidates", []) if c.get("verified")]
    dates = dates or sorted(meta_all)
    listen, speak, per_lesson = [], [], []
    for d in dates:
        p = os.path.join(DATA, "lessons", d + ".json")
        if not os.path.exists(p):
            continue
        doc = load_json(p)
        wl = os.path.join(RAW, d, "words_labeled.json")
        words = load_json(wl) if os.path.exists(wl) else None
        L, S, miss, n_amal = lesson_units(d, meta_all.get(d, {}), bk, [c for c in console_all if c["date"] == d], doc, words)
        for u in L + S:
            u["date"] = d
        listen += L
        speak += S
        lab = Counter(u["label"] for u in L)
        per_lesson.append({"date": d, "type": meta_all.get(d, {}).get("type"), "amal_sentences": n_amal,
                           "listen_units": len(L), "listen_labels": dict(lab),
                           "speak_sentences": len(S), "speak_scored": sum(u["scored"] for u in S),
                           "speak_labels": dict(Counter(u["label"] for u in S if u["scored"])),
                           "word_timings": words is not None, "missing_side": miss, "audio": audio_for(d),
                           "chat_lines": sum(1 for t in doc["turns"] if t.get("who") == "chat")})
    # global cut points
    def pct(vals, q):
        v = sorted(x for x in vals if x is not None)
        return v[int(q * (len(v) - 1))] if v else 0
    cut_l = {"wps_p75": pct([u["tags"]["wps"] for u in listen], 0.75), "emph_p75": pct([u["tags"]["emph_density"] for u in listen], 0.75),
             "syll_p75": pct([u["tags"]["syll"] for u in listen], 0.75)}
    cut_s = {"wps_p75": pct([u["tags"]["wps"] for u in speak], 0.75), "emph_p75": pct([u["tags"]["emph_density"] for u in speak], 0.75),
             "syll_p75": pct([u["tags"]["syll"] for u in speak], 0.75)}
    lad_l = ladder(listen, "understood", "breakdown")
    lad_s = ladder([u for u in speak if u["scored"]], "success", "corrected")
    # sensitivity view: 'understood' only with direct evidence (she confirmed / he reused her word / answered / glossed it)
    lad_l_strict = ladder([u for u in listen if not (u["label"] == "understood" and u.get("evidence") == "content reply only")],
                          "understood", "breakdown")
    eff_l = mh_effects(listen, "understood", "breakdown", cut_l)
    eff_s = mh_effects([u for u in speak if u["scored"]], "success", "corrected", cut_s)
    shown_l = [e["tag"] for e in eff_l if e["show"] and not e["tag"].startswith("rule_")]
    shown_s = [e["tag"] for e in eff_s if e["show"] and not e["tag"].startswith("rule_")]
    or_l = ridge_logit(listen, "understood", "breakdown", cut_l, shown_l)
    or_s = ridge_logit([u for u in speak if u["scored"]], "success", "corrected", cut_s, shown_s)
    for e in eff_l:
        e["or_adjusted"] = or_l.get(e["tag"])
    for e in eff_s:
        e["or_adjusted"] = or_s.get(e["tag"])
    latest = max((d["date"] for d in per_lesson if d["listen_units"]), default=None)
    lab_all = Counter(u["label"] for u in listen)
    summary = {
        "version": VERSION,
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "spec": "plan/SENTENCE-LADDER-SPEC-2026-09-27.md",
        "method": ("Listening unit = Amal's last Arabic sentence before a Medi reply (+ sentences charged by look-back, rescue, "
                   "or a hand-audited listening miss). Arabic words only; clitics stay inside their word. Labels are machine "
                   "guesses (rescue and wrong-answer are marked guess); Medi's swipes in supabase sentence_labels override them "
                   "on the page. Speaking success = no correction from Amal (grammar-console hand-verified + the lesson audit's "
                   "word fixes and words supplied)."),
        "thresholds": {"amal_join_s": AMAL_JOIN, "medi_join_s": MEDI_JOIN, "rescue_gap_s": RESCUE_GAP, "lookback_sentences": LOOKBACK_N,
                       "lookback_s": LOOKBACK_S, "mostly_english": MOSTLY_EN, "repeat_sim": REPEAT_SIM, "ladder_last": LADDER_LAST,
                       "ladder_pct": LADDER_PCT, "ladder_lessons": LADDER_LESSONS, "effect_floor": EFFECT_FLOOR},
        "cuts": {"listen": cut_l, "speak": cut_s},
        "lessons": per_lesson,
        "files": {d["date"]: f"data/sentence-ladder/{d['date']}.json" for d in per_lesson},
        "labels": {"listen": {k: lab_all.get(k, 0) for k in ("understood", "breakdown", "unknown")},
                   "speak": dict(Counter(u["label"] for u in speak if u["scored"]))},
        "ladder": {"listen": lad_l, "speak": lad_s, "listen_strict": {k: lad_l_strict[k] for k in ("N", "target", "pct_at_N")},
                   "rule": "good at N = >= 80% ok on the last 20 scored sentences of length N (at most 10 per lesson), "
                           "from >= 2 lessons; N = highest good length with no failed length below it; target = N + 1"},
        "evidence": {"understood": dict(Counter(u.get("evidence") for u in listen if u["label"] == "understood")),
                     "unknown": dict(Counter(u.get("why_unknown") for u in listen if u["label"] == "unknown")),
                     "breakdown_signals": dict(Counter(k for u in listen if u["label"] == "breakdown" for k in u["signals"]))},
        "effects": {"listen": [{k: v for k, v in e.items()} for e in eff_l], "speak": [{k: v for k, v in e.items()} for e in eff_s]},
        "recipe": recipe(lad_l, eff_l),
        "boost": boost_list(listen),
        "rules": rules_hear_say(listen, speak, console_all),
        "swipe": {"date": latest, "picks": swipe_picks(listen, latest, audio_for(latest)) if latest else [],
                  "table": "sentence_labels (supabase/migrations/020_sentence_labels.sql)"},
        "farsi_cognates": farsi_summary(),
        "deferred": ["monthly fixed 20-sentence listening check (spec, 'Later')"],
    }
    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        for d in per_lesson:
            date = d["date"]
            doc = {"version": VERSION, "date": date, "clock": f"seconds on the lesson page audio (docs/lessons/{date}/audio/...)",
                   "audio": d["audio"], "missing_side": d["missing_side"],
                   "listen": [u for u in listen if u["date"] == date], "speak": [u for u in speak if u["date"] == date]}
            with open(os.path.join(OUT_DIR, date + ".json"), "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))
    return summary, listen, speak


def dump(date):
    s, L, S = build([date], write=False)
    for u in L:
        print(f"{int(u['t'])//60:02d}:{int(u['t'])%60:02d} n={u['n']:2d} {u['label']:10s} {','.join(u['signals'])}")
        print("   A:", u["text"][:160])
        if u.get("reply"):
            print("   M:", u["reply"]["text"][:160])


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")
    ap.add_argument("dates", nargs="*")
    a = ap.parse_args()
    if a.dump:
        dump(a.dump)
        sys.exit(0)
    try:                                         # run log (data/runs, scripts/track.py): kind=build, rows out; never blocks
        import track
        _ctx = track.run("sentence_ladder.build", a.dates[-1] if len(a.dates) == 1 else None, kind="build",
                         tool=f"scripts/build_sentence_ladder.py@{VERSION}", params={"dates": a.dates or "all"},
                         inputs=[os.path.join(DATA, "lessons.json"), os.path.join(DATA, "grammar-console.json")])
        _run = _ctx.__enter__()
    except Exception:
        _ctx = _run = None
    try:
        summary, L, S = build(a.dates or None)
    except BaseException as _e:
        if _ctx is not None:
            try:
                _ctx.__exit__(type(_e), _e, _e.__traceback__)
            except BaseException:
                pass
        raise
    if _ctx is not None:
        try:
            _run.set(output_refs=[track.ref(OUT_SUMMARY, rows=len(L) + len(S))] +
                     [track.ref(os.path.join(OUT_DIR, d["date"] + ".json"), rows=d["listen_units"] + d["speak_sentences"])
                      for d in summary["lessons"]],
                     metrics={"listen_units": len(L), "speak_sentences": len(S), "labels": summary["labels"],
                              "ladder_listen_N": summary["ladder"]["listen"].get("N"),
                              "ladder_speak_N": summary["ladder"]["speak"].get("N")})
            _ctx.__exit__(None, None, None)
        except Exception:
            pass
    lab = summary["labels"]["listen"]
    tot = sum(lab.values()) or 1
    print("listening units:", tot, {k: f"{v} ({100 * v / tot:.0f}%)" for k, v in lab.items()})
    print("speaking scored:", summary["labels"]["speak"])
    ll, ls = summary["ladder"]["listen"], summary["ladder"]["speak"]
    print("listening ladder N=%s target=%s pct@N=%s" % (ll["N"], ll["target"], ll["pct_at_N"]))
    print("speaking ladder  N=%s target=%s pct@N=%s" % (ls["N"], ls["target"], ls["pct_at_N"]))
    print("recipe:", summary["recipe"]["text"])
    print("wrote", OUT_SUMMARY, "and", OUT_DIR)
