-- M5: Medi's flashcards (no login) may flag a word to Amal: an amal_rules row with no token and source='flashcards'.
drop policy if exists amal_rules_flash_insert on amal_rules;
create policy amal_rules_flash_insert on amal_rules for insert to anon
  with check (token is null and source = 'flashcards' and kind = 'flag');
-- card_results: the client id is the idempotency key; an offline replay must never duplicate (PK) — nothing to add.
