// AM-17 (Medi 2026-10-02: "can you add an undo button to all these tutor hub stuff"): the shared Undo helper and the
// New words card's choice between this browser's saved answers and the live server answers.
// Real case 2026-10-02: Medi tapped "Forget it" on آها by accident; the row (id 2097) was removed server-side, but his
// browser kept the card hidden because its old local answer was merged over the live answers.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const U=require('../docs/js/amal-undo.js');
require('../docs/js/hub/new-words-task.js');
const NW=globalThis.AneesNewWordsTask;
const AHA='newword:2026-10-01:aha0000000';

test('AM-17 stale local answer yields to the server once it was sent (آها, row 2097 removed)',()=>{
 const local={[AHA]:{kind:'newword_forget',at:'2026-10-02T12:30:00Z'}};
 const server={};                                             // the row is gone on the server
 const shown=U.reconcile(local,server,[],true);              // nothing waiting in the queue: the server wins
 assert.equal(shown[AHA],undefined);
 const data={items:[{id:AHA,status:'open'}]};
 assert.equal(NW.count(data,shown).left,1);                  // the card is back
 // still waiting to be sent: this browser's tap is kept (offline taps are never lost)
 assert.equal(U.reconcile(local,server,[AHA],true)[AHA].kind,'newword_forget');
 // the server could not be read: keep what this browser has
 assert.equal(U.reconcile(local,server,[],false)[AHA].kind,'newword_forget');
});

test('AM-17 a build-time answer from this link that the live read no longer has is open again',()=>{
 const data={items:[{id:AHA,status:'forget',tap:'newword_forget',tap_token:'T'},{id:'newword:x',status:'add',tap:'newword_add_old',tap_token:'OLD'}]};
 const v=NW.liveView(data,{},'T',true);
 assert.equal(v[AHA].kind,'undo');                            // gone from the server -> open
 assert.equal(v['newword:x'],undefined);                      // answered on an older link: the build stays the truth
 assert.equal(NW.count(data,v).left,1);
 assert.deepEqual(NW.liveView(data,{},'T',false),{});         // no live read: nothing overridden
});

test('AM-17 latest action per item wins: tap -> undo -> tap',()=>{
 const rows=[{word_key:'P',kind:'audit_confirm'},{word_key:'P',kind:'undo'}];
 assert.equal(U.isAnswer(U.latest(rows).P),false);
 rows.push({word_key:'P',kind:'audit_skip'});
 assert.equal(U.latest(rows).P.kind,'audit_skip');
});

test('AM-17 the undo row copies the tap and never deletes',()=>{
 const r=U.row({token:'T',source:'after',lesson_date:'2026-10-01',kind:'right',word_key:'kalb',payload:{label:'Right'}},{t:12.5});
 assert.deepEqual([r.token,r.source,r.lesson_date,r.kind,r.word_key],['T','after','2026-10-01','undo','kalb']);
 assert.equal(r.payload.undoes,'right');assert.deepEqual(r.payload.match,{t:12.5});
 const q=[{body:{word_key:'a',kind:'x'}},{body:{word_key:'b',kind:'y'}}];
 assert.deepEqual(U.unqueue(q,j=>j.body.word_key==='a').map(j=>j.body.word_key),['b']);
 const log=U.log(U.log([],'v1',{choice:'yes'}),'v2',null);
 assert.deepEqual(log.map(x=>x.key),['v1','v2']);
});

test('AM-17 one button, one look',()=>{
 assert.match(U.button({'data-x':'1'}),/^<button type="button" class="an-undo" data-x="1"[^>]*>↶ Undo<\/button>$/);
 assert.match(U.answered('You said: right',{'data-y':'2'}),/class="an-answered".*You said: right.*class="an-undo"/);
});
