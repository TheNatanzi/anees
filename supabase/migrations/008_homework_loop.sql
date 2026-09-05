-- M10c: text homework loop. Prompts are suggested by Anees, decided by Amal (keep / drop / edit / her own), answered by Medi
-- on docs/homework.html (typed Arabizi only), graded on the spot by the `grade` edge function, then judged by Amal on her
-- after link. Her verdict is the one that scores the word (writes word_events through scripts/apply_rules.py).

create table if not exists homework_items (
  id bigserial primary key,
  lesson_date date not null references lessons(date) on delete cascade,
  token text references amal_links(token) on delete set null,   -- the after link that carries these items
  n int not null,                          -- order on the sheet
  english text not null,                   -- the prompt Medi translates
  model_arabizi text not null default '',  -- Anees model answer (Doc words only) - never shown to Medi before he answers
  model_arabic text not null default '',
  keys text[] not null default '{}',       -- Doc words the prompt targets
  status text not null default 'suggested',   -- suggested | keep | drop | edit | amal
  edited_english text,                     -- her version when status = edit; her own line when status = amal
  created_at timestamptz not null default now(),
  decided_at timestamptz
);
create index if not exists homework_items_date on homework_items(lesson_date);

create table if not exists homework_answers (
  id text primary key,                     -- client uuid (offline replays are idempotent)
  item_id bigint not null references homework_items(id) on delete cascade,
  lesson_date date not null,
  answer text not null,
  ts timestamptz not null default now(),
  grade jsonb,                             -- {verdict: right|close|wrong, notes:[{kind, say}], fixed, model, cost_usd}
  graded_at timestamptz,
  amal_verdict text,                       -- right | fix | skip
  amal_fix text,
  amal_at timestamptz,
  applied timestamptz                      -- set by apply_rules.py once the verdict scored the word
);
create index if not exists homework_answers_item on homework_answers(item_id);

create table if not exists api_spend (
  id bigserial primary key,
  ts timestamptz not null default now(),
  service text not null,                   -- openai
  usd real not null,
  note text
);

alter table homework_items enable row level security;
alter table homework_answers enable row level security;
alter table api_spend enable row level security;

-- Medi page (no login): read items + answers, insert an answer.
drop policy if exists homework_items_read on homework_items;
create policy homework_items_read on homework_items for select to anon using (true);
drop policy if exists homework_answers_read on homework_answers;
create policy homework_answers_read on homework_answers for select to anon using (true);
drop policy if exists homework_answers_insert on homework_answers;
create policy homework_answers_insert on homework_answers for insert to anon with check (grade is null and amal_verdict is null);

-- Amal link: decide items and judge answers of HER lesson only, while the link is valid.
drop policy if exists homework_items_amal on homework_items;
create policy homework_items_amal on homework_items for update to anon
  using (token = anees_token() and anees_token() <> '' and exists (select 1 from amal_links l where l.token = anees_token() and l.expires_at > now()))
  with check (token = anees_token());
drop policy if exists homework_items_amal_insert on homework_items;
create policy homework_items_amal_insert on homework_items for insert to anon
  with check (token = anees_token() and status = 'amal' and exists (select 1 from amal_links l where l.token = anees_token() and l.expires_at > now() and l.lesson_date = homework_items.lesson_date));
drop policy if exists homework_answers_amal on homework_answers;
create policy homework_answers_amal on homework_answers for update to anon
  using (anees_token() <> '' and exists (select 1 from homework_items i join amal_links l on l.token = i.token where i.id = homework_answers.item_id and l.token = anees_token() and l.expires_at > now()))
  with check (true);

-- anon may change only status / edited_english / decided_at on items, and only amal_verdict / amal_fix / amal_at on answers
create or replace function homework_guard() returns trigger language plpgsql as $$
begin
  if current_user = 'anon' or coalesce(current_setting('request.jwt.claim.role', true), '') = 'anon' then
    if tg_table_name = 'homework_items' then
      if new.lesson_date <> old.lesson_date or new.token is distinct from old.token or new.n <> old.n or new.english <> old.english
         or new.model_arabizi <> old.model_arabizi or new.model_arabic <> old.model_arabic or new.keys <> old.keys or new.created_at <> old.created_at
         or new.status not in ('keep', 'drop', 'edit', 'amal') then
        raise exception 'anon may only decide an item (status / edited_english)';
      end if;
    else
      if new.item_id <> old.item_id or new.lesson_date <> old.lesson_date or new.answer <> old.answer or new.ts <> old.ts
         or new.grade is distinct from old.grade or new.graded_at is distinct from old.graded_at or new.applied is distinct from old.applied
         or new.amal_verdict not in ('right', 'fix', 'skip') then
        raise exception 'anon may only judge an answer (amal_verdict / amal_fix)';
      end if;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists homework_items_guard_t on homework_items;
create trigger homework_items_guard_t before update on homework_items for each row execute function homework_guard();
drop trigger if exists homework_answers_guard_t on homework_answers;
create trigger homework_answers_guard_t before update on homework_answers for each row execute function homework_guard();
