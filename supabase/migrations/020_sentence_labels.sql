-- Sentence-length ladder: Medi's swipe check of machine-labelled sentences (plan/SENTENCE-LADDER-SPEC-2026-09-27.md,
-- decision 7). After each lesson the Fluency tab shows 10 sentences picked by scripts/build_sentence_ladder.py
-- (docs/data/sentence-ladder.json -> swipe.picks); Medi swipes understood / didn't / not sure. One row per swipe.
-- NOT APPLIED YET (2026-09-27). Same access pattern as card_results (001_spine.sql): anon may read and insert, nothing else.
-- A relabel is a new row; readers take the latest row per sentence_id (by ts, then created_at). Rows are never updated
-- or deleted by the browser, so there is no update/delete grant or policy.

create table if not exists sentence_labels (
  id text primary key,                 -- client uuid: offline queue replays are idempotent (like card_results)
  sentence_id text not null,           -- '<lesson date>:L:<t*10>' or ':S:' from docs/data/sentence-ladder/<date>.json
  lesson_date date not null,
  side text not null default 'listen' check (side in ('listen', 'speak')),
  label text not null check (label in ('understood', 'breakdown', 'not_sure')),
  machine_label text check (machine_label is null or machine_label in ('understood', 'breakdown', 'unknown', 'success', 'corrected')),
  machine_version text,                -- sentence-ladder.json 'version' the pick came from
  n_words smallint check (n_words is null or n_words between 0 and 200),
  ts timestamptz not null,             -- when he swiped (client clock)
  answer_ms integer check (answer_ms is null or answer_ms >= 0),   -- visible time from card shown to swipe
  played boolean,                      -- did he play the clip before answering
  tz_offset_min smallint check (tz_offset_min is null or tz_offset_min between -840 and 840),
  tz text check (tz is null or char_length(tz) <= 64),
  subject text,                        -- same meaning as card_results.subject
  created_at timestamptz not null default now()
);
create index if not exists sentence_labels_sentence on sentence_labels(sentence_id);
create index if not exists sentence_labels_lesson on sentence_labels(lesson_date);

comment on table sentence_labels is 'Medi''s own label for a machine-labelled lesson sentence (swipe check). Latest row per sentence_id wins.';
comment on column sentence_labels.label is 'understood | breakdown (he did not understand / could not) | not_sure';

alter table sentence_labels enable row level security;
revoke update, delete on sentence_labels from anon, authenticated;

drop policy if exists sentence_labels_read on sentence_labels;
create policy sentence_labels_read on sentence_labels for select to anon using (true);
drop policy if exists sentence_labels_insert on sentence_labels;
create policy sentence_labels_insert on sentence_labels for insert to anon with check (true);
