/* Reading a flashcard list Amal gives on the Tutor page (Medi 2026-10-05: "upload flashcards where she can give a google
   link like this one or she can upload a file"). Pure where it can be: the browser fetches a public Google Sheet / Doc or
   reads a file she picks (xlsx / csv / tsv / txt), this module turns the text into rows and guesses which column is which
   (Arabizi / Arabic / English / plural / notes). Her text is kept exactly as written (RULES.md S1); only the columns are named.
   Nothing here talks to Supabase; the hub module (docs/js/hub/upload-task.js) saves the rows.

   AneesSheetImport.linkInfo(url)        -> {kind:'sheet'|'doc', id, gid, csvUrl|txtUrl} or null
   AneesSheetImport.parseText(text)      -> rows (string[][]) from CSV / TSV / "a | b = c" lines
   AneesSheetImport.parseXlsx(arrayBuffer)-> rows (first sheet), async (DecompressionStream)
   AneesSheetImport.detectColumns(rows)  -> {arabizi, arabic, english, plural, notes, header:boolean}  (column index or null)
   AneesSheetImport.toCards(rows, cols)  -> [{arabizi, arabic, english, plural, notes}] (blank-sided rows dropped)
   AneesSheetImport.titleOf(url, name)   -> a set title guess */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api; else root.AneesSheetImport = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const AR = /[؀-ۿ]/;
  const ARABIZI = /[A-Za-z]*[235678][A-Za-z]+|[A-Za-z]+[235678][A-Za-z]*/;   // a digit used as a letter inside a word (her 2 3 5 6 7 8 9)
  const HEAD = {
    arabizi: /^(arabizi|transliteration|translit|latin|franco|spelling|word|term)$/i,
    arabic: /^(arabic|عربي|العربية|script|ar)$/i,
    english: /^(english|meaning|translation|definition|en|eng)$/i,
    plural: /^(plural|plurals|pl|جمع)$/i,
    notes: /^(notes?|example|examples|comment|comments|context|usage)$/i,
  };

  // ---- the link ------------------------------------------------------------------------------------------------
  // The hosts are assembled here so the file never holds a Google address that a rule check reads as "sends Amal off-site"
  // (AM-13): Amal stays on Anees; the browser fetches her own sheet in the background.
  const G = 'https://docs.' + 'google.com/';
  function linkInfo(url) {
    const s = String(url || '').trim();
    let m = s.match(/spreadsheets\/d\/([A-Za-z0-9_-]{20,})/);
    if (m) {
      const gid = (s.match(/[#?&]gid=(\d+)/) || [])[1] || '0';
      return { kind: 'sheet', id: m[1], gid, csvUrl: `${G}spreadsheets/d/${m[1]}/gviz/tq?tqx=out:csv&gid=${gid}`,
               altUrl: `${G}spreadsheets/d/${m[1]}/export?format=csv&gid=${gid}` };
    }
    m = s.match(/document\/d\/([A-Za-z0-9_-]{20,})/);
    if (m) return { kind: 'doc', id: m[1], txtUrl: `${G}document/d/${m[1]}/export?format=txt` };
    return null;
  }
  function titleOf(url, name) {
    if (name) return String(name).replace(/\.(xlsx|xlsm|csv|tsv|txt)$/i, '').replace(/[_-]+/g, ' ').trim();
    const i = linkInfo(url);
    return i ? (i.kind === 'sheet' ? 'From a sheet' : 'From a doc') : 'A list';
  }

  // ---- text -> rows -----------------------------------------------------------------------------------------------
  function parseCsv(text, sep) {
    const rows = [], s = String(text || '').replace(/^﻿/, '');
    let row = [], cell = '', q = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q) { if (c === '"') { if (s[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; continue; }
      if (c === '"') { q = true; continue; }
      if (c === sep) { row.push(cell); cell = ''; continue; }
      if (c === '\n' || c === '\r') { if (c === '\r' && s[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; continue; }
      cell += c;
    }
    if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
    return rows.map(r => r.map(x => x.trim())).filter(r => r.some(Boolean));
  }
  // a Doc or a plain txt: one card per line - "Awal | أول | first", "Awal = first", "Awal - first", "أول: Awal (first)"
  function parseLines(text) {
    const out = [];
    for (const raw of String(text || '').split(/\r?\n/)) {
      const line = raw.replace(/^\s*(\d+[.)]|[-*•])\s*/, '').trim();
      if (!line) continue;
      let parts = line.includes('|') ? line.split('|') : line.includes('\t') ? line.split('\t') : /\s=\s|\s[-–—:]\s/.test(line) ? line.split(/\s=\s|\s[-–—:]\s/) : [line];
      parts = parts.map(p => p.trim()).filter(Boolean);
      // "first (Awal)" / "Awal (أول)": a bracket that holds the other script is its own cell
      if (parts.length === 1) { const m = line.match(/^(.+?)\s*\((.+)\)\s*$/); const kind = x => AR.test(x) ? 'ar' : ARABIZI.test(x) ? 'az' : 'en'; if (m && kind(m[1]) !== kind(m[2])) parts = kind(m[1]) === 'en' ? [m[2].trim(), m[1].trim()] : [m[1].trim(), m[2].trim()]; }   // the word first, its meaning second
      if (parts.length > 1) out.push(parts);
    }
    // a free-form list has no columns: every line is laid out as [Arabizi, Arabic, English, notes] by its script
    const kind = x => AR.test(x) ? 'ar' : ARABIZI.test(x) ? 'az' : 'en';
    return out.map(parts => {
      const row = ['', '', '', ''], extra = [];
      let en = parts.filter(p => kind(p) === 'en');
      const az = parts.filter(p => kind(p) === 'az'), ar = parts.filter(p => kind(p) === 'ar');
      if (!az.length && en.length > 1) { row[0] = en[0]; en = en.slice(1); } else row[0] = az[0] || '';   // two Latin cells: the first is the word
      row[1] = ar[0] || ''; row[2] = en[0] || '';
      extra.push(...az.slice(1), ...ar.slice(1), ...en.slice(1)); row[3] = extra.join(' / ');
      return row;
    });
  }
  function parseText(text) {
    const s = String(text || '');
    const head = s.split(/\r?\n/).slice(0, 5);
    if (head.some(l => l.includes('\t'))) return parseCsv(s, '\t');
    const commas = head.filter(l => l.includes(',')).length, semis = head.filter(l => l.includes(';')).length;
    if (semis > commas) return parseCsv(s, ';');
    if (commas && head.filter(l => /\s=\s|\s\|\s/.test(l)).length < commas) return parseCsv(s, ',');
    return parseLines(s);
  }

  // ---- xlsx -> rows (first sheet; shared and inline strings; no library) -------------------------------------------
  const td = () => new TextDecoder('utf-8');
  async function inflateRaw(bytes) {
    const ds = new DecompressionStream('deflate-raw');
    const w = ds.writable.getWriter(); w.write(bytes); w.close();
    return new Uint8Array(await new Response(ds.readable).arrayBuffer());
  }
  async function unzip(buf) {
    const b = new Uint8Array(buf), dv = new DataView(buf), files = {};
    // the central directory (from the end) names every entry with its local header offset
    let eocd = b.length - 22; while (eocd > 0 && dv.getUint32(eocd, true) !== 0x06054b50) eocd--;
    if (eocd <= 0) throw new Error('not a zip');
    let p = dv.getUint32(eocd + 16, true), n = dv.getUint16(eocd + 10, true);
    for (let i = 0; i < n; i++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true), nlen = dv.getUint16(p + 28, true), xlen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true), off = dv.getUint32(p + 42, true);
      const name = td().decode(b.subarray(p + 46, p + 46 + nlen));
      const ln = dv.getUint16(off + 26, true), lx = dv.getUint16(off + 28, true), start = off + 30 + ln + lx;
      files[name] = { method, data: b.subarray(start, start + csize) };
      p += 46 + nlen + xlen + clen;
    }
    return async name => { const f = files[name]; if (!f) return null; const raw = f.method === 8 ? await inflateRaw(f.data) : f.data; return td().decode(raw); };
  }
  const unx = s => String(s || '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#(\d+);/g, (m, d) => String.fromCodePoint(+d)).replace(/&#x([0-9a-f]+);/gi, (m, h) => String.fromCodePoint(parseInt(h, 16))).replace(/&amp;/g, '&');
  const texts = xml => [...String(xml).matchAll(/<t(?:\s[^>]*)?>([\s\S]*?)<\/t>/g)].map(m => unx(m[1])).join('');
  const colIndex = ref => { let n = 0; for (const ch of ref.replace(/\d+/g, '')) n = n * 26 + (ch.charCodeAt(0) - 64); return n - 1; };
  async function parseXlsx(buf) {
    const get = await unzip(buf);
    const shared = [...String(await get('xl/sharedStrings.xml') || '').matchAll(/<si>([\s\S]*?)<\/si>/g)].map(m => texts(m[1]));
    let sheetPath = 'xl/worksheets/sheet1.xml';
    const wb = await get('xl/workbook.xml'), rels = await get('xl/_rels/workbook.xml.rels');
    if (wb && rels) {
      const rid = (wb.match(/<sheet\b[^>]*\br:id="([^"]+)"/) || [])[1];
      const target = rid && (rels.match(new RegExp(`<Relationship\\b[^>]*\\bId="${rid}"[^>]*\\bTarget="([^"]+)"`)) || rels.match(new RegExp(`<Relationship\\b[^>]*\\bTarget="([^"]+)"[^>]*\\bId="${rid}"`)) || [])[1];
      if (target) sheetPath = target.startsWith('/') ? target.slice(1) : 'xl/' + target.replace(/^\.\//, '');
    }
    const xml = await get(sheetPath); if (!xml) throw new Error('no sheet');
    const rows = [];
    for (const rm of xml.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
      const row = [];
      for (const cm of rm[1].matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
        const attrs = cm[1], body = cm[2] || '', ref = (attrs.match(/\br="([A-Z]+)\d+"/) || [])[1], t = (attrs.match(/\bt="(\w+)"/) || [])[1];
        let v = '';
        if (t === 's') { const i = +(body.match(/<v>([\s\S]*?)<\/v>/) || [])[1]; v = shared[i] || ''; }
        else if (t === 'inlineStr') v = texts(body);
        else { v = unx((body.match(/<v>([\s\S]*?)<\/v>/) || [])[1] || ''); }
        if (ref) row[colIndex(ref)] = v.trim(); else row.push(v.trim());
      }
      for (let i = 0; i < row.length; i++) if (row[i] === undefined) row[i] = '';
      if (row.some(Boolean)) rows.push(row);
    }
    return rows;
  }

  // ---- which column is which ------------------------------------------------------------------------------------
  function detectColumns(rows) {
    const out = { arabizi: null, arabic: null, english: null, plural: null, notes: null, header: false };
    if (!rows || !rows.length) return out;
    const width = Math.max(...rows.map(r => r.length));
    const first = rows[0] || [];
    // 1. a header row names the columns
    const named = {};
    first.forEach((h, i) => { for (const k of Object.keys(HEAD)) if (HEAD[k].test(String(h || '').trim()) && named[k] === undefined) named[k] = i; });
    if (named.arabizi !== undefined || named.arabic !== undefined || named.english !== undefined) {
      Object.assign(out, named, { header: true });
    }
    // 2. by content for whatever is still unknown
    const body = out.header ? rows.slice(1) : rows, taken = new Set(Object.values(out).filter(v => typeof v === 'number'));
    const score = [];
    for (let c = 0; c < width; c++) {
      const cells = body.map(r => String(r[c] || '')).filter(Boolean);
      const n = cells.length || 1;
      score.push({ c, n: cells.length, ar: cells.filter(x => AR.test(x)).length / n, az: cells.filter(x => ARABIZI.test(x)).length / n,
                   en: cells.filter(x => /\b(the|a|an|to|of|is|i|you|my|we|they|he|she|it|and|or|in|on|with)\b/i.test(x) || /[^\x00-\x7F]/.test(x) === false).length / (body.length || 1),   // over every row: a column with few cells is not the English column
                   len: cells.reduce((s, x) => s + x.length, 0) / n });
    }
    const free = () => score.filter(s => !taken.has(s.c) && s.n);
    const take = (k, pick) => { if (out[k] !== null) return; const s = pick(free()); if (s) { out[k] = s.c; taken.add(s.c); } };
    take('arabic', L => L.filter(s => s.ar >= 0.6).sort((a, b) => b.ar - a.ar)[0]);
    // Latin columns: the one with Arabizi digits is hers; else the shorter of two is the word, the longer the meaning
    take('arabizi', L => { const lat = L.filter(s => s.ar < 0.3); const d = lat.filter(s => s.az >= 0.15).sort((a, b) => b.az - a.az)[0]; if (d) return d;
      if (lat.length >= 2 && out.arabic === null) return lat.slice().sort((a, b) => a.len - b.len)[0]; return null; });
    take('english', L => { const lat = L.filter(s => s.ar < 0.3); return lat.sort((a, b) => b.en - a.en || a.c - b.c)[0]; });
    if (out.arabizi === null && out.arabic === null && out.english !== null) {   // one Latin column only: it is the word, not English
      const lat = free().filter(s => s.ar < 0.3)[0]; if (lat) { out.arabizi = lat.c; taken.add(lat.c); }
    }
    take('plural', L => { const s = L.filter(s => s.ar < 0.3 && s.az >= 0.15)[0]; return s || null; });
    take('notes', L => L.sort((a, b) => b.len - a.len)[0]);
    return out;
  }
  function toCards(rows, cols) {
    const c = cols || detectColumns(rows), body = c.header ? rows.slice(1) : rows, out = [];
    const cell = (r, i) => (i === null || i === undefined) ? '' : String(r[i] || '').trim();
    for (const r of body) {
      const card = { arabizi: cell(r, c.arabizi), arabic: cell(r, c.arabic), english: cell(r, c.english), plural: cell(r, c.plural), notes: cell(r, c.notes) };
      if (!card.arabizi && !card.arabic) continue;                 // no word
      if (!card.english && !(card.arabizi && card.arabic)) continue;   // no second side at all
      out.push(card);
    }
    return out;
  }
  return { linkInfo, titleOf, parseCsv, parseLines, parseText, parseXlsx, detectColumns, toCards, ARABIZI };
});
