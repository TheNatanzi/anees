// node tests/test_verb_check.cjs — pure logic of Amal's verb check list.
const assert=require('assert');
const VC=require('../docs/js/verb-check-core.js');
const p={schema_version:1,kind:'verb-forms',
 items:{'a:present:You (f)':{tense:'Present',person:'You (f)',word:'inti bte3rafi',arabic:'إنتي بتعرفي'},
        'a:past:She':{tense:'Past',person:'She',word:'heyye 3irfat',arabic:'هي عرفت'}},
 verbs:[{key:'a',name:'ba3raf',arabic:'بعرف',english:'I know',ids:['a:present:You (f)','a:past:She']}]};
assert.ok(VC.validPayload(p));
assert.ok(!VC.validPayload({...p,verbs:[{...p.verbs[0],ids:['a:past:She']}]}),'every item must sit under a verb');
let a={};
a=VC.answer(p,a,'a:present:You (f)','yes',null,null,'t1');
assert.deepStrictEqual(a['a:present:You (f)'],{choice:'yes',word:'inti bte3rafi',arabic:'إنتي بتعرفي',updated_at:'t1'},'yes repeats the guess exactly');
a=VC.answer(p,a,'a:past:She','fix','',' ','t2');
assert.ok(!('a:past:She' in VC.sendable(a)),'an empty fix stays a local draft');
assert.deepStrictEqual(VC.progress(p,a),{total:2,finished:1,fixes:0,verbs:1,verbsDone:0});
a=VC.answer(p,a,'a:past:She','fix','heyye 3erfat','','t3');
assert.ok('a:past:She' in VC.sendable(a));
assert.strictEqual(VC.progress(p,a).verbsDone,1);
a=VC.answer(p,a,'a:past:She',null);
assert.ok(!('a:past:She' in a),'tapping again clears the answer');
assert.deepStrictEqual(VC.byTense(p,p.verbs[0]).map(t=>t.tense),['Present','Past']);
assert.ok(VC.validState(p,{schema_version:1,revision:3,answers:a}));
assert.ok(!VC.validState(p,{schema_version:1,revision:3,answers:{nope:{choice:'yes',word:'',arabic:'',updated_at:''}}}));
assert.throws(()=>VC.answer(p,a,'missing','yes'));
// level-2 add-on lists are a second, separate kind
{const p={schema_version:1,kind:'verb-addons',items:{'v:addon:obj':{tense:'Level 2',person:'I · + him (ending)',word:'Ana ba3rafo',arabic:'أنا بعرفو'}},verbs:[{key:'v',name:'ba3raf',arabic:'بعرف',english:'I know',ids:['v:addon:obj']}]};
 assert.strictEqual(VC.validPayload(p),true);assert.deepStrictEqual(VC.byTense(p,p.verbs[0]).map(t=>t.tense),['Level 2']);
 assert.strictEqual(VC.validPayload({...p,kind:'verb-forms'}),false);}
console.log('verb check core: ok');
