-- Big Picture: Medi's idea dump (Medi 2026-09-22: "a big pictures plan section where I can idea dump",
-- visible as its own tab). Raw ideas, not specs. Low security posture (Medi 2026-09-05): the page
-- uses the anon key; anon may read, add, and change an idea's status or note. No deletes: an idea
-- is retired by status 'dropped', so nothing typed is ever lost.
create table if not exists big_picture_ideas (
  id uuid primary key default gen_random_uuid(),
  title text not null check (length(btrim(title)) between 1 and 300),
  note text check (note is null or length(note) <= 4000),
  status text not null default 'idea' check (status in ('idea','picked','building','done','dropped')),
  source text not null default 'medi' check (source in ('medi','claude','legacy')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table big_picture_ideas is 'Medi''s Big Picture idea dump (docs/big-picture.html). Ideas only; a picked idea becomes a spec in plan/.';

create or replace function big_picture_touch() returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;
drop trigger if exists big_picture_touch on big_picture_ideas;
create trigger big_picture_touch before update on big_picture_ideas for each row execute function big_picture_touch();

alter table big_picture_ideas enable row level security;
drop policy if exists big_picture_read on big_picture_ideas;
create policy big_picture_read on big_picture_ideas for select to anon using (true);
drop policy if exists big_picture_add on big_picture_ideas;
create policy big_picture_add on big_picture_ideas for insert to anon with check (source = 'medi');
drop policy if exists big_picture_edit on big_picture_ideas;
create policy big_picture_edit on big_picture_ideas for update to anon using (true) with check (true);
revoke all on big_picture_ideas from anon;
grant select, insert on big_picture_ideas to anon;
grant update (status, note) on big_picture_ideas to anon;

-- Seed: Medi's first four ideas, Claude's Anki gaps, and the old index.html "Future projects" list.
insert into big_picture_ideas (title, note, source, created_at)
select * from (values
  ('Words into context', 'Flashcards show the word inside a short phrase. Source idea: Amal''s live-typed drill sentences.', 'medi', timestamptz '2026-09-22 08:00:00+00'),
  ('Sentences', 'Whole-sentence cards and drills, not single words; the target word can be blanked out.', 'medi', timestamptz '2026-09-22 08:00:01+00'),
  ('Audio lessons', 'Listen-first practice using Amal''s voice from the lesson recordings.', 'medi', timestamptz '2026-09-22 08:00:02+00'),
  ('User speaks lessons — cadence, speed and accent graded too', 'Medi answers out loud; graded on words right, rhythm, words per minute vs Amal, and how close the sounds are to Amal''s.', 'medi', timestamptz '2026-09-22 08:00:03+00'),
  ('Test both directions', 'Arabic → English and English → Arabic (Anki comparison 2026-09-22).', 'claude', timestamptz '2026-09-22 08:00:04+00'),
  ('Fix flow for leeches', 'Cards forgotten 8+ times: rewrite, split, or ask Amal (Anki comparison 2026-09-22).', 'claude', timestamptz '2026-09-22 08:00:05+00'),
  ('Amal''s newly taught words go straight into the next day''s new cards', 'Anki comparison 2026-09-22.', 'claude', timestamptz '2026-09-22 08:00:06+00'),
  ('Deep research → rules', 'Language-learning studies turned into rules the app follows.', 'legacy', timestamptz '2026-09-05 12:00:00+00'),
  ('Voice homework answers', 'Hold-to-talk on the homework page, transcribed by ElevenLabs Scribe.', 'legacy', timestamptz '2026-09-05 12:00:01+00'),
  ('Audio homework that listens', 'Record a sentence, the app compares pronunciation. Caveat: speech-to-text auto-corrects learners.', 'legacy', timestamptz '2026-09-05 12:00:02+00'),
  ('Adding words inside the app', 'A form for Medi or Amal that feeds a review inbox, never the Google Doc directly.', 'legacy', timestamptz '2026-09-05 12:00:03+00'),
  ('Separate-track recording', 'One audio track per person makes speaker labels exact.', 'legacy', timestamptz '2026-09-05 12:00:04+00')
) as v(title, note, source, created_at)
where not exists (select 1 from big_picture_ideas);
