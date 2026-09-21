-- Unified derived Speaking ledger. Raw recordings/events/cards are untouched.
begin;
create table if not exists public.speaking_events (
 id text primary key,
 lesson_date date not null,
 word_key text references public.words(key),
 data jsonb not null,
 check (id=data->>'id'),
 check (lesson_date::text=data->>'lesson_date'),
 check (word_key is not distinct from data->>'word_key')
);
create index if not exists speaking_events_word on public.speaking_events(word_key);
create table if not exists public.speaking_release (id boolean primary key default true check(id), data jsonb not null);
create table if not exists public.speaking_review_overlays (id text primary key, data jsonb not null);
create table if not exists public.speaking_event_revisions (
 id bigint generated always as identity primary key, event_id text not null,
 changed_at timestamptz not null default now(), previous jsonb, replacement jsonb
);
create table if not exists public.speaking_review_links (
 token text primary key check(token ~ '^[A-Za-z0-9_-]{43}$'),
 lesson_date date not null, expires_at timestamptz not null,
 event_ids jsonb not null, clips jsonb not null default '{}'
);
create table if not exists public.speaking_review_answers (
 request_id text primary key, event_id text not null, token text not null,
 answer jsonb not null, created_at timestamptz not null default now()
);
alter table public.speaking_events enable row level security;
alter table public.speaking_release enable row level security;
alter table public.speaking_review_overlays enable row level security;
alter table public.speaking_event_revisions enable row level security;
alter table public.speaking_review_links enable row level security;
alter table public.speaking_review_answers enable row level security;
revoke all on public.speaking_events,public.speaking_release,public.speaking_review_overlays,public.speaking_event_revisions,public.speaking_review_links,public.speaking_review_answers from public,anon,authenticated;
grant select on public.speaking_events,public.speaking_release to anon;
grant all on public.speaking_events,public.speaking_release,public.speaking_review_overlays,public.speaking_event_revisions,public.speaking_review_links,public.speaking_review_answers to service_role;
grant usage,select on sequence public.speaking_event_revisions_id_seq to service_role;
create policy speaking_events_read on public.speaking_events for select to anon using(true);
create policy speaking_release_read on public.speaking_release for select to anon using(true);

create or replace function public.log_speaking_revision() returns trigger language plpgsql
set search_path=public,pg_temp as $$
begin
 if tg_op='DELETE' then
  insert into speaking_event_revisions(event_id,previous) values(old.id,old.data); return old;
 elsif tg_op='UPDATE' and old.data is distinct from new.data then
  insert into speaking_event_revisions(event_id,previous,replacement) values(old.id,old.data,new.data);
 end if;
 return new;
end $$;
create trigger speaking_revision after update or delete on public.speaking_events for each row execute function public.log_speaking_revision();

-- Same Speaking transition function as Python/JS. Flashcards are never replayed here.
create or replace function public.speaking_progress(context jsonb) returns jsonb
language plpgsql immutable set search_path=public,pg_temp as $$
declare lesson jsonb; signal text; qualifies boolean; streak integer:=0; days jsonb:='[]';
 recovery integer:=0; bucket text:='never'; s jsonb; raw_bucket text;
begin
 for lesson in select value from jsonb_array_elements(context->'lessons') order by value->>0 loop
  if lesson->2='null'::jsonb then continue; end if;
  signal:=lesson->>1; qualifies:=(lesson->>2)::boolean;
  if signal='cold' and qualifies then
   streak:=streak+1;
   if not days ? (lesson->>0) then days:=days||jsonb_build_array(lesson->>0); end if;
   if recovery>0 then recovery:=recovery-1; signal:=case when recovery>0 then 'shaky' else 'cold' end; end if;
  else
   streak:=0; days:='[]';
   if signal='missed' or recovery>0 then recovery:=2; if signal='cold' then signal:='shaky'; end if; end if;
  end if;
  bucket:=case when streak>=5 and jsonb_array_length(days)>=5 then 'ice_cold' else signal end;
 end loop;
 raw_bucket:=bucket;
 s:=jsonb_build_object('bucket',bucket,'streak',streak,'streak_days',days,'mastery_streak',streak,'mastery_days',days,'recovery_left',recovery)||(context->'speaking');
 if (context->>'new')::boolean and (s->>'intro_uses')::integer<5 then s:=s||'{"bucket":"new"}'; end if;
 return s||jsonb_build_object('intro_target',case when (context->>'new')::boolean then 5 else 0 end,
   'weight',case when s->>'bucket' in ('new','missed') then 3 else 1 end,'lesson_signal',raw_bucket);
end $$;
revoke all on function public.speaking_progress(jsonb) from public,anon,authenticated;
grant execute on function public.speaking_progress(jsonb) to service_role;

create or replace function public.refresh_speaking_word(k text) returns void
language plpgsql security definer set search_path=public,pg_temp as $$
declare ctx jsonb; summary jsonb; ls jsonb; s jsonb; new_since text; marked boolean;
begin
 select progress_context into ctx from word_stats where word_key=k for update;
 if ctx is null then
  select min(lesson_date)::text into new_since from amal_rules where word_key=k and kind='new';
  ctx:=jsonb_build_object('version',3,'new',new_since is not null,'cards','[]'::jsonb,'lessons','[]'::jsonb,'speaking',jsonb_build_object('new_since',new_since));
  insert into word_stats(word_key,progress_context,progress_scores) values(k,ctx,
   '{"version":1,"flashcards":{"bucket":"never","streak":0,"streak_days":[],"mastery_streak":0,"mastery_days":[],"recovery_left":0,"last_reviewed":null,"attempts":0,"card_right":0,"times_missed":0,"first_try_right":0,"weight":1}}');
 end if;
 new_since:=ctx->'speaking'->>'new_since';
 select jsonb_build_object(
  'times_seen',count(*) filter(where data->>'spoken'='true'),
  'independent_uses',count(*) filter(where data->>'spoken'='true' and data->>'assessment'='independent'),
  'times_missed',count(*) filter(where data->>'assessment' in ('recall_failure','incorrect')),
  'last_reviewed',max(lesson_date)::text,
  'seen_lessons',count(distinct lesson_date) filter(where data->>'spoken'='true'),
  'intro_uses',count(*) filter(where data->>'spoken'='true' and (new_since is null or lesson_date::text>=new_since)),
  'new_since',new_since,
  'helped_uses',count(*) filter(where data->>'spoken'='true' and data->>'assessment'='helped'),
  'recall_failures',count(*) filter(where data->>'assessment'='recall_failure'),
  'incorrect_attempts',count(*) filter(where data->>'assessment'='incorrect'),
  'unresolved',count(*) filter(where data->>'assessment'='unresolved'),
  'provisional',count(*) filter(where data->>'assessment_status'='provisional'),
  'human_reviewed',count(*) filter(where data->>'assessment_status'='human_reviewed'))
 into summary from speaking_events where word_key=k and data->>'speaker'='Medi';
 with daily as (
  select lesson_date,
   bool_or(data->>'assessment' in ('recall_failure','incorrect')) miss,
   bool_or(data->>'assessment'='independent' and data->>'spoken'='true') success,
   bool_or(data->>'assessment'='helped') helped
  from speaking_events where word_key=k and data->>'speaker'='Medi' group by lesson_date
 ) select coalesce(jsonb_agg(jsonb_build_array(lesson_date::text,case when miss then 'missed' when success then 'cold' else 'shaky' end,success) order by lesson_date),'[]')
 into ls from daily where miss or success or helped;
 summary:=summary||jsonb_build_object('mastery_credits',(select count(*) from jsonb_array_elements(ls) a where a->>1='cold' and a->>2='true'));
 ctx:=ctx||jsonb_build_object('speaking',summary,'lessons',ls);
 s:=speaking_progress(ctx);
 update word_stats set progress_context=ctx,
  progress_scores=jsonb_set(progress_scores,'{speaking}',s-'lesson_signal'),
  bucket=s->>'bucket',lesson_signal=s->>'lesson_signal',times_seen=(s->>'times_seen')::int,
  independent_uses=(s->>'independent_uses')::int,times_missed=(s->>'times_missed')::int,
  seen_lessons=(s->>'seen_lessons')::int,last_reviewed=(s->>'last_reviewed')::timestamptz,
  last_lesson=(select max(lesson_date) from speaking_events where word_key=k and data->>'speaker'='Medi' and data->>'spoken'='true'),
  streak=(s->>'streak')::int,streak_days=array(select jsonb_array_elements_text(s->'streak_days')),
  mastery_streak=(s->>'mastery_streak')::int,mastery_days=s->'mastery_days',weight=(s->>'weight')::real,updated_at=now()
 where word_key=k;
end $$;
revoke all on function public.refresh_speaking_word(text) from public,anon,authenticated;
grant execute on function public.refresh_speaking_word(text) to service_role;

create or replace function public.speaking_snapshot() returns jsonb language sql stable
set search_path=public,pg_temp as $$
 select jsonb_build_object('release',(select data from speaking_release where id),
 'stats',(select coalesce(jsonb_agg(to_jsonb(s) order by word_key),'[]') from word_stats s),
 'events',(select coalesce(jsonb_agg(data order by lesson_date,id),'[]') from speaking_events))
$$;
revoke all on function public.speaking_snapshot() from public,authenticated;
grant execute on function public.speaking_snapshot() to anon,service_role;

create or replace function public.get_speaking_review() returns jsonb language plpgsql stable security definer
set search_path=public,pg_temp as $$
declare link speaking_review_links; result jsonb;
begin
 select * into link from speaking_review_links where token=anees_token() and expires_at>now();
 if not found then raise exception 'Review link unavailable'; end if;
 select jsonb_build_object('lesson_date',link.lesson_date,'events',coalesce(jsonb_agg(jsonb_build_object(
  'event',e.data,'expected',md5(e.data::text),'audio',link.clips->e.id,
  'saved',(select answer from speaking_review_answers a where a.event_id=e.id and a.token=link.token order by created_at desc limit 1)) order by q.ord),'[]'))
 into result from jsonb_array_elements_text(link.event_ids) with ordinality q(id,ord) join speaking_events e on e.id=q.id;
 return result;
end $$;
revoke all on function public.get_speaking_review() from public,authenticated;
grant execute on function public.get_speaking_review() to anon,service_role;

create or replace function public.review_speaking_event(p_event_id text,p_expected text,p_assessment text,p_spoken boolean,p_word_key text,p_note text,p_request_id text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare link speaking_review_links; e speaking_events; old_key text; replacement jsonb; previous speaking_review_answers;
begin
 select * into link from speaking_review_links where token=anees_token() and expires_at>now();
 if not found or not (link.event_ids ? p_event_id) then raise exception 'Review not authorized'; end if;
 select * into previous from speaking_review_answers where request_id=p_request_id;
 if found then
  if previous.token<>link.token or previous.event_id<>p_event_id or previous.answer is distinct from
   jsonb_build_object('assessment',p_assessment,'spoken',p_spoken,'word_key',p_word_key,'note',p_note,'previous_sha256',p_expected)
  then raise exception 'Request collision'; end if;
  return jsonb_build_object('saved',true,'replayed',true);
 end if;
 if p_assessment is null or p_assessment not in ('independent','helped','recall_failure','incorrect','unresolved') or p_spoken is null or length(coalesce(p_note,''))>1000 or length(coalesce(p_request_id,'')) not between 16 and 128 or length(coalesce(p_expected,''))<>32 then raise exception 'Invalid assessment'; end if;
 if p_assessment<>'unresolved' and p_word_key is null then raise exception 'Assessment requires an identified target'; end if;
 if p_word_key is not null and not exists(select 1 from words where key=p_word_key and active) then raise exception 'Unknown vocabulary target'; end if;
 select * into e from speaking_events where id=p_event_id for update;
 if not found or e.data->>'speaker'<>'Medi' or md5(e.data::text)<>p_expected then raise exception 'Evidence changed; reload review'; end if;
 if p_assessment in ('independent','helped') and (not p_spoken or p_word_key is null) then raise exception 'Success/practice requires a spoken identified target'; end if;
 if p_spoken and (p_word_key is null or jsonb_array_length(e.data->'item_ids')=0 or e.data->>'wording_status'='unresolved') then raise exception 'Resolve source wording before crediting speech'; end if;
 if p_spoken and exists(select 1 from speaking_events o where o.id<>e.id and o.data->>'source_sha256'=e.data->>'source_sha256' and o.data->>'spoken'='true' and o.data->>'speaker'='Medi' and
  (o.data->>'local_start')::numeric<(e.data->>'local_end')::numeric and (o.data->>'local_end')::numeric>(e.data->>'local_start')::numeric) then raise exception 'Overlapping speech credit'; end if;
 old_key:=e.word_key;
 replacement:=e.data||jsonb_build_object('word_key',p_word_key,'spoken',p_spoken,'assessment',p_assessment,'assessment_status','human_reviewed',
  'reason','Amal reviewed this assessment; original AI reasoning retained in the private revision audit',
  'human_correction',jsonb_build_object('reviewer','Amal','at',now(),'request_id',p_request_id));
 update speaking_events set word_key=p_word_key,data=replacement where id=e.id;
 insert into speaking_review_answers(request_id,event_id,token,answer) values(p_request_id,e.id,link.token,
  jsonb_build_object('assessment',p_assessment,'spoken',p_spoken,'word_key',p_word_key,'note',p_note,'previous_sha256',p_expected));
 if old_key is not null then perform refresh_speaking_word(old_key); end if;
 if p_word_key is not null and p_word_key is distinct from old_key then perform refresh_speaking_word(p_word_key); end if;
 update speaking_release set data=jsonb_set(data,'{revision}',to_jsonb(md5(data::text||p_request_id))) where id;
 return jsonb_build_object('saved',true,'replayed',false);
end $$;
revoke all on function public.review_speaking_event(text,text,text,boolean,text,text,text) from public,authenticated;
grant execute on function public.review_speaking_event(text,text,text,boolean,text,text,text) to anon,service_role;
notify pgrst,'reload schema';
commit;
