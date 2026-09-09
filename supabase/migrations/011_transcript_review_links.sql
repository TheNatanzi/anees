-- Isolated transcript review: no legacy amal_links/rules/homework authority.
create table public.transcript_review_links (
  token text primary key check (token ~ '^[A-Za-z0-9_-]{43}$'),
  lesson_date date not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  payload jsonb not null,
  answers jsonb not null,
  opened_at timestamptz,
  done_at timestamptz
);
alter table public.transcript_review_links enable row level security;
revoke all on public.transcript_review_links from public, anon, authenticated;
grant select on public.transcript_review_links to anon;
grant update (answers,opened_at,done_at) on public.transcript_review_links to anon;
grant all on public.transcript_review_links to service_role;
create policy transcript_review_read on public.transcript_review_links
  for select to anon using (token = public.anees_token() and expires_at > now());
create policy transcript_review_update on public.transcript_review_links
  for update to anon using (token = public.anees_token() and expires_at > now())
  with check (token = public.anees_token() and expires_at > now());
-- Client validation is repeated here: a malformed assertion must never become reference text.
create function public.transcript_review_trim(value text) returns text
language sql immutable set search_path = public, pg_temp as $trim$
  select btrim(value, U&'\0009\000A\000B\000C\000D\0020\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000\FEFF')
$trim$;
create function public.transcript_review_guard() returns trigger
language plpgsql set search_path = public, pg_temp as $$
declare entry record; proposed jsonb;
begin
  -- Owner-side expiry/revocation need not manufacture a new reviewer assertion.
  if current_user = 'service_role' and new.answers is not distinct from old.answers then return new; end if;
  if new.answers->>'binding' is distinct from old.answers->>'binding'
     or new.answers->>'schema_version' is distinct from '1'
     or jsonb_typeof(new.answers->'answers') is distinct from 'object'
     or jsonb_typeof(new.answers->'revision') is distinct from 'number'
     or (new.answers->>'revision')::bigint is distinct from (old.answers->>'revision')::bigint + 1 then
    raise exception 'Invalid review binding or revision';
  end if;
  for entry in select key,value from jsonb_each(new.answers->'answers') loop
    select value into proposed from jsonb_array_elements(old.payload->'items') where value->>'id' = entry.key;
    if proposed is null or jsonb_typeof(entry.value) is distinct from 'object'
       or coalesce(entry.value->>'choice','') not in ('yes','different','inaudible')
       or jsonb_typeof(entry.value->'draft') is distinct from 'string'
       or jsonb_typeof(entry.value->'updated_at') is distinct from 'string'
       or length(entry.value->>'draft') > 1000 then raise exception 'Invalid review answer'; end if;
    if entry.value->>'choice' = 'yes' and entry.value->>'text' is distinct from proposed->>'proposal' then
      raise exception 'Proposal changed';
    elsif entry.value->>'choice' = 'inaudible' and entry.value->'text' is distinct from 'null'::jsonb then
      raise exception 'Unclear audio is not confirmed wording';
    elsif entry.value->>'choice' = 'different' and (entry.value->>'text') is distinct from nullif(public.transcript_review_trim(entry.value->>'draft'),'') then
      raise exception 'Custom wording mismatch';
    end if;
  end loop;
  if new.done_at is not null and exists (
    select 1 from jsonb_array_elements(old.payload->'items') i
    where not (new.answers->'answers' ? (i->>'id'))
      or ((new.answers->'answers'->(i->>'id')->>'choice') = 'different'
          and coalesce(public.transcript_review_trim(new.answers->'answers'->(i->>'id')->>'text'),'') = '')
  ) then raise exception 'Review has unfinished answers'; end if;
  return new;
end $$;
create trigger transcript_review_guard_t before update on public.transcript_review_links
  for each row execute function public.transcript_review_guard();
