// AZ-12 (Medi 2026-10-09 "99% of the words said should come from amals arabic list ... if you strongly suspect a word to be
// on my list. You need to using the arabizi from our sheet." then "yes"): on a transcript line, a word that is HER sheet's
// word once the letters the engine swaps by sound are folded (ث=ت, ذ=ز, ظ=ض, ص=س, ط=ت, ق=ء, ة=ه) shows her sheet's
// Arabizi; the engine's Arabic stays underneath. Never a blind one-letter guess; his as-said forms win.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const A=require('../docs/js/word-bank-arabizi.js');
const W=[{arabic:'لسه',arabizi:'Lissa'},{arabic:'تلت',arabizi:'Tult'},{arabic:'ثانية',arabizi:'Saanie'},{arabic:'الظهر',arabizi:'Eldohur'},{arabic:'أمريكي',arabizi:'Amriki'},{arabic:'تقيل',arabizi:'T2eel'}];
const extra={words:{'ختيفتي':{latin:'5ateefti',method:'as-said',scope:'lessons'},'ثقيل':{latin:'t2eel-guess',method:'guess'}}};
const snap=A.create(W,{},extra,{scope:'lessons',snap:true}), plain=A.create(W,{},extra,{scope:'lessons'});
test('AZ-12 a sound-alike spelling of her word shows her Arabizi (ة/ه, ظ/ض, ث/ت, ق/ء)',()=>{
 assert.equal(snap('لسة').text,'Lissa');
 assert.equal(snap('الضهر').text,'Eldohur');
 assert.equal(snap('ثقيل').text,'T2eel');          // her sheet beats a guessed extra spelling
 assert.equal(plain('ثقيل').text,'t2eel-guess');   // only transcript views snap
});
test('AZ-12 no blind one-letter guess: three is not "a third", America is not "American"',()=>{
 assert.notEqual(snap('ثلاث').text,'Tult');
 assert.notEqual(snap('أمريكا').text,'Amriki');
});
test('AZ-12 his own wrong forms (as-said) stay as he said them; taanye stays taanye',()=>{
 assert.equal(snap('ختيفتي').text,'5ateefti');
 assert.notEqual(snap('تانية').text,'Saanie');
});
