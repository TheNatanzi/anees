/* Scored learner events that no catalog form can place (same test as the reliability audit's form_attributed check).
   Usage: node scripts/unplaced_scored_events.cjs 2026-09-21 [...dates]  -> JSON list of event ids. Read-only. */
const fs=require('fs'),path=require('path'),root=path.resolve(__dirname,'..'),C=require('../docs/js/word-bank-core.js'),R=require('../docs/js/word-bank-review.js');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^﻿/,''));
const dates=new Set(process.argv.slice(2)),raw=read('docs/data/word-bank-evidence.json').events,applied=R.apply(raw,read('docs/data/word-bank-review.json'));
const ev=C.prepareEvidence(applied.events),models=C.models(read('docs/data/words.json').items,read('docs/data/word-bank-catalog.json'),ev,[]);
const placed=new Set(models.flatMap(r=>r.entries.flatMap(f=>f.speaking.attempts.map(a=>a.id))));
console.log(JSON.stringify(ev.filter(e=>e.speaker==='Medi'&&dates.has(e.lesson_date)&&C.points(e)!==null&&!placed.has(e.id)).map(e=>e.id)));
