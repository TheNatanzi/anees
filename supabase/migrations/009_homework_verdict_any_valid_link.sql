-- M10c fix: Amal judges Medi's answers to the PREVIOUS sheet from her NEXT after-link, so the update policy on
-- homework_answers must accept any valid link whose lesson is on or after the item's lesson (not only the item's own token).
drop policy if exists homework_answers_amal on homework_answers;
create policy homework_answers_amal on homework_answers for update to anon
  using (anees_token() <> '' and exists (
           select 1 from homework_items i, amal_links l
           where i.id = homework_answers.item_id and l.token = anees_token() and l.expires_at > now() and l.lesson_date >= i.lesson_date))
  with check (true);
-- Amal's own prompt lines may also be added from a link whose lesson is on or after the sheet's lesson (same reason)
drop policy if exists homework_items_amal_insert on homework_items;
create policy homework_items_amal_insert on homework_items for insert to anon
  with check (token = anees_token() and status = 'amal'
              and exists (select 1 from amal_links l where l.token = anees_token() and l.expires_at > now() and l.lesson_date >= homework_items.lesson_date));
