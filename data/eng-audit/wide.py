"""List elements wider than the 375 px viewport: python data/eng-audit/wide.py <page>"""
import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 375, 'height': 812}); pg.goto('http://127.0.0.1:8796/' + sys.argv[1]); pg.wait_for_load_state('networkidle')
    print(pg.evaluate("""()=>{const out=[];for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(r.right>376&&r.width>0){let p=e,clip=false;for(let q=e.parentElement;q;q=q.parentElement){const o=getComputedStyle(q).overflowX;if(o==='auto'||o==='scroll'||o==='hidden'){clip=true;break}}if(!clip)out.push(e.tagName+'.'+e.className+' right='+Math.round(r.right)+' '+(e.textContent||'').slice(0,50).replace(/\s+/g,' '))}}return out.slice(0,15)}"""))
    print(pg.evaluate('document.documentElement.scrollWidth'))
    b.close()
