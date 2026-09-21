"""Publish a verified release transactionally; no emails or provider calls.

prepare: read-only live guards + private token/audio preparation.
apply: requires migration 014 already installed; compare locked table fingerprints,
       replace derived results, preserve raw/Flashcard data, verify readback.
"""
import argparse,base64,datetime,hashlib,json,secrets,subprocess
from pathlib import Path
import db
from build_speaking_release import read,save,filehash,ROOT

TABLES={'word_events':'id','word_stats':'word_key','card_results':'id','lessons':'date','words':'key','amal_rules':'id','lesson_events':'id','transcript_review_links':'token',
        'speaking_events':'id','speaking_release':'id','speaking_review_overlays':'id','speaking_review_links':'token','speaking_review_answers':'request_id'}
def literal(v):return "'"+str(v).replace("'","''")+"'"
def compact(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def existing_tables():
    return [r['tablename'] for r in db.sql("select tablename from pg_tables where schemaname='public'",retries=1) if r['tablename'] in TABLES]
def fingerprint_query(names):
    return 'select jsonb_build_object('+','.join(literal(t)+",(select md5(coalesce(jsonb_agg(to_jsonb(t) order by "+TABLES[t]+"),'[]'::jsonb)::text) from public."+t+' t)' for t in sorted(names))+') as fingerprints'
def prepare(folder,snapshot):
    folder=Path(folder);snapshot=Path(snapshot)
    if not (folder/'verification.json').exists() or not (folder/'local-database-tests.json').exists():raise RuntimeError('Complete independent and local database verification first')
    checked=read(folder/'local-database-tests.json')
    if checked.get('release_revision')!=read(folder/'release.json')['revision'] or checked.get('migration_sha256')!=filehash(ROOT/'supabase/migrations/014_speaking_evidence.sql'):
        raise RuntimeError('Database verification is stale; rerun local database tests')
    for table,key in TABLES.items():
        path=snapshot/(table+'.json')
        if not path.exists():continue
        params={'select':'lesson_date,created_at,expires_at,payload,answers,opened_at,done_at'} if table=='transcript_review_links' else {}
        live=db.select(table,params,retries=1);old=read(path)
        sortkey=(lambda r:compact(r)) if table=='transcript_review_links' else (lambda r:str(r[key]))
        if sorted(live,key=sortkey)!=sorted(old,key=sortkey):raise RuntimeError('Source changed since private snapshot: '+table)
    names=existing_tables();fingerprints=db.sql(fingerprint_query(names),retries=1)[0]['fingerprints']
    save(folder/'live-guard.json',{'tables':names,'fingerprints':fingerprints})
    # Reuse tokens/clips on rerun; never manufacture duplicate review links.
    if not (folder/'review-links.json').exists():
        events={e['id']:e for e in read(folder/'events.json')};inputs=read(folder/'inputs.json')
        recordings={digest:path for path,digest in inputs.items() if path.lower().endswith('.mp3')}
        clips=folder/'review-clips';clips.mkdir(exist_ok=True);links=[]
        for lesson in read(folder/'release.json')['lessons']:
            media={}
            for ident in lesson['review_queue']:
                e=events[ident];audio=recordings[e['source_sha256']]
                start=max(0,(e['local_start'] or 0)-6);duration=min(25,max(8,(e['local_end'] or start)-start+6))
                dest=clips/(ident+'.mp3')
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',audio,'-t',str(duration),'-vn','-codec:a','libmp3lame','-b:a','64k',str(dest)],check=True,capture_output=True)
                media[ident]='data:audio/mpeg;base64,'+base64.b64encode(dest.read_bytes()).decode()
            links.append({'token':secrets.token_urlsafe(32),'lesson_date':lesson['date'],
                          'expires_at':(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=30)).isoformat(),
                          'event_ids':lesson['review_queue'],'clips':media})
        save(folder/'review-links.json',links)
    print(json.dumps({'prepared':True,'guarded_tables':len(names),'private_reviews':len(read(folder/'review-links.json'))}))

def apply(folder):
    folder=Path(folder);guard=read(folder/'live-guard.json');release=read(folder/'release.json')
    if 'speaking_events' not in existing_tables():raise RuntimeError('Migration 014 must be approved and installed before apply')
    for p,h in read(folder/'inputs.json').items():
        if filehash(p)!=h:raise RuntimeError('Source changed: '+p)
    for p,h in read(folder/'code-hashes.json').items():
        if filehash(ROOT/p)!=h:raise RuntimeError('Scoring code changed after verification')
    events=read(folder/'events.json');stats=read(folder/'stats.json');overlays=read(folder/'overlays.json');links=read(folder/'review-links.json')
    # A previously acknowledged/ambiguous successful apply is verified, not repeated.
    current=db.select('speaking_release',retries=1)
    if current and current[0]['data']['revision']==release['revision']:
        return verify(folder)
    raw_guard={t:v for t,v in guard['fingerprints'].items() if not t.startswith('speaking_')}
    queries=['begin;','lock table '+','.join('public.'+t for t in guard['tables'])+' in share row exclusive mode;']
    check=fingerprint_query(guard['tables']).replace(' as fingerprints','')
    queries+=['do $guard$ begin if ('+check+') <> '+literal(compact(guard['fingerprints']))+"::jsonb then raise exception 'Evidence changed after preview'; end if; end $guard$;"]
    def insert(table,rows,on,where=None):
        if not rows:return
        columns=sorted(rows[0]);assert all(sorted(r)==columns for r in rows)
        names=','.join(columns);updates=','.join(k+'=excluded.'+k for k in columns if k!=on)
        queries.append('insert into public.'+table+' ('+names+') select '+names+' from jsonb_populate_recordset(null::public.'+table+','+literal(compact(rows))+'::jsonb) on conflict ('+on+') do update set '+updates+((' where '+where) if where else '')+';')
    insert('speaking_events',[{'id':e['id'],'lesson_date':e['lesson_date'],'word_key':e['word_key'],'data':e} for e in events],'id','speaking_events.data is distinct from excluded.data')
    dates=sorted({e['lesson_date'] for e in events})
    queries.append('delete from public.speaking_events where lesson_date::text in ('+','.join(map(literal,dates))+') and not (id in (select jsonb_array_elements_text('+literal(compact([e['id'] for e in events]))+'::jsonb)));')
    insert('word_stats',stats,'word_key',"(to_jsonb(word_stats)-'updated_at') is distinct from (to_jsonb(excluded)-'updated_at')")
    insert('speaking_review_overlays',[{'id':o['id'],'data':o} for o in overlays],'id','speaking_review_overlays.data is distinct from excluded.data')
    insert('speaking_review_links',links,'token')
    insert('speaking_release',[{'id':True,'data':release}],'id')
    queries.append('commit;')
    # Keep the exact guarded SQL private for audit/rollback investigation.
    sql='\n'.join(queries);(folder/'applied-transaction.sql').write_text(sql,encoding='utf-8')
    db.sql(sql,retries=1)
    receipt=verify(folder);save(folder/'published.json',receipt);return receipt

def verify(folder):
    folder=Path(folder);expected=read(folder/'release.json')
    live=db.rest('GET','rpc/speaking_snapshot',retries=1)
    assert live['release']==expected,'Release differs'
    assert {e['id']:e for e in live['events']}=={e['id']:e for e in read(folder/'events.json')},'Ledger readback differs'
    actual={s['word_key']:s for s in live['stats']}
    for s in read(folder/'stats.json'):
        for k,v in s.items():
            got=actual[s['word_key']][k]
            if k=='last_reviewed' and got and v:assert got.replace('+00:00','Z')==v.replace('+00:00','Z')
            else:assert got==v,(s['word_key'],k)
    guard=read(folder/'live-guard.json')
    unchanged=[t for t in guard['tables'] if t!='word_stats' and not t.startswith('speaking_')]
    now=db.sql(fingerprint_query(unchanged),retries=1)[0]['fingerprints']
    assert all(now[t]==guard['fingerprints'][t] for t in unchanged),'Raw source changed'
    return {'revision':expected['revision'],'ledger_rows':len(live['events']),'stats_rows':len(actual),'raw_sources_and_cards_unchanged':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','apply','verify']);p.add_argument('--release',required=True);p.add_argument('--snapshot')
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.release,a.snapshot)
    else:print(json.dumps(apply(a.release) if a.mode=='apply' else verify(a.release)))
