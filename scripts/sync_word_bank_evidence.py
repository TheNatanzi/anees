"""Install a previously verified evidence ledger without changing legacy scores.

Dry-run by default. Existing event IDs must be identical; reviewed evidence is
never overwritten or deleted. Does not send review links or activate the legacy
publisher. New Word Bank scores are derived in the browser from this ledger.
"""
import argparse, hashlib, json, sys
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(folder):
    folder=Path(folder)
    events=read(folder/'events.json'); stats=read(folder/'stats.json'); release=read(folder/'release.json')
    verification=read(folder/'verification.json'); checked=read(folder/'local-database-tests.json')
    revision=digest({'events':events,'stats':{s['word_key']:s for s in stats},'overlays':read(folder/'overlays.json')})
    if revision!=release['revision'] or checked['release_revision']!=revision:
        raise ValueError('Release integrity or database verification mismatch')
    if verification['events_checked']!=len(events) or any(verification[k]!='passed' for k in ['source_span_checks','overlap_checks','independent_arithmetic','python_browser_parity']):
        raise ValueError('Independent verification incomplete')
    for filename,expected in read(folder/'inputs.json').items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest()!=expected:
            raise ValueError('Source file changed; rebuild release')
    if len({e['id'] for e in events})!=len(events):raise ValueError('Duplicate event ID')
    return events,revision

def sync(folder,apply=False):
    events,revision=validate(folder)
    return sync_events(events,revision,apply)

def sync_events(events,revision,apply=False):
    """Insert-only install of already-built events (used by scripts/load_lesson.py too)."""
    import db
    current={r['id']:r['data'] for r in db.select('speaking_events',retries=1)}
    if any(e['id'] in current and current[e['id']]!=e for e in events):
        raise ValueError('Existing evidence differs; preserve it and reconcile explicitly')
    existing_words={r['key'] for r in db.select('words',{'select':'key'},retries=1)}
    if any(e.get('word_key') and e['word_key'] not in existing_words for e in events):
        raise ValueError('Source vocabulary identity missing')
    pending=[e for e in events if e['id'] not in current]
    report={'source_revision':revision,'verified_events':len(events),'new_events':len(pending),'lessons':sorted({e['lesson_date'] for e in events}),'applied':False}
    if not apply:return report
    # Transaction lock makes the conflict check and insert atomic. Only inserts:
    # raw source tables, legacy word_stats, flashcards and human revisions stay untouched.
    rows=[{'id':e['id'],'lesson_date':e['lesson_date'],'word_key':e.get('word_key'),'data':e} for e in events]
    for offset in range(0,len(rows),100):
        batch=rows[offset:offset+100]
        payload=json.dumps(batch,ensure_ascii=False).replace("'","''")
        sql="""begin;
    lock table public.speaking_events in share row exclusive mode;
    create temporary table bank_incoming on commit drop as select * from jsonb_populate_recordset(null::public.speaking_events,'"""+payload+"""'::jsonb);
    do $guard$ begin
     if exists(select 1 from bank_incoming i join public.speaking_events e using(id) where i.data is distinct from e.data) then
     raise exception 'Evidence changed since verification'; end if;
    end $guard$;
    insert into public.speaking_events(id,lesson_date,word_key,data) select id,lesson_date,word_key,data from bank_incoming on conflict(id) do nothing;
    commit;"""
        db.sql(sql,retries=1)
    actual={r['id']:r['data'] for r in db.select('speaking_events',retries=1)}
    if any(actual.get(e['id'])!=e for e in events):raise RuntimeError('Evidence readback failed')
    report['applied']=True
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--release',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--source-scripts',type=Path)
    a=p.parse_args()
    if a.source_scripts:sys.path.insert(0,str(a.source_scripts))
    print(json.dumps(sync(a.release,a.apply)))
