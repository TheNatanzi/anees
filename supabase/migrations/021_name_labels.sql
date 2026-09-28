-- Names & places layer: Medi's one-tap answers to "Possible names" (AI Reports › Robot blind spots, docs/js/possible-names.js).
-- scripts/names.py possible lists words that look like names; Medi taps "Name" / "Not a name"; scripts/names.py build reads
-- the latest row per cand_fp into docs/data/names.json, so every pipeline treats the word as a name (or never asks again).
-- NOT APPLIED YET (2026-09-28): Medi pastes it. Same access pattern as sentence_labels (020): anon may read and insert,
-- nothing else. A changed answer is a new row; readers take the latest row per cand_fp (by ts, then created_at).
-- PRIVACY (the site and repo are public): cand_fp is the salted sha256 fingerprint of the normalised word (js/names.js fp,
-- scripts/names.py fp). A person's name is stored ONLY as that fingerprint - the check below refuses text for a person.
-- A place / country / other name keeps its text (it is not private and the builder needs it to match).

create table if not exists name_labels (
  id text primary key,                 -- client uuid: offline queue replays are idempotent (like sentence_labels)
  cand_fp text not null check (cand_fp ~ '^[0-9a-f]{32}$'),
  label text not null check (label in ('name', 'not_name')),
  kind text check (kind is null or kind in ('place', 'country', 'person', 'other')),
  text text check (text is null or char_length(text) between 1 and 80),
  lesson_date date,                    -- the lesson of the first example sentence
  source_version text,                 -- possible-names.json 'version' the row came from
  ts timestamptz not null,             -- when he tapped (client clock)
  tz_offset_min smallint check (tz_offset_min is null or tz_offset_min between -840 and 840),
  created_at timestamptz not null default now(),
  constraint name_labels_person_is_fingerprint_only check (kind is distinct from 'person' or text is null),
  constraint name_labels_kind_only_for_names check (label = 'name' or kind is null)
);
create index if not exists name_labels_cand on name_labels(cand_fp);

comment on table name_labels is 'Medi''s answer to a possible name (Name / Not a name). Latest row per cand_fp wins. People: fingerprint only.';
comment on column name_labels.cand_fp is 'salted sha256 (first 32 hex) of the normalised word, scripts/names.py fp()';

alter table name_labels enable row level security;
revoke update, delete on name_labels from anon, authenticated;

drop policy if exists name_labels_read on name_labels;
create policy name_labels_read on name_labels for select to anon using (true);
drop policy if exists name_labels_insert on name_labels;
create policy name_labels_insert on name_labels for insert to anon with check (true);
