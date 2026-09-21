import json,re,copy,hashlib,collections
from pathlib import Path
import sys
W=Path(sys.argv[1]);R=Path(__file__).resolve().parents[1]
snap=json.loads((W/'snapshot-investigate.json').read_text(encoding='utf8'));events=snap['events'];patches={};additions=[];row_edits={}
def own(e):return next((r['text'] for r in e.get('context',[]) if r['row_id']==e['row_id']),e.get('text',''))
def norm(t):return re.sub(r'[^\w\s]',' ',t.lower()).strip()
def find(prefix):return next(e for e in events if e['id'].startswith(prefix))
def setp(e,reason,**kw):
 p=patches.setdefault(e['id'],{'expected':{k:e.get(k) for k in ['source_sha256','row_id','word_key','text','t_start','t_end','assessment','reason']},'changes':{}})['changes']
 p.update(contextual_audit=True,audit_version='2026-09-21-context-v1',reason=reason,**kw)
def correct(e,reason,**kw):setp(e,reason,assessment='independent',vocab_points=1,ignored=False,observation_only=False,needs_review=False,immediate_repeat=False,is_echo=False,grammar_only=False,classification='lexical',**kw)
def ignore(e,reason,**kw):setp(e,reason,assessment='unresolved',vocab_points=None,ignored=True,**kw)
def wrong(e,reason,**kw):setp(e,reason,assessment='incorrect',vocab_points=0,ignored=False,observation_only=False,immediate_repeat=False,is_echo=False,needs_review=False,grammar_only=False,classification='lexical',wrong_parts=[e['text'].strip(' .،؟?!')],**kw)
# Every learner event is audited. Only positively supported changes are applied.
for e in events:
 if e['speaker']!='Medi':continue
 text=own(e);n=norm(text);reason=e.get('reason','');key=e.get('word_key');ctx=e.get('context',[])
 blocked=e.get('ignored') or e.get('is_echo') or e.get('immediate_repeat') or e.get('grammar_only') or e.get('scored_in_event') or e.get('observation_only') or e.get('wording_status')=='unresolved' or not key
 if not blocked and e['assessment']=='helped' and re.search(r'Learner replays (?:the corrected sentence|the sentence after)|Tutor has supplied/written',reason):
  ignore(e,'Repeats or reads the supplied correction/model; no additional vocabulary score.',immediate_repeat=True);continue
 meaning=re.search(r'(?:شو\s+يعني|shu\s+ya[3a]ni|what\s+does)\s+(.+)',text,re.I)
 if meaning:
  target=norm(meaning.group(1));token=norm(e['text'])
  if key in ['shu','ya3ni']:ignore(e,'Question wording, not the unknown vocabulary target. No vocabulary penalty or new assessment for the question wrapper.');continue
  if token and token in target:wrong(e,'Explicit request for this word’s meaning: score the requested vocabulary target, not shu/ya3ni.');continue
 if key=='shu' and (re.fullmatch(r'(?:uh|um|آه|اه|آآآ|شو|shu|what|huh|\s)+',n) or re.search(r'what did you (?:just )?say',text,re.I)):
  ignore(e,'Clarification request (“what?”), not failed recall of shu.');continue
 if not blocked and e['assessment']=='helped' and re.search(r'self.correct',reason,re.I) and re.search(r'before Amal supplies|within the same sentence',reason) and not re.search(r'hint|cue|overlap',reason,re.I):
  correct(e,'Self-corrected before the tutor supplied the answer: full credit for the final word; the abandoned word receives no miss.',self_corrected=True);continue
 if key=='alyoum' and not blocked:
  if e['id'].startswith(('3b4227bdfc','0f04332efa','0be5a0f7a5')):continue
  correct(e,'El-yom is used as today; nearby hesitation, another word’s correction, or its presence in Amal’s question is not an error on el-yom.');continue
 if not blocked and e['assessment']=='helped' and re.search(r'question.*new.*answer|supplied.*new (?:answer|sentence)',reason,re.I):
  correct(e,'Word used in a new answer, not a repetition or a requested answer supplied by the tutor. A word occurring in the question alone does not reduce credit.');continue
 if not blocked and e['assessment']=='helped' and reason.startswith('Same vocabulary supplied'):
  mine=next((r for r in ctx if r['row_id']==e['row_id']),None)
  before=[r for r in ctx if r['speaker']=='Amal' and r.get('timeline_end',1e9)<=e['t_start']]
  after=[r for r in ctx if r['speaker']=='Amal' and 0<=r.get('timeline_start',-1)-e['t_end']<=8]
  toks=[t for t in re.findall(r'[\w]+',n) if t not in ['uh','um','yeah','okay','oh','اه','آآآ']]
  if before and re.search(r'[?؟]',before[-1]['text']) and len(toks)>=3 and not any(re.search(r'\b(no|wrong|instead|correction)\b|لا،|بالعكس',r['text'],re.I) for r in after):
   correct(e,'New connected answer to a question. No word-specific error established; tutor use of the word in a question is not sufficient evidence of help.');continue
 # Preserve prior explicit decisions; improve the script-biased baseline only
 # where the tutor confirms a connected answer and does not offer a correction.
 if not blocked and e['assessment']=='unresolved' and reason.startswith('Isolated production'):
  after=[r for r in ctx if r['speaker']=='Amal' and 0<=r.get('timeline_start',-1)-e['t_end']<=8]
  if len(re.findall(r'[\w]+',text))>=3 and after and re.fullmatch(r'(?:ممتاز|صح|حلو|مم|mm.hmm|okay|yes|perfect|excellent|[\s.!،])+',after[0]['text'],re.I):
   correct(e,'Connected Arabizi/Arabic answer followed by tutor confirmation; Latin transcription is not evidence of an isolated or wrong word.')
# Source-bound decisions explicitly established in the user’s review.
wrong(find('e2685055e7'),'Safra was substituted for Safar and Amal corrected the distinction. Both words receive a linked miss.',attempt_target={'word_key':'safar'},confusion_pair=True)
ignore(find('6b6eac659a'),'Repeats Safar after Amal supplied the correction; no new score.',immediate_repeat=True)
correct(find('414ca95cfe'),'Safra is used in a connected sentence and Amal confirms it with mumtaz; Arabizi transcription does not make it an isolated attempt.')
for pref in ['8873d9589f','bdb049b891','cadde19a66']:
 correct(find(pref),'Self-corrected before Amal supplied the answer: final target earns 1; original false start is not penalized.',self_corrected=True)
ignore(find('2339cba193'),'Abandoned eighteen corrected to eighty by Medi before the tutor supplied eighty. No miss for the abandoned word.',scored_in_event=find('8873d9589f')['id'])
# Existing genuine substitutions also follow the agreed both-words rule.
for pref in ['80485988fd','bcbd99d026']:
 e=find(pref);setp(e,e['reason'],wrong_parts=[])
e=find('ac5a7ffbd9');setp(e,e['reason'],wrong_parts=['بخسر'])
wrong(find('39b569c9bd'),'Explicitly swapped the meanings of annoyed and annoying; both vocabulary items receive a linked miss.',attempt_target={'word_key':'muz3ej'},confusion_pair=True)
wrong(find('d8fc282b86'),'Eleven was offered for twelve and corrected by Amal; both vocabulary items receive a linked miss.',attempt_target={'word_key':'tna3sh'},confusion_pair=True)
# Do not invent a confidently recognized spoken word for an uncertain ASR fragment.
# This specific pronunciation was supplied directly by the learner in this chat.
def derived(seed,row,key,text,assessment,reason):
 e=copy.deepcopy(seed);off=seed['t_start']-seed['local_start'];e.update(id=hashlib.sha256(('context-audit:'+row['row_id']+':'+key).encode()).hexdigest(),row_id=row['row_id'],word_key=key,text=text,original_text=row['text'],t_start=row['timeline_start'],t_end=row['timeline_end'],local_start=row['timeline_start']-off,local_end=row['timeline_end']-off,item_ids=[],assessment=assessment,reason=reason,assessment_status='user_reviewed',contextual_audit=True,classification='lexical',spoken=True,match_method='user_transcript_correction',vocab_points=0 if assessment=='incorrect' else 1)
 for k in ['ignored','is_echo','immediate_repeat','observation_only','grammar_only','attempt_target','scored_in_event']:e.pop(k,None)
 additions.append({'anchor_id':seed['id'],'expected_source':seed['source_sha256'],'event':e});return e
seed=find('a02476f003');row=next(r for r in seed['context'] if r['speaker']=='Medi' and 'كمي' in r['text'])
bad=derived(seed,row,'8Ame2','8amee2','incorrect','Learner-confirmed pronunciation was 8amee2, transcribed incorrectly as kmy. Amal corrected it to 8aame2; score 0.')
bad.update(wrong_parts=['8amee2'],corrected_text='8aame2',transcript_correction=True)
row_edits[row['row_id']]={'source_sha256':seed['source_sha256'],'original':row['text'],'display':'uh, 8amee2','reason':'Learner-confirmed transcription correction; original ASR retained.'}
ignore(seed,'Immediate repetition after Amal corrected 8amee2 to 8aame2; the initial attempt receives the miss.',immediate_repeat=True)
seed=find('ec9b816823');row=next(r for r in seed['context'] if r['row_id']==seed['row_id'])
bluz=derived(seed,row,'blUze','buluz','independent','Learner confirmed buluz (shirt); ASR blwz/بلوز is a transcription variant, not a lexical error.')
row_edits[row['row_id']]={'source_sha256':seed['source_sha256'],'original':row['text'],'display':'Uh, buluz abyad','reason':'Learner-confirmed buluz spelling; original ASR retained.'}
# Review obvious clarification uses in the supplied contexts.
for pref in ['19f769d7c0','66da52468a','91d2249cb9','ddde005081','bd27cbd8d7']:
 ignore(find(pref),'Asking the tutor to repeat or clarify the utterance; not failed recall of shu.')
correct(find('fc96a30ce8'),'Shu is correctly used in the new question about today’s verbs; the earlier standalone clarification shu is excluded.')
# Specific connected Latin-script uses from the broader audit.
for pref in ['9b47e75867','3ebb377f89','279e084cff','e9dd186be8','99ca46e6f8','dfe25e9468','9a9d9cec4a','bc221fd9c9','d4abd7ce9d']:
 correct(find(pref),'Context supports the vocabulary use in the learner’s own answer; pause segmentation or Latin-script ASR is not a word-specific error.')
# Repeated restarts within one row should not multiply a scored attempt.
seen={}
for e in sorted(events,key=lambda e:(e['lesson_date'],e['t_start'])):
 if e['speaker']!='Medi':continue
 p={**e,**patches.get(e['id'],{}).get('changes',{})};k=(e['lesson_date'],e['row_id'],e['word_key'])
 if p.get('assessment')=='independent' and not p.get('ignored') and e['word_key']:
  if k in seen:ignore(e,'Repeated occurrence within the same sentence; count the vocabulary attempt once.',scored_in_event=seen[k])
  else:seen[k]=e['id']
out={'version':'2026-09-21-context-v1','patches':patches,'additions':additions,'transcript_rows':row_edits}
(R/'docs/data/word-bank-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
reviewed=[{**e,**patches.get(e['id'],{}).get('changes',{})} for e in events]+[x['event'] for x in additions]
audit=[]
for e in reviewed:
 if e['speaker']!='Medi':continue
 status='not scored' if any(e.get(k) for k in ['ignored','is_echo','immediate_repeat','grammar_only','observation_only','scored_in_event']) else e['assessment']
 audit.append({'id':e['id'],'date':e['lesson_date'],'time':round(e['t_start'],2),'word':e.get('word_key'),'status':status,'changed':e['id'] in patches or any(x['event']['id']==e['id'] for x in additions),'sentence':own(e),'reason':e['reason']})
(W/'audited-events.json').write_text(json.dumps(reviewed,ensure_ascii=False),encoding='utf8')
(R/'docs/data/word-bank-audit.json').write_text(json.dumps({'version':out['version'],'scope':'All published learner occurrences; contextual/rule audit, not a fresh audio transcription. Unresolved entries remain unscored.','counts':dict(collections.Counter(e['status'] for e in audit)),'events':audit},ensure_ascii=False,indent=2),encoding='utf8')
print('Reviewed',len(audit),'patches',len(patches),'new recovered entries',len(additions),'counts',collections.Counter(e['status'] for e in audit))
