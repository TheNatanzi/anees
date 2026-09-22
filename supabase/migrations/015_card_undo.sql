-- Flashcards FSRS: card_results stays the one durable answer log (Medi 2026-09-21).
-- Undo last answer marks the row, never deletes it. The browser may set undone_at
-- only, only once, and only within an hour of the answer reaching the server.
alter table card_results add column if not exists undone_at timestamptz;
create index if not exists card_results_ts on card_results(ts);

-- Supabase grants anon table-wide UPDATE by default; narrow it to this one column.
revoke update on card_results from anon, authenticated;
grant update (undone_at) on card_results to anon;
drop policy if exists card_results_undo on card_results;
create policy card_results_undo on card_results for update to anon
  using (undone_at is null and created_at > now() - interval '1 hour')
  with check (undone_at is not null);
