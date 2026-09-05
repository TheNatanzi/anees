-- Anees data spine (M0). Applied through the Supabase management API by scripts/apply_migrations.py.
-- Public pages use the anon key; Amal's links carry a secret token in the X-Anees-Token header and RLS
-- lets that token see and write only its own rows. Scripts write with the service key (bypasses RLS).

create table if not exists words (
  key text primary key,
  arabizi text not null,
  arabic text not null default '',
  english text not null default '',
  plural text,
  arabic_plural text,
  topic text not null,
  subtopic text not null,
  tab text,
  doc_order int,
  match_loose text,
  match_skeleton text,
  arabic_norm text,
  aliases text[] default '{}',
  row_hash text,
  active boolean not null default true,
  first_seen timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists words_topic on words(topic);
create index if not exists words_loose on words(match_loose);

create table if not exists lessons (
  date date primary key,
  source text,
  minutes real,
  words int,
  arabic_share real,
  speaker_split text,
  split_ok boolean,
  unlabeled_share real,
  topics jsonb,
  summary jsonb,
  report_url text,
  updated_at timestamptz not null default now()
);

create table if not exists lesson_events (
  id bigserial primary key,
  lesson_date date not null references lessons(date) on delete cascade,
  kind text not null,          -- missed | nailed | new | reused | typed | moment
  word_key text,
  t_start real,
  t_end real,
  speaker text,
  text text,
  clip text,
  confidence real,
  detail jsonb,
  created_at timestamptz not null default now()
);
create index if not exists lesson_events_date on lesson_events(lesson_date);
create index if not exists lesson_events_word on lesson_events(word_key);

create table if not exists word_events (
  id bigserial primary key,
  lesson_date date not null references lessons(date) on delete cascade,
  word_key text not null references words(key),
  t_start real,
  t_end real,
  speaker text,
  prompted boolean,
  correction boolean,
  uptake boolean,
  confidence real,
  clip text,
  text text,
  created_at timestamptz not null default now()
);
create index if not exists word_events_word on word_events(word_key);
create index if not exists word_events_date on word_events(lesson_date);

create table if not exists card_results (
  id text primary key,          -- client uuid: offline queue replays are idempotent
  word_key text not null,
  ts timestamptz not null,
  mode text,                    -- ar_first | en_first
  result text not null,         -- got | missed
  attempt int not null default 1,
  round_id text,
  subject text,
  created_at timestamptz not null default now()
);
create index if not exists card_results_word on card_results(word_key);

create table if not exists word_stats (
  word_key text primary key references words(key) on delete cascade,
  bucket text not null default 'never',   -- ice_cold | cold | shaky | missed | never
  last_reviewed timestamptz,
  last_lesson date,
  seen_lessons int not null default 0,
  times_seen int not null default 0,
  times_missed int not null default 0,
  card_right int not null default 0,
  card_wrong int not null default 0,
  streak int not null default 0,
  streak_days text[] not null default '{}',
  recent boolean not null default false,  -- learned in the last 3 lessons
  weight real not null default 1,
  updated_at timestamptz not null default now()
);

create table if not exists amal_links (
  token text primary key,
  kind text not null,           -- before | after
  lesson_date date,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '7 days',
  opened_at timestamptz,
  done_at timestamptz,
  payload jsonb,
  answers jsonb
);

create table if not exists amal_rules (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  token text references amal_links(token),
  source text not null,         -- planner | after | homework | flashcards
  lesson_date date,
  kind text not null,           -- keep | drop | edit | right | wrong | not_medi | skip | flag | topic | new_words | repeat
  word_key text,
  payload jsonb
);
create index if not exists amal_rules_word on amal_rules(word_key);

-- ---------- RLS ----------
alter table words enable row level security;
alter table lessons enable row level security;
alter table lesson_events enable row level security;
alter table word_events enable row level security;
alter table card_results enable row level security;
alter table word_stats enable row level security;
alter table amal_links enable row level security;
alter table amal_rules enable row level security;

drop policy if exists words_read on words;
create policy words_read on words for select to anon using (true);
drop policy if exists lessons_read on lessons;
create policy lessons_read on lessons for select to anon using (true);
drop policy if exists lesson_events_read on lesson_events;
create policy lesson_events_read on lesson_events for select to anon using (true);
drop policy if exists word_events_read on word_events;
create policy word_events_read on word_events for select to anon using (true);
drop policy if exists word_stats_read on word_stats;
create policy word_stats_read on word_stats for select to anon using (true);
drop policy if exists card_results_read on card_results;
create policy card_results_read on card_results for select to anon using (true);
drop policy if exists card_results_insert on card_results;
create policy card_results_insert on card_results for insert to anon with check (true);

create or replace function anees_token() returns text language sql stable as $$
  select coalesce(current_setting('request.headers', true)::json ->> 'x-anees-token', '')
$$;

drop policy if exists amal_links_own on amal_links;
create policy amal_links_own on amal_links for select to anon using (token = anees_token() and anees_token() <> '');
drop policy if exists amal_links_own_update on amal_links;
create policy amal_links_own_update on amal_links for update to anon
  using (token = anees_token() and anees_token() <> '') with check (token = anees_token());

drop policy if exists amal_rules_own_read on amal_rules;
create policy amal_rules_own_read on amal_rules for select to anon using (token = anees_token() and anees_token() <> '');
drop policy if exists amal_rules_own_insert on amal_rules;
create policy amal_rules_own_insert on amal_rules for insert to anon
  with check (token = anees_token() and exists (select 1 from amal_links l where l.token = anees_token() and l.expires_at > now()));

-- keep public rules readable without the token (the Amal tab shows the rules log): a view that hides the token
create or replace view amal_rules_public as
  select id, created_at, source, lesson_date, kind, word_key, payload from amal_rules;
grant select on amal_rules_public to anon;
