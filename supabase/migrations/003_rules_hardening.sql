-- Codex M4 audit fixes: (1) a token may only write rules for its own link's lesson; (2) anon may not touch token / kind /
-- lesson_date / expires_at / created_at / payload on amal_links; (3) word_events.asked ("Medi asked for it").
alter table word_events add column if not exists asked boolean;

drop policy if exists amal_rules_own_insert on amal_rules;
create policy amal_rules_own_insert on amal_rules for insert to anon
  with check (token = anees_token()
              and exists (select 1 from amal_links l where l.token = anees_token() and l.expires_at > now()
                          and (amal_rules.lesson_date is null or amal_rules.lesson_date = l.lesson_date)));

create or replace function amal_links_guard() returns trigger language plpgsql as $$
begin
  if current_user = 'anon' or coalesce(current_setting('request.jwt.claim.role', true), '') = 'anon' then
    if new.token <> old.token or new.kind <> old.kind or new.lesson_date is distinct from old.lesson_date
       or new.expires_at <> old.expires_at or new.created_at <> old.created_at or new.payload is distinct from old.payload then
      raise exception 'anon may only update answers / opened_at / done_at';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists amal_links_guard_t on amal_links;
create trigger amal_links_guard_t before update on amal_links for each row execute function amal_links_guard();
