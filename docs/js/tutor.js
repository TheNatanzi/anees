/* Tutor page (Medi 2026-09-26): everything Amal needs to check right now, one card each.
   List facts come from data/tutor.json; answered counts are read live from Supabase with each link's own token
   (the same header Amal's pages send). Nothing here writes anything. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = n => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('en-US');
  const day = s => s ? String(s).slice(0, 10) : '—';
  const PAGES = 'https://thenatanzi.github.io/anees/';

  async function rest(path, token) {
    const H = { apikey: ANEES.anon, Authorization: 'Bearer ' + ANEES.anon, 'X-Anees-Token': token };
    const r = await fetch(ANEES.url + '/rest/v1/' + path, { headers: H, cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  async function live(item) {
    try {
      if (item.kind === 'verb_check') {
        const rows = await rest('verb_check_links?select=answers,opened_at&token=eq.' + encodeURIComponent(item.token), item.token);
        const a = (rows[0] && rows[0].answers && rows[0].answers.answers) || {};
        const vals = Object.values(a), last = vals.map(v => v.updated_at).filter(Boolean).sort().pop();
        return { ok: !!rows[0], done: vals.length, right: vals.filter(v => v.choice === 'yes').length, fixed: vals.filter(v => v.choice === 'fix').length, last, opened: rows[0] && rows[0].opened_at };
      }
      if (item.kind === 'after' || item.kind === 'before') {
        const rows = await rest('amal_links?select=answers,opened_at,done_at&token=eq.' + encodeURIComponent(item.token), item.token);
        const a = (rows[0] && rows[0].answers) || {};
        const done = Object.keys(a.q || {}).length + Object.keys(a.h || {}).length + Object.keys(a.p || {}).length + Object.keys(a.s || {}).length;
        return { ok: !!rows[0], done, right: null, fixed: null, last: a.updated || null, opened: rows[0] && rows[0].opened_at, finished: !!(rows[0] && rows[0].done_at) };
      }
      if (item.kind === 'word_review') {
        const rows = await rest('transcript_review_links?select=answers,opened_at,done_at&token=eq.' + encodeURIComponent(item.token), item.token);
        const a = (rows[0] && rows[0].answers && rows[0].answers.answers) || {};
        const vals = Object.values(a), last = vals.map(v => v.updated_at).filter(Boolean).sort().pop();
        return { ok: !!rows[0], done: vals.length, right: vals.filter(v => v.choice === 'yes').length, fixed: vals.filter(v => v.choice === 'different').length, last };
      }
      if (item.kind === 'grammar_notes') {
        const rows = await rest('amal_rules?select=word_key,created_at&source=eq.grammar_notes&token=eq.' + encodeURIComponent(item.token), item.token);
        return { ok: true, done: rows.length, rules: new Set(rows.map(r => r.word_key)).size, last: rows.map(r => r.created_at).sort().pop() };
      }
      if (item.kind === 'materials') return { ok: true };
      if (item.kind === 'review') {
        const rows = (await rest('amal_rules?select=word_key,kind,created_at&source=eq.review&token=eq.' + encodeURIComponent(item.token), item.token))
          .filter(r => !String(r.word_key || '').startsWith('verify:'));   // "check these moments" answers share the token; they are not patterns
        const ids = new Set(rows.map(r => r.word_key)), last = rows.map(r => r.created_at).sort().pop();
        return { ok: true, done: ids.size, right: rows.filter(r => /correct/i.test(r.kind || '')).length, fixed: null, last };
      }
    } catch (e) { return { ok: false }; }
    return { ok: true };
  }

  function bar(done, total) {
    const pct = total ? Math.round(100 * done / total) : 0;
    return `<div class="tu-bar" role="img" aria-label="${pct}% done"><div class="tu-fill" style="width:${Math.max(done ? 2 : 0, pct)}%"></div></div>`;
  }

  function card(it, L) {
    const link = /^https?:/.test(it.url) ? it.url : PAGES + it.url;
    let big, sub, extra = '';
    if (it.kind === 'materials') {
      big = '8'; sub = 'topics · her explanations, inside Anees';
    } else if (it.kind === 'grammar_notes') {
      big = L && L.ok !== false ? fmt(L.done) : '—';
      sub = `new notes written here · ${fmt(it.doc_notes)} notes from her Doc shown under the rules`;
      extra = `<p class="tu-meta">last note ${L && L.last ? day(L.last) : 'none yet'} · link open until ${esc(it.expires)}</p>`;
    } else if (!L || L.ok === false) {
      big = '—'; sub = 'could not read her answers right now';
    } else {
      const left = Math.max(0, it.total - L.done);
      big = `${fmt(L.done)} <span class="tu-of">of ${fmt(it.total)}</span>`;
      sub = it.kind === 'review' ? `patterns answered · ${fmt(left)} left · ${fmt(it.moments)} moments inside`
        : it.kind === 'after' || it.kind === 'before' ? `questions answered · ${fmt(left)} left` + (L.finished ? ' · finished' : '')
        : it.kind === 'word_review' ? `lines answered · ${fmt(left)} left` : `forms answered · ${fmt(left)} left`;
      extra = bar(L.done, it.total);
      const bits = [];
      if (it.kind === 'verb_check' && L.done) bits.push(`${fmt(L.right)} right · ${fmt(L.fixed)} fixed`);
      bits.push('last answer ' + (L.last ? day(L.last) : 'none yet'));
      if (it.kind === 'verb_check' && L.done > (it.pulled || 0)) bits.push(`<b>${fmt(L.done - (it.pulled || 0))} answers not in the app yet</b>`);
      bits.push('link open until ' + it.expires);
      extra += `<p class="tu-meta">${bits.join(' · ')}</p>`;
    }
    // Menu, not copy links (Medi 2026-09-26): Open goes through the stable address so it keeps working when a token changes
    const go = { review: 'review', after: 'after', before: 'before', word_review: 'word-review', grammar_notes: 'grammar-notes', materials: 'materials' }[it.kind]
      || (it.kind === 'verb_check' ? (it.id.endsWith('-2') ? 'verb-check-2' : 'verb-check') : null);
    const href = go ? 'go.html?to=' + go : link;
    const buttons = [`<a class="tu-btn tu-primary" href="${esc(href)}">Open</a>`];
    return `<article class="tu-card"><div class="tu-top"><h2 class="tu-title">${esc(it.title)}</h2><span class="tu-who">${esc(it.who)}</span></div>
      <p class="tu-what">${esc(it.what)}</p><div class="tu-num"><span class="ab-number">${big}</span><span class="ab-tiny">${esc(sub)}</span></div>${extra}
      <div class="tu-actions">${buttons.join('')}</div></article>`;
  }

  async function main() {
    let T;
    try { T = await (await fetch('data/tutor.json', { cache: 'no-store' })).json(); }
    catch (e) { $('#tu-list').innerHTML = '<div class="vp-notice">tutor.json could not load. Refresh to retry.</div>'; return; }
    const lives = await Promise.all(T.open.map(live));
    const byId = Object.fromEntries(T.open.map((it, i) => [it.id, lives[i]]));
    const verbs = T.open.filter(x => x.kind === 'verb_check'), rv = T.open.find(x => x.kind === 'review');
    const verbLeft = verbs.reduce((n, x) => n + Math.max(0, x.total - ((byId[x.id] && byId[x.id].done) || 0)), 0);
    const notPulled = verbs.reduce((n, x) => n + Math.max(0, ((byId[x.id] && byId[x.id].done) || 0) - (x.pulled || 0)), 0);
    const lastAll = lives.map(l => l && l.last).filter(Boolean).sort().pop();
    $('#ab-metrics').innerHTML = [
      ['Open for Amal', T.open.length, 'lists waiting on her'],
      ['Verb forms left', fmt(verbLeft), 'across both verb lists'],
      ['Slip patterns left', rv && byId[rv.id] && byId[rv.id].ok !== false ? fmt(rv.total - byId[rv.id].done) : '—', 'correct him, or a reason'],
      ['Lesson questions left', fmt(T.open.filter(x => x.kind === 'after' || x.kind === 'before').reduce((n, x) => n + Math.max(0, x.total - ((byId[x.id] && byId[x.id].done) || 0)), 0)), 'after / before lesson links'],
      ['Grammar notes', (() => { const g = T.open.find(x => x.kind === 'grammar_notes'); const l = g && byId[g.id]; return l && l.ok !== false ? fmt(l.done) : '—'; })(), 'written on the rules page'],
      ['Not in the app yet', fmt(notPulled), 'her verb answers to pull'],
      ['Her last answer', lastAll ? day(lastAll) : '—', 'any list']
    ].map(([l, v, n]) => `<div class="ab-metric"><div class="ab-metric-label">${esc(l)}</div><div class="ab-number">${esc(v)}</div><div class="ab-tiny">${esc(n)}</div></div>`).join('');
    $('#tu-list').innerHTML = T.open.map((it, i) => card(it, lives[i])).join('');
    $('#tu-closed').innerHTML = (T.closed || []).map(c => `<li><b>${esc(c.title)}</b> · ${esc(c.why)}</li>`).join('');
    $('#ab-source').textContent = 'Live from her links · ' + new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    document.querySelectorAll('[data-copy]').forEach(b => b.onclick = async () => {
      try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = 'Copied'; } catch (e) { b.textContent = b.dataset.copy; }
    });
  }
  main();
})();
