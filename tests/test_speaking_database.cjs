// Runs entirely in an ephemeral local PostgreSQL instance. Never connects to Supabase.
const {PGlite}=require(process.env.PGLITE_MODULE||'@electric-sql/pglite');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
require('../docs/js/buckets.js');
const root=path.resolve(__dirname,'..'),work=path.resolve(process.argv[2]);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
async function main(){
 const db=new PGlite();
 await db.exec('create role anon; create role authenticated; create role service_role bypassrls;');
 for(const file of fs.readdirSync(path.join(root,'supabase/migrations')).filter(f=>/^0\d\d_/.test(f)).sort()){
  if(file.startsWith('014_'))await db.exec('grant select on all tables in schema public to anon; revoke create on schema public from public;');
  try{await db.exec(fs.readFileSync(path.join(root,'supabase/migrations',file),'utf8'));}catch(e){throw Error(file+': '+e.message);}
 }
 const load=async(table,rows)=>{if(!rows.length)return;const keys=Object.keys(rows[0]);await db.query(`insert into ${table} (${keys.join(',')}) select ${keys.join(',')} from jsonb_populate_recordset(null::${table},$1::jsonb)`,[JSON.stringify(rows)]);};
 await load('words',read(path.join(work,'snapshot/words.json')));
 await load('word_stats',read(path.join(work,'release/stats.json')));
 await load('speaking_events',read(path.join(work,'release/events.json')).map(data=>({id:data.id,lesson_date:data.lesson_date,word_key:data.word_key,data})));
 await load('speaking_release',[{id:true,data:read(path.join(work,'release/release.json'))}]);
 const stats=read(path.join(work,'release/stats.json'));
 let count=0;
 // Test all actual transition contexts plus explicit mastery/recovery edge cases.
 const cases=stats.map(s=>s.progress_context);
 for(const signals of [['missed','cold','cold'],['missed','cold','missed'],['cold','cold','cold','cold','cold'],['cold','shaky','cold'],['missed']]){
  cases.push({version:3,new:false,cards:[],lessons:signals.map((s,i)=>[`2026-09-${String(i+1).padStart(2,'0')}`,s,s==='cold']),speaking:{times_seen:0,independent_uses:0,times_missed:0,last_reviewed:null,seen_lessons:0,intro_uses:0,new_since:null}});
 }
 for(const ctx of cases){
  const expected=AneesBuckets.progressFromContext(ctx);
  const sql=(await db.query('select speaking_progress($1::jsonb) result',[JSON.stringify(ctx)])).rows[0].result;
  assert.deepEqual(sql,{...expected.progress_scores.speaking,lesson_signal:expected.lesson_signal});count++;
 }
 const e=(await db.query("select * from speaking_events where lesson_date='2026-09-10' and word_key='mnIh' and data->>'assessment'='helped'")).rows[0];
 assert(e);
 const before=(await db.query('select progress_scores from word_stats where word_key=$1',[e.word_key])).rows[0].progress_scores;
 const token='t'.repeat(43),other='z'.repeat(43);
 await db.query("insert into speaking_review_links(token,lesson_date,expires_at,event_ids) values($1,$2,now()+interval '1 day',$3::jsonb)",[token,e.lesson_date,JSON.stringify([e.id])]);
 await db.exec('set role anon');
 const denied=async(sql,args=[])=>{let refused=false;try{await db.query(sql,args);}catch(err){refused=true;}assert(refused,'Expected rejection: '+sql);};
 for(const table of ['speaking_review_overlays','speaking_event_revisions','speaking_review_links','speaking_review_answers'])await denied('select * from '+table);
 await denied("update speaking_events set word_key='mnIh'");
 await denied("select refresh_speaking_word('mnIh')");
 await denied('select get_speaking_review()');
 await db.query("select set_config('request.headers',$1,false)",[JSON.stringify({'x-anees-token':other})]);
 await denied('select get_speaking_review()');
 await db.query("select set_config('request.headers',$1,false)",[JSON.stringify({'x-anees-token':token})]);
 const q=(await db.query('select get_speaking_review() r')).rows[0].r;
 assert.equal(q.events.length,1);
 const call='select review_speaking_event($1,$2,$3,$4,$5,$6,$7) r';
 const args=[e.id,q.events[0].expected,'incorrect',true,e.word_key,'local test only','request-000000000001'];
 await denied(call,[e.id,null,...args.slice(2)]);
 await denied(call,['not-in-this-review',...args.slice(1)]);
 await denied(call,[e.id,'0'.repeat(32),...args.slice(2)]);
 await db.query(call,args);
 const replay=(await db.query(call,args)).rows[0].r;assert.equal(replay.replayed,true);
 await denied(call,[...args.slice(0,2),'independent',...args.slice(3)]); // request ID cannot hide a different answer
 const after=(await db.query('select progress_scores from word_stats where word_key=$1',[e.word_key])).rows[0].progress_scores;
 assert.deepEqual(before.flashcards,after.flashcards);
 assert.equal(after.speaking.bucket,'missed');
 assert.equal(after.speaking.times_seen,before.speaking.times_seen);
 const latest=(await db.query('select get_speaking_review() r')).rows[0].r;
 assert(latest.events[0].saved);
 assert.equal(latest.events[0].event.assessment_status,'human_reviewed');
 await denied(call,[...args.slice(0,6),'request-000000000002']); // old etag fails
 const second=[e.id,latest.events[0].expected,'unresolved',false,e.word_key,'inaudible','request-000000000003'];
 await db.query(call,second);
 const un=(await db.query('select progress_scores from word_stats where word_key=$1',[e.word_key])).rows[0].progress_scores;
 assert.deepEqual(un.flashcards,before.flashcards);
 assert.equal(un.speaking.times_seen,before.speaking.times_seen-1);
 await db.exec('reset role');
 const history=(await db.query('select count(*)::int n from speaking_event_revisions where event_id=$1',[e.id])).rows[0].n;assert.equal(history,2);
 // Recompute every word through the server path and compare against browser replay.
 for(const s of stats){
  if(s.word_key===e.word_key)continue;
  await db.query('select refresh_speaking_word($1)',[s.word_key]);
  const current=(await db.query('select progress_context,progress_scores from word_stats where word_key=$1',[s.word_key])).rows[0];
  assert.deepEqual(current.progress_scores.speaking,AneesBuckets.progressFromContext(current.progress_context).progress_scores.speaking);
  assert.deepEqual(current.progress_scores.flashcards,s.progress_scores.flashcards);
  assert.deepEqual(current.progress_scores.speaking,s.progress_scores.speaking);
 }
 const report={database:'ephemeral PGlite PostgreSQL',release_revision:read(path.join(work,'release/release.json')).revision,migration_sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'supabase/migrations/014_speaking_evidence.sql'))).digest('hex'),transition_cases:count,permissions:'anonymous writes/private reads denied',review:'token binding, stale/null etag, idempotency, partial save, reversal, flashcard isolation passed',revision_entries:history};
 fs.writeFileSync(path.join(work,'release/local-database-tests.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await db.close();
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
