/* Presentation only. Never use this rendering as pronunciation or scoring evidence. */
(function(root){
'use strict';
const AR=/[\u0621-\u063A\u0641-\u064A\u0671]/;
const norm=s=>String(s||'').normalize('NFC').replace(/[\u064B-\u065F\u0670\u0640]/g,'').replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي');
// Common spoken forms and discourse words. These do not correct the source wording.
const spoken={
 'جواب':'jawaab','المضارع':'el-muDaare3','مضارع':'muDaare3','سهل':'sahel','نجوم':'nujoom','نجمة':'nejme','ألوان':'alwaan','بلوز':'buluz','ريحته':'ree7to','السؤال':'el-su2aal','سؤال':'su2aal','درجة':'darjet',
 'أنا':'ana','إنت':'inta','إنتي':'inti','أنت':'inta','أنتي':'inti','إنتو':'intu','هو':'huwwe','هي':'hiyye','إحنا':'i7na','احنا':'i7na','هم':'humme','هما':'humma','همه':'humme',
 'شو':'shu','مش':'mish','ما':'ma','لا':'la','آه':'aah','اه':'ah','آآآ':'aaa','آآ':'aa','أآ':'aa','آ':'aa','مم':'mm','مهم':'muhim','امم':'umm','أمم':'umm','طيب':'6ayyeb','بس':'bas','يعني':'ya3ni',
 'كل':'kul','إشي':'ishi','اشي':'ishi','شي':'shi','كمان':'kaman','مرة':'marra','تاني':'tani','هلا':'halla','هلأ':'halla2','هلأك':'halla2ak','هلق':'halla2','اليوم':'el-yom','امبارح':'embare7','مبارح':'mbare7',
 'اللي':'illi','إلي':'illi','الي':'illi','إنه':'enno','إنو':'enno','إن':'en','أنه':'enno','أنو':'enno','لما':'lamma','إذا':'iza','اذا':'iza','عشان':'3ashan','لأنه':'la2anno','لانو':'la2anno',
 'من':'min','في':'fi','فيه':'fih','فيها':'fiha','فيو':'fiyo','مع':'ma3','على':'3ala','عن':'3an','عند':'3ind','عندي':'3indi','عندك':'3indak','عندكم':'3indkom','عنا':'3inna','عندهم':'3indhom',
 'و':'w','ب':'b','ل':'l','ال':'el','يا':'ya','هادا':'hada','هذا':'hada','هاد':'had','هاي':'hay','هادي':'hadi','هدول':'hadol','هون':'hon','هناك':'hunak','هيك':'hek',
 'نعم':'na3am','صح':'sa7','صحيح':'sa7i7','تمام':'tamam','ممتاز':'mumtaz','منيح':'mni7','حلو':'7elu','أكيد':'akid','اوكي':'okay','أو':'aw','أول':'awwal','آخر':'akher',
 'الكلمة':'el-kilme','كلمة':'kilme','الجملة':'el-jumle','جملة':'jumle','الفعل':'el-fi3el','فعل':'fi3el','أفعال':'af3al','الأفعال':'el-af3al','بعد':'ba3d','بعدين':'ba3den','قبل':'2abl',
 'بدك':'biddak','بدي':'biddi','بدنا':'bidna','لازم':'lazem','ممكن':'mumkin','تقدر':'ti2dar','بقدر':'ba2dar','بنقدر':'bni2dar','شوفت':'shuft','شفت':'shift',
 'كان':'kan','كانت':'kanet','كنت':'kunt','كنا':'kunna','يكون':'ykun','تكون':'tkun','أكون':'akun','يكونوا':'ykunu','بتكون':'btikun',
 'بيصلح':'bi9alle7','يصلح':'yi9alle7','بصلح':'ba9alle7','بتصلح':'bti9alle7','بيصلع':'bi9la3','بيخرب':'bi5arrib','بيخربه':'bi5arrbo','بخرب':'ba5arrib','بتخرب':'bti5arrib','خرب':'5arab','خربت':'5arabet','خربتهم':'5arabet-hom',
 'بيحكي':'bi7ki','بحكي':'ba7ki','أحكي':'a7ki','احكي':'i7ki','بتحكي':'bti7ki','بحكيلك':'ba7kilak','بيحكولي':'bi7kuli','حكيت':'7aket','حكينا':'7akena',
 'بعرف':'ba3raf','بتعرف':'bti3raf','بتعرفي':'bti3rafi','نسيت':'nsit','ناسي':'nasi','عارف':'3aref','فهمت':'fhemet','فاهمة':'fahme','فاهم':'fahem',
 'بنبسط':'binbisit','بنبسطوا':'binbis6u','ببسط':'babsu6','انبسط':'inbasa6','أنبسط':'anbisi6','انبسطت':'inbasa6et','بينبسط':'byinbisit','بتنبسط':'btinbisit','بتنبسطي':'btinbis6i',
 'بعصب':'ba3a99ib','بتعصب':'bti3a99ib','بعصّب':'ba3a99ib','أعصب':'a3a99ib','تعصب':'ti3a99ib','بيعصبني':'bi3a99ibni','بزعج':'baz3ij','بنزعج':'binzi3ij','انزعجت':'inza3ajet',
 'بضحك':'baD7ak','بيضحك':'biDa77ek','بيضحكني':'biDa77ekni','بتعب':'bat3ab','أتعب':'at3ab','أتعبها':'at3abha','بتضل':'btiDall','بضل':'baDall',
 'بشتغل':'bashti8el','أشتغل':'ashti8el','اشتغلت':'ishta8alet','بمشي':'bamshi','بشرب':'bashrab','شربت':'shribet','بشم':'bashemm','بكتب':'baktub','أكتب':'aktub','صحيت':'97it',
 'بيحطوا':'bi7u66u','حطوا':'7a66u','بيلبس':'byilbas','بلبس':'balbas','لابس':'labes','بتغير':'bti8ayyer','بغير':'ba8ayyer','غيرتي':'8ayyarti','غيرت':'8ayyaret',
 'بصور':'ba9awwer','بتصور':'bti9awwer','صوريني':'9awwrini','تصوريني':'t9awwrini','صورت':'9awwaret','بتذكر':'btitzakkar','بذكر':'bazakker','تذكرت':'tzakkaret',
 'بتوجع':'btiwajja3','بيوجع':'biwajja3','بيوجعها':'biwajja3ha','رجله':'rijlo','رجلك':'rijlak','بطنها':'ba6inha','كسرت':'kasaret','كسرتي':'kasarti','بكسر':'bakser',
 'ساعد':'sa3ad','ساعدني':'sa3adni','صلح':'9alla7','صلحلي':'9alla7li','أطلب':'a6lob','أطلبهم':'a6lobhom','بطلب':'ba6lob','منهم':'minhom','معهم':'ma3hom','لهم':'ilhom','لها':'ilha',
 'بعتذر':'ba3tizer','بتأسف':'bat2assaf','أتأسف':'at2assaf','أسف':'asef','بأسف':'ba2saf','آسف':'asef','صحتين':'9a7ten','فحتين':'fa7ten','قلبك':'2albak',
 'خطيبتي':'5a6ibti','عيلتي':'3elti','عيلتنا':'3eltna','أخوي':'a5uy','شعرك':'sha3rak','شعرها':'sha3rha','رأيي':'ra2yi','رأي':'ra2y','راي':'ray',
 'أزرق':'azra2','فاتح':'fate7','أسود':'aswad','سودا':'soda','بنية':'bunniyye','قهوة':'ahwe','كتير':'ktir','شوي':'shway','مليان':'malyan','عادة':'3ade','عادةً':'3adatan',
 'شلون':'shlon','كيف':'kif','قديش':'2addesh','ليش':'lesh','ليه':'leh','وين':'wen','مين':'meen','كم':'kam','شكرًا':'shukran','شكرا':'shukran','يلّا':'yalla','يلا':'yalla','معليش':'ma3lesh','معلش':'ma3lesh',
 'أعطيك':'a36ik','يعطيك':'ya36ik','يعطيكي':'ya36iki','الله':'allah','العافية':'el-3afye','يبارك':'ybarek','فيك':'fik','بيومك':'byomak','أشوفك':'ashufak','بشوفك':'bashufak',
 'مغيم':'m8ayyem','مغيمة':'m8ayyme','مغني':'m8anni','شوب':'shob','درجة':'daraje','الحرارة':'el-7arara','حوالين':'7awalen','نفس':'nafs',
 'تمنتاش':'tmanta3sh','تمانين':'tamanin','ثمانين':'thamanin','تلاتة':'tlate','خمسة':'5amse','وعشرين':'w-3ishrin','ونص':'w-nu99','بسرعة':'bisur3a'
};
function create(words=[],catalog={},extra={},opts={}){
 const exact=new Map(),lexicon=new Map();
 // Words she never typed whole: sound-alike matches and her own pieces, checked against the sentence (arabizi-extra.json).
 // A row with a scope ("lessons": his own wrong / cut-off / unclear forms, method as-said) is used only by the page that
 // asks for that scope - the Lessons page error cards and transcript lines (RULES.md S1, AZ-05 / AZ-10). Everywhere
 // else the word falls through to the Arabic + "Unverified spelling stays in Arabic" (Codex final approval 2026-10-05).
 const built=new Map(),asSaid=new Set();for(const [ar,e] of Object.entries(extra.words||{}))if(e&&e.latin&&(!e.scope||e.scope===opts.scope)){built.set(norm(ar),e.latin);if(e.method==='as-said'||e.scope)asSaid.add(norm(ar));}
 const sheetPairs=[];   // AZ-snap: [norm Arabic, her Latin] from her own sheet rows only
 function add(ar,latin){
  // Her Doc adds notes in brackets: "أسبوع (أسبوعين" / "Usboo3", "3ain (F)". Keep the word, drop the note.
  const clean=x=>String(x||'').replace(/\([^)]*\)?/g,' ').replace(/\s+/g,' ').trim();
  ar=clean(ar);latin=clean(latin);
  if(!ar||!latin||AR.test(latin)||/[\/|()[\]]/.test(ar+latin)||!AR.test(ar))return;
  const a=ar.split(/\s+/),b=latin.split(/\s+/);if(a.length!==b.length)return;
  a.forEach((s,i)=>{if(AR.test(s)&&/^[\p{L}0-9'’\-]+$/u.test(b[i])){if(!lexicon.has(norm(s)))lexicon.set(norm(s),b[i]);sheetPairs.push([norm(s).replace(/[^ء-ي]/g,''),b[i]]);}});
 }
 for(const w of words)add(w.arabic,w.house_spelling||w.arabizi);
 for(const g of catalog.groups||[])for(const f of g.entries||[]){add(f.arabic,f.word);for(const p of f.persons||[])if(p.provenance==='document')add(p.arabic,p.word);}
 // Pronouns in documented conjugations disambiguate homographs such as Hayy (here’s) versus heyye (she).
 for(const [key,ar] of [['heiye ','هي'],['huwe ','هو'],['i7na ','إحنا'],['intu ','إنتو'],['hume ','هم']]){const form=words.find(w=>w.key?.startsWith(key)&&w.arabizi);if(form)lexicon.set(norm(ar),form.arabizi.split(/\s+/)[0]);}
 for(const [ar,latin] of Object.entries(spoken)){exact.set(ar,latin);if(!lexicon.has(norm(ar)))lexicon.set(norm(ar),latin);}
 // Homographs and Doc typos (hand check 2026-09-26, 96/100): the same Arabic has several Doc rows; pick the everyday sense.
 // Her own spellings only (Marra = 'one time' row; Tenein = her 'two' row minus a stray V; Kam = her 'how many' row,
 // not Kum 'sleeve' - Medi 2026-10-02).
 // 3indna = her own chat spelling (9x; Medi 2026-10-03 "I said e7na 3endna (we have)" - the page showed 3inna).
 for(const [ar,latin] of [['مرة','Marra'],['تنين','Tenein'],['كم','Kam'],['عندنا','3indna'],['طريق','6aree2'],['قانون','qanoon']])lexicon.set(norm(ar),latin);   // 6aree2: her '3ala el-6aree2' (was 6ariq)
 // Homograph by context (Medi 2026-10-03 "not saanye, taanye (another shirt as written later)"): ثانية is her list's Saanie
 // (a second, Units of Time) only after a number or kam ('khamas thawaani', 'kam saanie'); everywhere else it is taanye,
 // second / another (her chat: 'marra tanye', 'el-tayyara el-taanya') - 'blooze taanye'.
 const NUMBEFORE=/(?:^|\s)(?:\d+|كم|واحدة?|وحدة|تنتين|ثنتين|تلات|ثلاث|اربع|أربع|خمس|ست|سبع|تمان|ثمان|تسع|عشر|[ء-ي]+ة?عشر)[\s،,]*$/;
 function sense(raw,before){
  const n=norm(raw);
  if(n===norm('ثانية')||n===norm('ثانيه'))return {text:NUMBEFORE.test(before||'')?'Saanie':'taanye',approximate:false};
  for(const [pre,lat] of [['وال','w-el-'],['بال','b-el-'],['ال','el-']])if(n===norm(pre+'ثانية')||n===norm(pre+'ثانيه'))return {text:lat+'taanye',approximate:false};
  return word(raw);
 }
 function word(raw){
  if(/^آ+ه?$/.test(raw))return {text:raw.endsWith("ه")?"aaah":"aaa",approximate:false};
  const n=norm(raw);if(lexicon.has(n))return {text:lexicon.get(n),approximate:false};
  if(exact.has(raw))return {text:exact.get(raw),approximate:false};
  for(const [prefix,latin] of [['وال','w-el-'],['بال','b-el-'],['لل','l-el-'],['ال','el-'],['و','w-']]){
   if(n.startsWith(prefix)&&lexicon.has(n.slice(prefix.length)))return {text:latin+lexicon.get(n.slice(prefix.length)),approximate:false};
  }
  // his own wrong / cut-off forms (as-said) win: the error cards must show what he said
  if(asSaid.has(n))return {text:built.get(n),approximate:false,built:true};
  // AZ-12 (Medi 2026-10-09 "99% of the words said should come from amals arabic list ... if you strongly suspect a word to
  // be on my list. You need to using the arabizi from our sheet." + "yes"): on a transcript line, a word one letter away
  // from exactly ONE word of her sheet is shown in her sheet's Arabizi; the engine's Arabic stays small underneath (S2,
  // TR-02: his real slip stays visible there and on the error cards, whose as-said forms are matched above).
  if(opts.snap){const s=snap(n);if(s)return {text:s.latin,approximate:false,snapped:s.ar};}
  if(built.has(n))return {text:built.get(n),approximate:false,built:true};
  return {text:raw,approximate:true}; // Keep Arabic when vowels/spelling are not documented; never invent a consonant string.
 }
 // Her sheet's words only (her Doc + catalog rows - not the built-in spoken list, not arabizi-extra), 3+ letters.
 // A strong suspicion = the SAME word once the letters the engine swaps by sound are folded together (ث=ت, ذ=ز/د, ظ=ض,
 // ص=س, ط=ت, ق=ء, ة=ه, ى=ي, أ/إ/آ=ا) and exactly ONE of her rows folds to it. A blind one-letter distance was tried on
 // 10-08 (2026-10-09) and was wrong in most of 41 changes (ثلاث three -> Tult a third, أمريكا -> Amriki): not used.
 let sheetIdx=null;
 const fold=w=>w.replace(/[ث]/g,'ت').replace(/[ذ]/g,'ز').replace(/[ظ]/g,'ض').replace(/[ص]/g,'س').replace(/[ط]/g,'ت').replace(/[ق]/g,'ء').replace(/[ؤئ]/g,'ء').replace(/ة/g,'ه').replace(/[^ء-ي]/g,'');
 function snap(n){
  if(n.length<3)return null;
  if(!sheetIdx){sheetIdx=new Map();for(const [ar,lat] of sheetPairs){const f=fold(ar);if(!f)continue;const o=sheetIdx.get(f);if(!o)sheetIdx.set(f,{ar,lat,n:1});else if(o.lat.toLowerCase()!==lat.toLowerCase())o.n++;}}
  if(fold(n)===fold('ثانيه'))return null;              // تانية taanye (another) vs her ثانية Saanie (a second): sense() decides
  const h=sheetIdx.get(fold(n));
  return h&&h.n===1?{ar:h.ar,latin:h.lat}:null;      // two different rows fold the same = not a strong suspicion
 }
 return function render(text){let approximate=false;const source=String(text||'');const value=source.replace(/ـ/g,'').replace(/[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]/g,'').replace(/[\u0621-\u063A\u0641-\u065F\u0670\u0671]+/g,(s,off,str)=>{const w=sense(s,str.slice(0,off));approximate ||= w.approximate;return w.text;}).replace(/،/g,',').replace(/؟/g,'?').replace(/؛/g,';');return {text:value,source,generated:AR.test(source),approximate};};
}
const api={create};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.AneesWordBankArabizi=api;
})(typeof window!=='undefined'?window:globalThis);
