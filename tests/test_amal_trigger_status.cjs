const test=require('node:test'),assert=require('node:assert/strict');
const S=require('../docs/js/amal-trigger-status.js');
test('Settings line names unreadable sources with the reason and shows what moved',()=>{
 const L=S.lines({checked:'2026-09-29T10:00:00-07:00',sources:[{label:'Tutor',readable:true,n:3},{label:'Doc',readable:false,why:'private: HTTP 401'}],
  firings:[{at:'2026-09-29T10:15:00-07:00',changed:[{label:'Tutor'}],failures:[],numbers_moved:[{what:'Words %',from:80.8,to:81.2}],published:'pushed'}]});
 assert.match(L.head,/1 not readable/);assert.ok(L.sources.some(s=>/HTTP 401/.test(s)));
 assert.match(L.firings[0],/Words % 80.8 → 81.2/);assert.match(L.firings[0],/publish: pushed/);
});
test('no data -> says so',()=>{assert.match(S.lines(null).head,/not run yet/);});
