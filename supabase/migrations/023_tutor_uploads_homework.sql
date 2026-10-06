-- Tutor page "Upload flashcards" + "Assign homework" + Medi's STUDENT tab (Medi 2026-10-05: "Lets add something at the top
-- of the tutor for 'upload flashcards' where she can give a google link like this one or she can upload a file. Subsequently
-- we need add a student tab now where she can assign me work ... lets also create a box for her 'assign homework'").
-- Grill answers 2026-10-05: storage = Supabase like her taps (the browser reads the link / file and saves rows; the hourly job
-- rebuilds the pages); AI checks first, Amal confirms or overrules; homework has its own number.
-- Same access pattern as transcript_corrections (022): anon may read and insert, nothing else; append-only; an undo is a
-- new row with `undoes`. Amal's rows carry the token of the Tutor link she used (provenance only). The AI check is written
-- by the check-homework edge function with the service key. Low security posture by Medi's choice (PR-02).

create table if not exists amal_uploads (
  id text primary key check (char_length(id) between 8 and 64),     -- client uuid: offline queue replays are idempotent
  kind text not null check (kind in ('upload', 'undo')),
  undoes text,                                                       -- id of the upload this row undoes
  title text check (title is null or char_length(title) <= 200),
  source text check (source is null or source in ('sheet', 'doc', 'file', 'paste')),
  source_ref text check (source_ref is null or char_length(source_ref) <= 500),   -- the link or the file name
  keep text check (keep is null or keep in ('permanent', 'temporary')),           -- Q6/Q7: permanent = remind her to add to the Doc
  columns jsonb check (columns is null or pg_column_size(columns) < 2000),        -- {arabizi: 0, arabic: 1, english: 2, plural: null, notes: null}
  rows jsonb check (rows is null or pg_column_size(rows) < 400000),              -- [{arabizi, arabic, english, plural, notes}] as she wrote them (S1)
  n int check (n is null or (n >= 0 and n <= 5000)),
  token text,                                                        -- the Tutor link she used (amal_links.token); not checked, provenance only
  created_at timestamptz not null default now()
);
comment on table amal_uploads is 'Amal''s flashcard uploads from the Tutor page (a Google Sheet / Doc link or a file). Append-only; undo = a new row with undoes.';

create table if not exists homework_tasks (
  id text primary key check (char_length(id) between 8 and 64),
  kind text not null check (kind in ('translate', 'create', 'question', 'cards', 'undo')),
  undoes text,
  prompt text check (prompt is null or char_length(prompt) <= 2000),              -- the sentence / the question
  direction text check (direction is null or direction in ('en_ar', 'ar_en')),     -- Q4: translate both ways, Amal picks per sentence
  words jsonb check (words is null or pg_column_size(words) < 4000),               -- create: the words he must use
  context text check (context is null or char_length(context) <= 2000),            -- question: optional context
  set_ref text check (set_ref is null or char_length(set_ref) <= 120),             -- cards: the Flashcards tile (q:<set>, u:<upload>, shaky)
  set_title text check (set_title is null or char_length(set_title) <= 200),
  n_cards int check (n_cards is null or (n_cards >= 0 and n_cards <= 5000)),
  lesson_date date,                                                                -- the lesson it is for
  token text,
  created_at timestamptz not null default now()
);
comment on table homework_tasks is 'Homework Amal assigns on the Tutor page: translate / create / question, or a card set for a lesson. Append-only.';

create table if not exists homework_replies (
  id text primary key check (char_length(id) between 8 and 64),
  task_id text not null,
  answer text not null check (char_length(answer) between 1 and 2000),
  script text check (script is null or script in ('arabizi', 'arabic', 'english', 'mixed')),
  ai jsonb,                                                                        -- {verdict: right|close|wrong|ungraded, reason, fixed, model, cost_usd}
  ai_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists homework_replies_task on homework_replies(task_id);
comment on table homework_replies is 'Medi''s typed homework answers (Student tab). The AI check (check-homework) fills ai with the service key; Amal''s word is in homework_verdicts.';

create table if not exists homework_verdicts (
  id text primary key check (char_length(id) between 8 and 64),
  reply_id text not null,
  kind text not null check (kind in ('verdict', 'undo')),
  undoes text,
  verdict text check (verdict is null or verdict in ('right', 'close', 'wrong')),
  agrees boolean,                                                                  -- true = she confirmed the AI; false = she overruled it (S6: a correction rule)
  note text check (note is null or char_length(note) <= 1000),
  fix text check (fix is null or char_length(fix) <= 1000),
  token text,
  created_at timestamptz not null default now()
);
create index if not exists homework_verdicts_reply on homework_verdicts(reply_id);
comment on table homework_verdicts is 'Amal''s confirm / overrule of the AI check, one row per tap (Tutor page). Append-only; undo = a new row with undoes.';

alter table amal_uploads enable row level security;
alter table homework_tasks enable row level security;
alter table homework_replies enable row level security;
alter table homework_verdicts enable row level security;
revoke update, delete on amal_uploads, homework_tasks, homework_replies, homework_verdicts from anon, authenticated;

drop policy if exists amal_uploads_read on amal_uploads;
create policy amal_uploads_read on amal_uploads for select to anon using (true);
drop policy if exists amal_uploads_insert on amal_uploads;
create policy amal_uploads_insert on amal_uploads for insert to anon with check (true);
drop policy if exists homework_tasks_read on homework_tasks;
create policy homework_tasks_read on homework_tasks for select to anon using (true);
drop policy if exists homework_tasks_insert on homework_tasks;
create policy homework_tasks_insert on homework_tasks for insert to anon with check (true);
drop policy if exists homework_replies_read on homework_replies;
create policy homework_replies_read on homework_replies for select to anon using (true);
drop policy if exists homework_replies_insert on homework_replies;
create policy homework_replies_insert on homework_replies for insert to anon with check (ai is null and ai_at is null);
drop policy if exists homework_verdicts_read on homework_verdicts;
create policy homework_verdicts_read on homework_verdicts for select to anon using (true);
drop policy if exists homework_verdicts_insert on homework_verdicts;
create policy homework_verdicts_insert on homework_verdicts for insert to anon with check (true);
