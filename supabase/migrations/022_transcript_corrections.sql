-- Medi's corrections on the Lessons page transcript (Medi 2026-10-02: "i am going to make some corrections to the
-- transcript. try and make rule and patterns with my corrections."). docs/js/transcript-corrections.js writes one row
-- per correction through a localStorage queue; scripts/medi_corrections.py pull mirrors the table into
-- data/lesson-work/medi-corrections.json and the builders apply the effective set (not undone) upstream of every page.
-- Same access pattern as name_labels (021) / sentence_labels (020): anon may read and insert, nothing else. An undo is a
-- new row with `undoes`; nothing is ever updated or deleted. Transcripts are public by the owner's choice (PR-02).

create table if not exists transcript_corrections (
  id text primary key,                         -- client uuid: offline queue replays are idempotent
  lesson_date date not null check (lesson_date >= date '2026-08-01'),   -- upper bound (now()+1 day): trigger below
  turn_t numeric not null check (turn_t >= 0 and turn_t < 20000),   -- the line's start on the lesson clock (s)
  turn_who text not null check (turn_who in ('Medi', 'Amal', 'chat', '?')),
  kind text not null check (kind in ('text', 'speaker', 'time', 'missing', 'not-slip', 'was-wrong', 'classify', 'add',
                                     'not-use', 'undo', 'rule-answer')),
  target jsonb check (target is null or pg_column_size(target) < 2000),    -- the chip it is about: {k, rule, word, said}
  payload jsonb check (payload is null or pg_column_size(payload) < 4000),  -- what to change
  note text check (note is null or char_length(note) <= 600),             -- his words
  undoes text,                                 -- id of the row this one undoes
  proposal text check (proposal is null or char_length(proposal) <= 80),   -- a proposed rule's id (kind rule-answer)
  answer text check (answer is null or answer in ('yes', 'one')),
  ts timestamptz not null,
  tz_offset_min smallint check (tz_offset_min is null or tz_offset_min between -840 and 840),
  created_at timestamptz not null default now()
);
-- Council 5 (2026-10-03): a lesson date in the future is a bad row. A CHECK may not call now() reliably, so a trigger does.
create or replace function transcript_corrections_date_ok() returns trigger language plpgsql set search_path = public as $$
begin
  if new.lesson_date > (now() + interval '1 day')::date then
    raise exception 'transcript_corrections: lesson_date % is in the future', new.lesson_date;
  end if;
  return new;
end $$;
drop trigger if exists transcript_corrections_date_ok on transcript_corrections;
create trigger transcript_corrections_date_ok before insert on transcript_corrections
  for each row execute function transcript_corrections_date_ok();
alter table transcript_corrections add constraint transcript_corrections_id_len check (char_length(id) between 8 and 64);

create index if not exists transcript_corrections_lesson on transcript_corrections(lesson_date);

comment on table transcript_corrections is 'Medi''s corrections on the lesson transcript. Append-only; undo = a new row with undoes.';

alter table transcript_corrections enable row level security;
revoke update, delete on transcript_corrections from anon, authenticated;

drop policy if exists transcript_corrections_read on transcript_corrections;
create policy transcript_corrections_read on transcript_corrections for select to anon using (true);
drop policy if exists transcript_corrections_insert on transcript_corrections;
create policy transcript_corrections_insert on transcript_corrections for insert to anon with check (true);
