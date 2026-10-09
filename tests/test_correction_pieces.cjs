// PR-22 (Medi's 10-08 notes, 2026-10-09): the one-box fix sees his whole joined sentence and saves each text fix on the
// piece it changes; the edge function gets the lines around (its prompt has {context}).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('fs'),path=require('path');
const P=require('../docs/js/correction-parse.js');
const parts=[{t:308.73,line:'Elion,'},{t:311.35,line:'ion el,'},{t:313.71,line:'ion el khamis,'}];
test('PR-22 a text item lands on the piece named by m:ss, else the piece that holds the words',()=>{
 assert.equal(P.pieceFor({parts},'ion el khamis','5:13').t,313.71);
 assert.equal(P.pieceFor({parts},'ion el khamis',null).t,313.71);
 const got=P.fromAI({items:[{kind:'text',engine_wrote:'ion el khamis',heard:'yoam el 5amees',at:'5:13'},{kind:'credit',word:'Elion'}]},'x',{parts,line:parts.map(p=>p.line).join(' '),who:'Medi'});
 assert.equal(got[0].payload.at,313.71);
 assert.equal(got[1].payload.credit,'independent');
});
test('PR-22 the page sends the lines around and saves on the right piece; the edge function reads {context}',()=>{
 const tc=fs.readFileSync(path.join(__dirname,'..','docs','js','transcript-corrections.js'),'utf8');
 assert.match(tc,/context: context \|\| ''/);
 assert.match(tc,/PR\.pieceFor\(ctx, r\.payload\.engine_wrote/);
 const ts=fs.readFileSync(path.join(__dirname,'..','supabase','functions','parse-correction','index.ts'),'utf8');
 assert.match(ts,/PROMPT\.replace\("\{context\}", context\)/);
 const pr=fs.readFileSync(path.join(__dirname,'..','supabase','functions','parse-correction','prompt.ts'),'utf8');
 assert.match(pr,/\{context\}/);
});
