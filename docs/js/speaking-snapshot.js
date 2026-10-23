/* The Speaking snapshot {release, stats, events} read from the tables in pages of 1,000 rows.
   Same shape and order as rpc/speaking_snapshot (events by lesson_date, id; stats by word_key), but no single request
   has to build the whole 11 MB answer: on 2026-09-23 the RPC passed anon's 3-second limit in 4 of 6 calls. */
(function (root) {
  'use strict';
  const PAGE = 1000, POOL = 3, TRIES = 3, WAIT_MS = 600;
  async function load(base, headers, fetchImpl) {
    const f = fetchImpl || root.fetch.bind(root);
    // 2026-10-22: ten pages at once made the server time out (500 on offsets 5000-9000 in 2 of 4 loads), and one failed
    // page dropped the whole lesson lane on Flashcards. Each page now retries, and at most POOL pages run at the same time.
    const get = async (path, extra) => {
      let last;
      for (let i = 0; i < TRIES; i++) {
        const r = await f(base + '/rest/v1/' + path, { headers: { ...headers, ...(extra || {}) }, cache: 'no-store' });
        if (r.ok) return { rows: await r.json(), range: r.headers.get('content-range') };
        last = Error('Data request failed (' + r.status + ')');
        if (r.status < 500 && r.status !== 429) break;
        if (i < TRIES - 1) await new Promise(res => setTimeout(res, WAIT_MS * (i + 1)));
      }
      throw last;
    };
    const pooled = async (items, fn) => {
      const out = new Array(items.length); let next = 0;
      await Promise.all(Array.from({ length: Math.min(POOL, items.length) }, async () => {
        while (next < items.length) { const k = next++; out[k] = await fn(items[k]); }
      }));
      return out;
    };
    const ev = 'speaking_events?select=data&order=lesson_date.asc,id.asc&limit=' + PAGE + '&offset=';
    const first = await get(ev + '0', { Prefer: 'count=exact' });
    const total = Number(String(first.range || '').split('/')[1]);
    const offsets = [];
    for (let o = PAGE; Number.isFinite(total) ? o < total : false; o += PAGE) offsets.push(o);
    const [rest, stats, release] = await Promise.all([
      pooled(offsets, o => get(ev + o)),
      get('word_stats?select=*&order=word_key.asc'),
      get('speaking_release?select=data'),
    ]);
    let events = first.rows.concat(...rest.map(p => p.rows)).map(r => r.data);
    if (!Number.isFinite(total) && first.rows.length === PAGE) {            // no count header: keep paging
      for (let o = PAGE; ; o += PAGE) { const p = await get(ev + o); events = events.concat(p.rows.map(r => r.data)); if (p.rows.length < PAGE) break; }
    }
    if (Number.isFinite(total) && events.length !== total) throw Error('Speaking evidence changed while loading');
    return { release: release.rows[0] ? release.rows[0].data : null, stats: stats.rows, events };
  }
  root.AneesSnapshot = { load };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.AneesSnapshot;
})(typeof window !== 'undefined' ? window : globalThis);
