// Anees doc sync (rule AM-20, Medi 2026-10-02). Runs under wc@adibs.com (an editor of Amal's Doc; the account Drive for
// desktop syncs to G:/My Drive on Medi's PC). Every hour: export Amal's "Arabic Full Vocabulary list" as markdown and
// write it to My Drive/Anees doc sync/amal-vocab-doc.md + amal-vocab-doc.status.json. The PC's hourly task
// (scripts/import_vocab.py) reads them. READ-ONLY on her Doc: drive.readonly can read it, drive.file can only touch the
// two files this script created (ai_rules N2: the app never writes the Doc). Source of truth: the anees repo,
// scripts/apps_script/doc_sync/. Set up once: run install() (creates the hourly trigger and exports once).
const DOC_ID = '1inA6ZeETtqJZHQYiZxtubWytsN5xh8_klQH50yRyrjw';
const FOLDER = 'Anees doc sync', MD = 'amal-vocab-doc.md', STATUS = 'amal-vocab-doc.status.json';
const MIN_CHARS = 20000;   // the Doc's markdown is ~130k chars; anything far shorter is a broken export, never written

function call_(method, url, opt) {
  opt = opt || {};
  opt.method = method;
  opt.muteHttpExceptions = true;
  opt.headers = Object.assign({ Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, opt.headers || {});
  return UrlFetchApp.fetch(url, opt);
}

function ok_(r, what) {
  if (r.getResponseCode() >= 300) throw new Error(what + ' HTTP ' + r.getResponseCode() + ': ' + r.getContentText().slice(0, 200));
  return r;
}

function ensure_(key, name, mimeType, parent) {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty(key);
  if (id) {
    const r = call_('get', 'https://www.googleapis.com/drive/v3/files/' + id + '?fields=id,trashed');
    if (r.getResponseCode() === 200 && !JSON.parse(r.getContentText()).trashed) return id;
  }
  const meta = { name: name, mimeType: mimeType };
  if (parent) meta.parents = [parent];
  const made = JSON.parse(ok_(call_('post', 'https://www.googleapis.com/drive/v3/files?fields=id',
    { contentType: 'application/json', payload: JSON.stringify(meta) }), 'create ' + name).getContentText());
  props.setProperty(key, made.id);
  return made.id;
}

function put_(id, text, mime) {
  ok_(call_('patch', 'https://www.googleapis.com/upload/drive/v3/files/' + id + '?uploadType=media',
    { contentType: mime + '; charset=utf-8', payload: Utilities.newBlob(text, mime + '; charset=utf-8').getBytes() }), 'write ' + id);
}

function exportDoc() {
  const props = PropertiesService.getScriptProperties();
  const now = new Date().toISOString();
  const st = { tried_at: now, ok_at: props.getProperty('ok_at'), error: null, chars: null, doc_modified: null, doc_id: DOC_ID };
  let folder = null;
  try {
    folder = ensure_('folder_id', FOLDER, 'application/vnd.google-apps.folder', null);
    const r = ok_(call_('get', 'https://www.googleapis.com/drive/v3/files/' + DOC_ID + '/export?mimeType=text%2Fmarkdown'), 'export');
    const md = r.getContentText('UTF-8');
    if (md.length < MIN_CHARS) throw new Error('export too short: ' + md.length + ' chars (expected ~130000)');
    const meta = JSON.parse(ok_(call_('get', 'https://www.googleapis.com/drive/v3/files/' + DOC_ID + '?fields=modifiedTime'), 'metadata').getContentText());
    put_(ensure_('md_id', MD, 'text/markdown', folder), md, 'text/markdown');
    st.ok_at = now; st.chars = md.length; st.doc_modified = meta.modifiedTime;
    props.setProperty('ok_at', now);
  } catch (e) {
    st.error = String(e && e.message || e).slice(0, 300);
  }
  if (folder) put_(ensure_('status_id', STATUS, 'application/json', folder), JSON.stringify(st, null, 1), 'application/json');
  if (st.error) throw new Error(st.error);   // shows as a failed execution in the Apps Script dashboard too
  return st;
}

function install() {
  ScriptApp.getProjectTriggers().filter(function (t) { return t.getHandlerFunction() === 'exportDoc'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('exportDoc').timeBased().everyHours(1).create();
  return exportDoc();
}
