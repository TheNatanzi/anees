"""Build source-linked Word Bank form groups. Offline; never writes to the Doc or DB.

Run after import_vocab.py. Explicit --document/--words paths support saved exports.
Ambiguous matches stay separate; generated forms are marked inferred.
"""
import argparse,json,re,sys
from pathlib import Path

PRONOUNS={'ana':'I','inta':'You (m)','inti':'You (f)','huwwe':'He','huwwa':'He','heyye':'She','hiyye':'She','i7na':'We','e7na':'We','intu':'You (pl)','humme':'They'}
IRREGULAR=dict(zip('ate drank spoke talked wrote read went came saw knew thought bought brought took gave made did said told paid pushed walked ran sat stood slept woke felt found lost left heard understood began started forgot remembered drove rode flew swam wore kept met sent built cut put taught learned learnt fell won became got held caught chose sold sang broke'.split(),'eat drink speak speak write read go come see know think buy bring take give make do say tell pay push walk run sit stand sleep wake feel find lose leave hear understand begin start forget remember drive ride fly swim wear keep meet send build cut put teach learn learn fall win become get hold catch choose sell sing break'.split()))
IRREGULAR.update({'drew':'draw','drawn':'draw','swore':'swear','tore':'tear','fed':'feed','lit':'light','was':'be','were':'be','could':'can'})
SYNONYMS={'talk':'speak'}
def gloss(s):
    s=re.sub(r'^(?:I|You(?:\s*\([^)]*\))?|He|She|We|They)\s+','',s.strip(),flags=re.I)
    s=re.sub(r'\([^)]*\)','',s).strip().lower()
    result=[]
    for part in re.split(r'\s*[/;]\s*',s):
        part=part.strip(); token=part.split(' ')[0] if part else ''
        token=IRREGULAR.get(token,token)
        if token.endswith('ied'):token=token[:-3]+'y'
        elif token.endswith('ed') and token not in {'need','feed','bleed','breed','speed','succeed','exceed','proceed'}:
            stem=token[:-2]
            result.append(stem[:-1] if stem.endswith('e') else stem)
            token=stem[:-1] if len(stem)>2 and stem[-1:]==stem[-2:-1] else stem
        token=SYNONYMS.get(token,token)
        result.append(token[:-1] if token.endswith('e') else token)
    return set(result)-{''}
def consonants(s):
    s=s.lower().replace('q','2').replace('kh','5').replace('gh','8').replace('sh','S').replace('6','t').replace('9','s')
    s=re.sub('[aeiou\\W]','',s)
    return re.sub(r'(.)\1+',r'\1',s)
VERB_ENGINE_SKIP={'ana beddi'}  # a pseudo-verb (bidd- + ending), not conjugated
def load_verb_checks(root):
    """Amal's answers from the verb check list (scripts/verb_check_links.py pull). Her text always wins."""
    path=root/'data/vocab/amal_verb_checks.json'
    return json.loads(path.read_text(encoding='utf-8')).get('answers',{}) if path.exists() else {}
def fill_verb_forms(groups,checks):
    """Every person of Present/Past/Command: Amal's documented form, else the
    engine's guess tagged checked=False. This is the only writer of guessed forms."""
    import verb_forms as vf
    for g in groups:
        if g['type']!='Verb' or g['key'] in VERB_ENGINE_SKIP:continue
        forms={}
        for f in g['entries']:
            if f['label'] not in vf.TENSES:continue
            forms[f['label']]={p['person']:(vf.strip_pronoun(p['word']),vf.strip_ar_pronoun(p.get('arabic',''))) for p in f['persons'] if p['provenance']=='document' and (' / ' not in p['word'] or f['label']=='Present')}
        if not forms.get('Present',{}).get('I'):continue
        out=vf.conjugate(forms)
        for f in g['entries']:
            if f['label'] not in vf.TENSES:continue
            documented={p['person']:p for p in f['persons'] if p['provenance']=='document'}
            people=[]
            for person in vf.PERSONS_BY_TENSE[f['label']]:
                if person in documented:people.append(documented[person]);continue
                guess=out[f['label']].get(person)
                if not guess:continue
                word,arabic=guess['word'],guess['arabic']
                if f['label']!='Command':word,arabic=vf.with_pronoun(person,word,arabic)
                item={'id':f['id']+':'+person,'person':person,'word':word,'arabic':arabic,'provenance':'inferred','checked':False}
                answer=checks.get(item['id'])
                if answer and answer.get('choice')=='yes' and answer.get('word')==word:item['checked']=True
                elif answer and answer.get('choice')=='fix' and (answer.get('word') or '').strip():
                    fixed,fixed_ar=answer['word'].strip(),(answer.get('arabic') or '').strip()
                    if f['label']!='Command':fixed,fixed_ar=vf.with_pronoun(person,vf.strip_pronoun(fixed),vf.strip_ar_pronoun(fixed_ar))
                    item.update(word=fixed,arabic=fixed_ar,checked=True,guess=word)
                people.append(item)
            # Documented persons the engine does not model (e.g. extra variants) stay.
            people+=[p for p in f['persons'] if p['provenance']=='document' and p['person'] not in vf.PERSONS_BY_TENSE[f['label']]]
            f['persons']=people
            if not f['word'] and people:
                lead=next((p for p in people if p['person']==('You (m)' if f['label']=='Command' else 'I')),people[0])
                f['word']=vf.strip_pronoun(lead['word']);f['arabic']=vf.strip_ar_pronoun(lead['arabic']);f['provenance']='inferred'
def main():
    p=argparse.ArgumentParser();p.add_argument('--document',type=Path);p.add_argument('--words',type=Path);p.add_argument('--output',type=Path);p.add_argument('--source-scripts',type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if a.source_scripts:sys.path.insert(0,str(a.source_scripts))
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from import_vocab import parse_markdown,parse_html,arabizi_forms,source_key,arabic_norm,source_arabic_forms,same_word
    from arabizi import loose
    document=a.document or max((root/'data/vocab').glob('doc_*.md'))
    words_path=a.words or root/'docs/data/words.json'
    vocabulary=json.loads(words_path.read_text(encoding='utf-8-sig'))
    words=vocabulary['items'];by_key={w['key']:w for w in words}
    source=(parse_html if document.suffix.lower() in ['.html','.htm'] else parse_markdown)(document.read_text(encoding='utf-8-sig'))
    def key(r):
        base=source_key(r);an=arabic_norm(source_arabic_forms(r)[0])
        # The importer may suffix a homograph whose Arabic is different. Resolve
        # that actual source record instead of binding every sense to the base.
        candidates=[w for k,w in by_key.items() if (k==base or re.fullmatch(re.escape(base)+r'~\d+',k)) and same_word(w.get('arabic_norm') or arabic_norm(w.get('arabic','')),an)]
        return candidates[0]['key'] if len(candidates)==1 else None
    def person(r):
        bits=r['arabizi'].split(' ',1)
        if len(bits)==1 and r['topic']=='Past Tense':
            who=re.match(r'^(I|He|She|We|They)\s+',r['english'],re.I)
            if who:
                pron={'i':'Ana','he':'huwwe','she':'heyye','we':'i7na','they':'humme'}[who[1].lower()]
                # Subject inferred from the documented English; lexical form
                # remains exactly the single word written by Amal.
                return {'person':PRONOUNS[pron.lower()],'word':pron+' '+r['arabizi'],'arabic':r['arabic'],'provenance':'document','key':key(r),'source_word':r['arabizi']}
        if len(bits)<2 or bits[0].lower() not in PRONOUNS:return None
        return {'person':PRONOUNS[bits[0].lower()],'word':r['arabizi'],'arabic':r['arabic'],'provenance':'document','key':key(r)}
    groups=[];claimed=set()
    for r in source:
        if r['topic']!='Verbs List' or not re.match(r'^Ana\s+b',r['arabizi'],re.I):continue
        k=key(r)
        if not k or k in claimed:continue
        name=re.sub(r'^Ana\s+','',arabizi_forms(r['arabizi'].replace('q/2','q').replace('2/q','2'))[0],flags=re.I)
        if '(' in name:continue # Meaning-changing combinations are attached below.
        terms=gloss(r['english']); entries=[]; keys=[k]
        base=name.lower();stem=base[2:] if base.startswith('ba') else None
        for tense in ['Past','Present','Future','Command']:
            people=[];formkeys=[];display='';arabic='';provenance='inferred'
            if tense=='Present':
                display=name;arabic=re.sub(r'^أنا\s+','',r['arabic']);people=[person(r)];formkeys=[k];provenance='document'
                if stem and re.fullmatch('[a-z0-9]+',base):
                    vowel=stem[0] in 'aeiou';suffix=base[1:] if vowel else stem
                    for pron,lab,prefix in [('inta','You (m)','bt' if vowel else 'bti'),('inti','You (f)','bt' if vowel else 'bti'),('huwwe','He','by' if vowel else 'bi'),('heyye','She','bt' if vowel else 'bti'),('i7na','We','bn' if vowel else 'bni'),('intu','You (pl)','bt' if vowel else 'bti'),('humme','They','by' if vowel else 'bi')]:
                        tail=re.sub('[ie]$','',suffix)+'u' if lab in ['You (pl)','They'] else suffix
                        people.append({'person':lab,'word':pron+' '+prefix+tail,'arabic':'','provenance':'inferred'})
            elif tense in ['Past','Command']:
                section='Past Tense' if tense=='Past' else 'Command Tense'
                matches=[x for x in source if x['topic']==section and terms.intersection(gloss(x['english']))]
                # English synonyms alone cannot identify a verb (basawwi != ba3mel).
                root_hint=consonants(stem or base[1:])
                # The source sometimes lists two full present alternatives
                # (basta5dem/basta3mel, bathonn/bazonn). Both documented roots
                # may identify the same source vocabulary record.
                present_variants=[re.sub(r'^Ana\s+','',v,flags=re.I).lower() for v in arabizi_forms(r['arabizi'])]
                root_hints={consonants(v[2:] if v.startswith('ba') else v[1:]) for v in present_variants if re.fullmatch(r'b[a-z0-9]+',v)} or {root_hint}
                if tense=='Past':
                    # Select a whole source paradigm by its I/you-m stem, not gloss alone.
                    blocks=[];block=[];seen_people=set()
                    for x in matches:
                        px=person(x)
                        if not px:continue
                        if px['person'] in seen_people:
                            blocks.append(block);block=[];seen_people=set()
                        block.append(x);seen_people.add(px['person'])
                    if block:blocks.append(block)
                    matching=[]
                    for block in blocks:
                        anchors=[x for x in block if re.match('^(Ana|inta) ',x['arabizi'],re.I)]
                        roots={consonants(re.sub(r'(?:et|it|t)$','',x['arabizi'].split(' ',1)[1].lower())) for x in anchors}
                        # Documented weak-final meet has lta2ayt, whose y is
                        # absent from present balte2i; do not generalize this
                        # exception to unrelated English synonyms.
                        meet=k=='ana balte2' and any(x['arabizi']=='Ana lta2ayt' for x in block)
                        if root_hints.intersection(roots) or meet:matching.append(block)
                    matches=matching[0] if len(matching)==1 else []
                else:
                    irregular={'ana ba23ud':'E3od / e3odi / e3odu','ana bAji':'Ta3aal / ta3ali / ta3alu'}
                    matches=[x for x in matches if consonants(x['arabizi'].split('/')[0].strip()) in root_hints or x['arabizi']==irregular.get(k)]
                # Distinct senses/forms must not be collapsed just because English overlaps.
                if tense=='Past':
                    starts=[i for i,x in enumerate(matches) if re.match('^Ana ',x['arabizi'],re.I)]
                    masculine=[x for x in matches if re.match('^inta ',x['arabizi'],re.I)]
                    if len(starts)==1 or not starts and len(masculine)==1:
                        people=[person(x) for x in matches if person(x)]
                        if len({x['person'] for x in people})!=len(people):people=[]
                        if people:
                            first=next((x for x in people if x['person']=='I'),None)
                            if first is None:
                                masculine_form=next(x for x in people if x['person']=='You (m)')
                                first={'person':'I','word':'Ana '+masculine_form['word'].split(' ',1)[1],'arabic':re.sub(r'^إنت\s+','أنا ',masculine_form['arabic']),'provenance':'inferred'}
                                people.insert(0,first)
                            display=first['word'].split(' ',1)[1];arabic=re.sub(r'^أنا\s+','',first['arabic']);formkeys=[x['key'] for x in people if x.get('key')];provenance=first['provenance']
                elif len(matches)==1:
                    x=matches[0];variants=arabizi_forms(x['arabizi'])
                    if len(variants)==3:
                        people=[{'person':lab,'word':v,'arabic':'','provenance':'document'} for lab,v in zip(['You (m)','You (f)','You (pl)'],variants)]
                        display=variants[0];arabic=x['arabic'];formkeys=[key(x)] if key(x) else [];provenance='document'
                    elif k=='ana basta5dem' and x['arabizi']=='Esta3mel / ista5dem':
                        # Two lexical alternatives, not masculine/feminine.
                        # Only this masculine form is explicitly documented.
                        display='ista5dem';arabic='استخدم';formkeys=[key(x)] if key(x) else [];provenance='document'
                        people=[{'person':'You (m)','word':display,'arabic':arabic,'provenance':'document','source_word':x['arabizi']}]
            elif tense=='Future' and stem and re.fullmatch('[a-z0-9]+',base):
                vowel=stem[0] in 'aeiou';suffix=base[1:] if vowel else stem
                for pron,lab,prefix in [('Ana','I','' if vowel else 'a'),('inta','You (m)','t' if vowel else 'ti'),('inti','You (f)','t' if vowel else 'ti'),('huwwe','He','y' if vowel else 'yi'),('heyye','She','t' if vowel else 'ti'),('i7na','We','n' if vowel else 'ni'),('intu','You (pl)','t' if vowel else 'ti'),('humme','They','y' if vowel else 'yi')]:
                    tail=re.sub('[ie]$','',suffix)+'u' if lab in ['You (pl)','They'] else suffix
                    people.append({'person':lab,'word':pron+' ra7 '+prefix+tail,'arabic':'','provenance':'inferred'})
                display=people[0]['word'][4:]
            # Source-taught doubled-middle pattern: fakkar/fakkaret, command fakker.
            # Restrict inference to this identifiable regular pattern; never overwrite a source form.
            if not display and stem and re.fullmatch(r'[a-z0-9]a([a-z0-9])\1e[a-z0-9]',stem):
                if tense=='Past':
                    past_stem=stem[:-2]+'a'+stem[-1]
                    people=[{'person':label,'word':pron+' '+past_stem+suffix,'arabic':'','provenance':'inferred'} for pron,label,suffix in [('Ana','I','et'),('inta','You (m)','et'),('inti','You (f)','ti'),('huwwe','He',''),('heyye','She','at'),('i7na','We','na'),('intu','You (pl)','tu'),('humme','They','u')]]
                    display=past_stem+'et';provenance='inferred'
                elif tense=='Command':
                    contracted=stem[:-2]+stem[-1]
                    people=[{'person':label,'word':word,'arabic':'','provenance':'inferred'} for label,word in [('You (m)',stem),('You (f)',contracted+'i'),('You (pl)',contracted+'u')]]
                    display=stem;provenance='inferred'
            if not display and tense=='Future' and base.startswith('ba') and ' ' in base:
                display='ra7 '+name[1:]
                people=[{'person':'I','word':'Ana '+display,'arabic':'','provenance':'inferred'}]
            if not display and tense=='Past' and k=='ana basA3ed' and 'saa3adet not sa3adet' in document.read_text(encoding='utf-8-sig'):
                # A documented example in prose was missed by table parsing.
                # Do not invent the rest of its person paradigm here.
                display='saa3adet';provenance='document'
                people=[{'person':'I','word':'Ana saa3adet','arabic':'','provenance':'document','source_note':'Past tense Notes: saa3adet not sa3adet; the long vowel is retained for I/you/we.'}]
            entries.append({'id':k+':'+tense.lower(),'label':tense,'word':display,'arabic':arabic,'provenance':provenance if display else 'needs-source','persons':people,'keys':formkeys,'uses':[]})
            keys.extend(formkeys)
        # Keep separate lexical uses only when the document supplies distinct meanings.
        for x in source:
            if x['topic']!='Verbs List' or not re.match(r'^Ana\s+'+re.escape(name)+r'\s*\(',x['arabizi'],re.I):continue
            xk=key(x)
            if not xk or xk==k or x['english']==r['english']:continue
            keys.append(xk)
            for f in entries:
                prep=re.search(r'\(([^)]+)\)',x['arabizi']).group(1)
                f['uses'].append({'id':xk,'preposition':prep,'meaning':x['english'],'word':(f['word']+' '+prep).strip(),'provenance':'document' if f['label']=='Present' else 'inferred'})
                if f['label']=='Present':f['keys'].append(xk)
        claimed.update(keys)
        groups.append({'id':k,'key':k,'keys':list(dict.fromkeys(keys)),'name':name,'arabic':re.sub(r'^أنا\s+','',r['arabic']),'english':r['english'],'topic':r['topic'],'type':'Verb','entries':entries,'root':'','pattern':r['subtopic'] if r['subtopic']!='Verbs List' else ''})
    # Correct the explicit source-linked Ba7ki example without using the lossy merged gloss.
    for g in groups:
        if g['key']=='ana ba7ki':
            past=g['entries'][0];pastrows=[x for x in source if x['topic']=='Past Tense' and re.search(r'\btalked\b',x['english'],re.I)]
            past['persons']=[person(x) for x in pastrows if person(x)];past['keys']=list(dict.fromkeys(x['key'] for x in past['persons'] if x.get('key')));past.update(word='7akait',arabic='حكيت',provenance='document');g['keys']=list(dict.fromkeys(g['keys']+past['keys']));g['root']='ح ك ي';g['pattern']='End-vowel verb'
        if g['key']=='ana bedi':
            wanted=[x for x in source if x['topic']=='Past Tense' and re.search(r'\bwanted\b',x['english'],re.I)]
            people=[]
            for x in wanted:
                label=re.sub(r'\s+wanted\s*$','',x['english'],flags=re.I).strip()
                if label not in {'I','You (m)','You (f)','You (pl)','We','He','She','They'}:continue
                variants=arabizi_forms(x['arabizi']);ar=source_arabic_forms(x)
                people.append({'person':label,'word':variants[1] if len(variants)>1 else variants[0],
                               'arabic':ar[1] if len(ar)>1 else ar[0], 'provenance':'document','key':key(x)})
            if len(people)==8 and all(p['key'] for p in people):
                past=g['entries'][0];first=next(p for p in people if p['person']=='I')
                past.update(persons=people,keys=[p['key'] for p in people],word=first['word'],arabic=first['arabic'],provenance='document')
                g['keys']=list(dict.fromkeys(g['keys']+past['keys']))
        if g['key']=='ana banbese6' and 'enbese6' in by_key:
            w=by_key['enbese6'];m=re.fullmatch(r'm:\s*(\S+)\s+f:\s*(\S+)\s+p:\s*(\S+)',w.get('plural',''))
            if '(command)' in w['english'] and m:
                command=g['entries'][3]
                command.update(word=m[1],arabic=w['arabic'],keys=['enbese6'],provenance='document',persons=[{'person':label,'word':m[i],'arabic':w['arabic'] if i==1 else '', 'provenance':'document'} for i,label in enumerate(['You (m)','You (f)','You (pl)'],1)])
                g['keys'].append('enbese6')
        if g['key']=='ana babse6' and 'byebse6' in by_key:
            w=by_key['byebse6']
            if w['english']=='It causes happiness / makes someone happy':
                present=g['entries'][1];present['keys'].append('byebse6');g['keys'].append('byebse6')
                present['persons']=[p for p in present['persons'] if p['person']!='He']+[{'person':'He','word':w['arabizi'],'arabic':w['arabic'],'provenance':'document','key':'byebse6'}]
    fill_verb_forms(groups, load_verb_checks(root))
    # The same first-person form also appears without Ana in topic tables
    # (Akalet in Food and Ana akalet in Past Tense). Keep both source keys,
    # but attach their histories to the same tense instead of a duplicate row.
    owned={k for g in groups for k in g['keys']}
    def first_person_signature(w):
        return (w['english'].strip().casefold(),
                re.sub(r'^انا\s+','',arabic_norm(w['arabic'])),
                loose(re.sub(r'^Ana\s+','',w['arabizi'],flags=re.I)))
    signatures={}
    for g in groups:
        for f in g['entries']:
            for fk in f['keys']:
                if fk in by_key:signatures.setdefault(first_person_signature(by_key[fk]),{})[f['id']]=(g,f)
    for w in words:
        if not w.get('active',True) or w['key'] in owned or not re.match(r'^I\s',w['english']):continue
        targets=signatures.get(first_person_signature(w),{})
        if len(targets)!=1:continue
        g,f=next(iter(targets.values()));f['keys'].append(w['key']);g['keys'].append(w['key']);owned.add(w['key']);claimed.add(w['key'])
    # Adjective gender forms are either explicit M/F rows or slash forms in the Doc.
    # Do not mistake transliteration alternatives (e.g. Su5un / Sukhun) for genders.
    adjectives=[r for r in source if r['topic']=='Adjectives']
    def meaning(r):
        return re.sub(r'\s*\((?:m|f|p|m\s*&\s*f)\)\s*','',r['english'],flags=re.I).strip().casefold()
    def marker(r):
        m=re.search(r'\((m\s*&\s*f|m|f|p)\)',r['english'],re.I)
        return re.sub(r'\s','',m.group(1).lower()) if m else ''
    def female_variant(v,base):
        if re.fullmatch(r'mishtaa[q2]a? la',v,re.I):
            return bool(re.fullmatch(r'mishtaa[q2]a la',v,re.I))
        return v!=base and bool(re.search(r'(?:a|e|iyye|iyya)$',v,re.I))
    for r in adjectives:
        k=key(r)
        if not k or k in claimed or marker(r) in ['f','p']:continue
        variants=arabizi_forms(r['arabizi']);base=variants[0]
        ar_parts=[x.strip() for x in r['arabic'].split('/')]
        male_ar=ar_parts[0]
        gender_forms=[];singular_keys=[k];keys=[k]
        female_rows=[x for x in adjectives if marker(x)=='f' and meaning(x)==meaning(r) and x['subtopic']==r['subtopic']]
        if marker(r)=='m' and len(female_rows)==1:
            female=female_rows[0];fk=key(female)
            gender_forms=[{'person':'Masculine','word':base,'arabic':male_ar,'provenance':'document'},
                          {'person':'Feminine','word':arabizi_forms(female['arabizi'])[0],'arabic':female['arabic'],'provenance':'document'}]
            if fk:singular_keys.append(fk);keys.append(fk)
        elif marker(r)=='m&f':
            gender_forms=[{'person':'Masculine / Feminine','word':base,'arabic':male_ar,'provenance':'document'}]
        elif len(variants)>1 and marker(r)!='m':
            fem=[v for v in variants[1:] if female_variant(v,base)]
            if fem:
                female_ar=''
                if len(ar_parts)>1:
                    female_ar=male_ar+'ة' if ar_parts[-1]=='ة' else ar_parts[-1]
                gender_forms=[{'person':'Masculine','word':base,'arabic':male_ar,'provenance':'document'},
                              {'person':'Feminine','word':' / '.join(fem),'arabic':female_ar,'provenance':'document'}]
        if not gender_forms:continue
        plural_rows=[x for x in adjectives if marker(x)=='p' and meaning(x)==meaning(r) and x['subtopic']==r['subtopic']]
        entries=[{'id':k+':singular','label':'Singular','word':' / '.join(v['word'] for v in gender_forms),
                  'arabic':' / '.join(dict.fromkeys(v['arabic'] for v in gender_forms if v['arabic'])),
                  'keys':singular_keys,'persons':gender_forms,'provenance':'document','uses':[]}]
        display_forms=list(gender_forms)
        if len(plural_rows)==1:
            p_row=plural_rows[0];pk=key(p_row)
            if pk:
                entries.append({'id':k+':plural','label':'Plural','word':p_row['arabizi'],'arabic':p_row['arabic'],'keys':[pk],'persons':[],'provenance':'document','uses':[]})
                keys.append(pk);display_forms.append({'person':'Plural','word':p_row['arabizi'],'arabic':p_row['arabic'],'provenance':'document'})
        claimed.update(keys)
        groups.append({'id':k,'key':k,'keys':list(dict.fromkeys(keys)),'name':base,'arabic':male_ar,'english':r['english'],
                       'topic':r['topic'],'type':'Adjective','entries':entries,'display_forms':display_forms,'root':'','pattern':''})
    # Preserve form-key ambiguity rather than assigning duplicate source keys twice.
    target=a.output or root/'docs/data/word-bank-catalog.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'version':2,'source':document.name,'source_exported':vocabulary.get('exported'),'groups':groups},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'verb_groups':sum(g['type']=='Verb' for g in groups),'adjective_groups':sum(g['type']=='Adjective' for g in groups),'entries':sum(len(g['entries']) for g in groups),'source_forms':sum(len(f['persons']) for g in groups for f in g['entries'])}))
if __name__=='__main__':main()
