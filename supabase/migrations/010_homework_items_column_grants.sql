-- M10c hardening: the public (anon) read of homework_items must never expose the link token (secret) nor the model answer
-- (Medi must answer before seeing it). Column-level grant; scripts and the grade function use the service key.
revoke select on homework_items from anon;
grant select (id, lesson_date, n, english, status, edited_english, keys, created_at, decided_at) on homework_items to anon;
