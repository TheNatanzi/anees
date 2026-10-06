/* PG-31 (Medi 2026-10-06, "This top bar is really bothering me" -> Option 1): on a phone the ten menu links wrapped into four
   rows and pushed every page a screen down. Now a phone shows a bottom tab bar with the five daily destinations - Progress,
   Lessons, Cards, Student, More - and More opens a sheet with the other links. The bar is built from the page's own
   sidebar links (same labels, same current-page mark), so a page with the shared menu gets it for free; laptops keep the
   sidebar. Research behind the choice: plan/PHONE-NAV-2026-10-06.md (Nielsen Norman Group on hidden menus, Apple HIG and
   Material 3 on 3-5 tab destinations). */
(function () {
  if (typeof document === 'undefined') return;
  const MQ = '(max-width: 680px)';
  const TABS = [['progress.html', 'Progress'], ['lessons.html', 'Lessons'], ['cards.html', 'Cards'], ['student.html', 'Student']];
  const css = `
@media ${MQ} {
  #anees-bank aside nav { display: none !important; }
  #anees-bank aside { padding: 8px 14px; }
  #anees-bank main { padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px)) !important; }
  .pn-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 40; display: grid; grid-template-columns: repeat(5, 1fr); gap: 2px; padding: 6px 6px calc(8px + env(safe-area-inset-bottom, 0px));
            background: var(--ab-panel, #1e2a26); border-top: 1px solid var(--ab-line, #33423c); }
  .pn-tab { display: grid; justify-items: center; gap: 3px; padding: 6px 2px; border: 0; border-radius: 10px; background: transparent; color: var(--ab-muted, #9aa69f); font: 600 11px var(--sabz-font-sans, system-ui, sans-serif); text-decoration: none; min-height: 48px; }
  .pn-tab i { width: 20px; height: 20px; border-radius: 6px; border: 1.5px solid currentColor; display: block; }
  .pn-tab[aria-current="page"] { color: var(--ab-accent, #7fb59a); background: var(--ab-active, rgba(127,181,154,.12)); }
  .pn-tab[aria-current="page"] i { background: currentColor; }
  .pn-sheet { position: fixed; inset: 0; z-index: 41; background: rgba(0,0,0,.45); display: none; }
  .pn-sheet[open] { display: block; }
  .pn-sheet > div { position: absolute; left: 0; right: 0; bottom: 0; background: var(--ab-panel, #1e2a26); border-top: 1px solid var(--ab-line, #33423c); border-radius: 18px 18px 0 0; padding: 10px 14px calc(16px + env(safe-area-inset-bottom, 0px)); display: grid; gap: 4px; }
  .pn-sheet h2 { font: 600 11px var(--sabz-font-sans, system-ui, sans-serif); letter-spacing: .12em; text-transform: uppercase; color: var(--ab-muted, #9aa69f); margin: 4px 0 6px; }
  .pn-sheet a { display: block; padding: 12px 10px; border-radius: 10px; color: var(--ab-text, #e9ede8); text-decoration: none; font: 500 16px var(--sabz-font-sans, system-ui, sans-serif); }
  .pn-sheet a[aria-current="page"] { background: var(--ab-active, rgba(127,181,154,.12)); color: var(--ab-accent, #7fb59a); }
  .pn-sheet button { margin-top: 6px; min-height: 44px; border: 1px solid var(--ab-line, #33423c); background: transparent; color: var(--ab-text, #e9ede8); border-radius: 10px; font: 600 14px var(--sabz-font-sans, system-ui, sans-serif); }
}
@media (min-width: 681px) { .pn-bar, .pn-sheet { display: none !important; } }`;
  function build() {
    const nav = document.querySelector('#anees-bank aside nav'); if (!nav || document.querySelector('.pn-bar')) return;
    // four pages (Lessons, Word Bank, Grammar, Settings) mark their own entry as a <button> with no href: it is this page
    const here = (location.pathname.split('/').pop() || 'progress.html').replace(/^$/, 'progress.html');
    const links = [...nav.querySelectorAll('a.ab-nav, button.ab-nav')].map(a => ({ href: a.getAttribute('href') || here, label: a.textContent.trim(), cur: a.getAttribute('aria-current') === 'page' }));
    if (!links.length) return;
    const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
    const byHref = h => links.find(l => l.href === h);
    const main = TABS.map(([h, label]) => { const l = byHref(h); return l ? { ...l, label } : null; }).filter(Boolean);
    const rest = links.filter(l => !TABS.some(([h]) => h === l.href));
    const moreCur = rest.some(l => l.cur);
    const bar = document.createElement('nav'); bar.className = 'pn-bar'; bar.setAttribute('aria-label', 'Phone menu');
    bar.innerHTML = main.map(l => `<a class="pn-tab" href="${l.href}"${l.cur ? ' aria-current="page"' : ''}><i></i>${l.label}</a>`).join('')
      + `<button type="button" class="pn-tab" id="pn-more"${moreCur ? ' aria-current="page"' : ''} aria-haspopup="dialog" aria-expanded="false"><i></i>More</button>`;
    const sheet = document.createElement('div'); sheet.className = 'pn-sheet'; sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-label', 'More pages');
    sheet.innerHTML = `<div><h2>More</h2>${rest.map(l => `<a href="${l.href}"${l.cur ? ' aria-current="page"' : ''}>${l.label}</a>`).join('')}<button type="button" id="pn-close">Close</button></div>`;
    document.body.appendChild(bar); document.body.appendChild(sheet);
    const more = bar.querySelector('#pn-more'), open = v => { if (v) sheet.setAttribute('open', ''); else sheet.removeAttribute('open'); more.setAttribute('aria-expanded', String(v)); };
    more.onclick = () => open(!sheet.hasAttribute('open'));
    sheet.querySelector('#pn-close').onclick = () => open(false);
    sheet.addEventListener('click', e => { if (e.target === sheet) open(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') open(false); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build); else build();
})();
