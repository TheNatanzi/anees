// send_lesson_email.mjs — rich house-style email for Anees (Medi only, per the "never contact Amal" rule). Sends through the
// same Gmail app password as the Alchemy stack (alchemy-lock/.env); nodemailer is borrowed from alchemy-lock's node_modules.
//
//   node send_lesson_email.mjs "subject" payload.json
// payload: { headline, sub, rows:[{tag,name,detail}], link, button?, footer, text,
//            chart?: {title, bars:[{label,value,value2?}], legend?},   // house rule: chart on every email (table bars, no images)
//            log?:   [{t, text}] }                                       // house rule: log on every email

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const LOCK = 'C:/Claude/Personal/Project Alchemy/alchemy-lock';
const require = createRequire(path.join(LOCK, 'package.json'));
const nodemailer = require('nodemailer');

const env = {};
for (const line of fs.readFileSync(path.join(LOCK, '.env'), 'utf8').split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)=(.*)$/);
  if (m) env[m[1]] = m[2].trim();
}
const user = env.GMAIL_ADDRESS, pass = env.GMAIL_APP_PASSWORD;
if (!user || !pass) { console.error('GMAIL_ADDRESS / GMAIL_APP_PASSWORD missing'); process.exit(1); }

const TO = 'thenatanzi@gmail.com';   // hard-coded on purpose: only Medi
const [subject, payloadFile] = process.argv.slice(2);
const p = JSON.parse(fs.readFileSync(payloadFile, 'utf8'));
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const ink = '#1B2620', mut = '#5B6A62', line = '#D6DDD8', card = '#ffffff', bg = '#F4F6F2', teal = '#0F6E56', grey = '#9BAAA2', amber = '#B26F0E';

const rows = (p.rows || []).map(r => `
  <tr>
    <td style="padding:10px 12px;border-top:1px solid ${line};font:12px/1.3 system-ui;color:${teal};letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;vertical-align:top">${esc(r.tag || '')}</td>
    <td style="padding:10px 12px;border-top:1px solid ${line};font:16px/1.4 system-ui;color:${ink}">${esc(r.name || '')}<div style="font:13px/1.4 system-ui;color:${mut}">${esc(r.detail || '')}</div></td>
  </tr>`).join('');

let chart = '';
if (p.chart && p.chart.bars && p.chart.bars.length) {
  const mx = Math.max(1, ...p.chart.bars.map(b => Math.max(b.value || 0, b.value2 || 0)));
  const bar = (v, color) => `<td style="padding:2px 0;width:100%"><div style="background:${color};height:12px;width:${Math.max(2, Math.round(100 * (v || 0) / mx))}%;border-radius:6px"></div></td>`;
  const lines = p.chart.bars.map(b => `
    <tr><td style="font:12px system-ui;color:${mut};padding:2px 8px 2px 0;white-space:nowrap;vertical-align:top">${esc(b.label)}</td>
        <td style="width:100%"><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse"><tr>${bar(b.value, b.value2 == null ? amber : teal)}<td style="font:12px system-ui;color:${ink};padding-left:6px">${b.value ?? '–'}</td></tr>
        ${b.value2 == null ? '' : `<tr>${bar(b.value2, grey)}<td style="font:12px system-ui;color:${mut};padding-left:6px">${b.value2}</td></tr>`}</table></td></tr>`).join('');
  chart = `<div style="background:${card};border:1px solid ${line};border-radius:14px;padding:14px 16px;margin-top:12px">
    <div style="font:600 14px system-ui;color:${ink}">${esc(p.chart.title || 'Chart')}</div>
    <div style="font:12px system-ui;color:${mut};margin-bottom:8px">${esc(p.chart.legend || '')}</div>
    <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">${lines}</table></div>`;
}

let log = '';
if (p.log && p.log.length) {
  log = `<div style="background:${card};border:1px solid ${line};border-radius:14px;padding:14px 16px;margin-top:12px">
    <div style="font:600 14px system-ui;color:${ink};margin-bottom:6px">Log</div>
    ${p.log.map(l => `<div style="font:13px/1.5 system-ui;color:${ink}"><span style="color:${mut};font-variant-numeric:tabular-nums">${esc(l.t)}</span> &nbsp;${esc(l.text)}</div>`).join('')}</div>`;
}

const html = `<!doctype html><html><body style="margin:0;background:${bg};padding:16px;font-family:system-ui,sans-serif">
<div style="max-width:560px;margin:0 auto">
  <div style="background:${card};border:1px solid ${line};border-radius:14px;padding:18px 20px">
    <div style="font:12px/1.3 system-ui;color:${mut};letter-spacing:.08em;text-transform:uppercase">Anees</div>
    <div style="font:600 24px/1.25 system-ui;color:${ink};margin-top:6px">${esc(p.headline || subject)}</div>
    <div style="font:15px/1.5 system-ui;color:${mut};margin-top:6px">${esc(p.sub || '')}</div>
    ${p.link ? `<a href="${esc(p.link)}" style="display:inline-block;margin-top:14px;background:${teal};color:#fff;text-decoration:none;font:600 15px/1 system-ui;padding:12px 18px;border-radius:999px">${esc(p.button || 'Open the transcript')}</a>` : ''}
  </div>
  <table style="width:100%;border-collapse:collapse;background:${card};border:1px solid ${line};border-radius:14px;margin-top:12px;overflow:hidden">${rows}</table>
  ${chart}${log}
  <div style="font:12px/1.5 system-ui;color:${mut};margin:14px 4px 0">${esc(p.footer || '')}</div>
</div></body></html>`;

const tx = nodemailer.createTransport({ service: 'gmail', auth: { user, pass } });
const info = await tx.sendMail({ from: `Anees <${user}>`, to: TO, subject, text: p.text || p.headline || subject, html });
console.log('sent:', subject, info.messageId || '');
