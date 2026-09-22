-- Amal's check list for guessed verb forms (verb drills step 2).
-- Same isolation as transcript_review_links: a bearer token in the link, no login,
-- anon may only read its own row and write answers/opened_at/done_at.
create table public.verb_check_links (
  token text primary key check (token ~ '^[A-Za-z0-9_-]{43}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  payload jsonb not null,
  answers jsonb not null,
  opened_at timestamptz,
  done_at timestamptz
);
alter table public.verb_check_links enable row level security;
revoke all on public.verb_check_links from public, anon, authenticated;
grant select on public.verb_check_links to anon;
grant update (answers,opened_at,done_at) on public.verb_check_links to anon;
grant all on public.verb_check_links to service_role;
create policy verb_check_read on public.verb_check_links
  for select to anon using (token = public.anees_token() and expires_at > now());
create policy verb_check_update on public.verb_check_links
  for update to anon using (token = public.anees_token() and expires_at > now())
  with check (token = public.anees_token() and expires_at > now());

-- Answers: {schema_version:1, revision:n, answers:{<item id>:{choice:'yes'|'fix', word, arabic, updated_at}}}
-- 'yes' must repeat the guess exactly; 'fix' must carry Amal's own non-empty Arabizi.
create function public.verb_check_guard() returns trigger
language plpgsql set search_path = public, pg_temp as $$
declare entry record; proposed jsonb;
begin
  if current_user = 'service_role' and new.answers is not distinct from old.answers then return new; end if;
  if new.answers->>'schema_version' is distinct from '1'
     or jsonb_typeof(new.answers->'answers') is distinct from 'object'
     or jsonb_typeof(new.answers->'revision') is distinct from 'number'
     or (new.answers->>'revision')::bigint is distinct from (old.answers->>'revision')::bigint + 1 then
    raise exception 'Invalid check revision';
  end if;
  for entry in select key,value from jsonb_each(new.answers->'answers') loop
    proposed := old.payload->'items'->entry.key;
    if proposed is null or jsonb_typeof(entry.value) is distinct from 'object'
       or coalesce(entry.value->>'choice','') not in ('yes','fix')
       or jsonb_typeof(entry.value->'word') is distinct from 'string'
       or jsonb_typeof(entry.value->'arabic') is distinct from 'string'
       or jsonb_typeof(entry.value->'updated_at') is distinct from 'string'
       or length(entry.value->>'word') > 200 or length(entry.value->>'arabic') > 200 then
      raise exception 'Invalid check answer';
    end if;
    if entry.value->>'choice' = 'yes' and (entry.value->>'word' is distinct from proposed->>'word'
       or entry.value->>'arabic' is distinct from proposed->>'arabic') then
      raise exception 'Guess changed';
    elsif entry.value->>'choice' = 'fix' and btrim(entry.value->>'word') = '' then
      raise exception 'A fix needs Amal''s form';
    end if;
  end loop;
  return new;
end $$;
create trigger verb_check_guard_t before update on public.verb_check_links
  for each row execute function public.verb_check_guard();
