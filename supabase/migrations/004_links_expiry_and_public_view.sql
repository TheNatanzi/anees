-- Codex M3 audit: (1) an expired link is invisible and read-only to its holder; (2) the public rules log carries no token and
-- no free-text payload — only what Medi's Amal tab needs (kind, word, lesson, a short label).
drop policy if exists amal_links_own on amal_links;
create policy amal_links_own on amal_links for select to anon
  using (token = anees_token() and anees_token() <> '' and expires_at > now());
drop policy if exists amal_links_own_update on amal_links;
create policy amal_links_own_update on amal_links for update to anon
  using (token = anees_token() and anees_token() <> '' and expires_at > now()) with check (token = anees_token());

drop view if exists amal_rules_public;
create view amal_rules_public with (security_invoker = false) as
  select id, created_at, source, lesson_date, kind, word_key,
         left(coalesce(payload->>'edited', payload->>'arabizi', payload->>'topic', payload->>'label', payload->>'alias', ''), 120) as text
  from amal_rules;
grant select on amal_rules_public to anon;
