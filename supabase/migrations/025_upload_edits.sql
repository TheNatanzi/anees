-- Medi 2026-10-28: "a view card set button ... and a way to edit cards, add cards, remove cards" (both the student on
-- Flashcards and the tutor on her Tutor page). Still append-only (AM-17): an edit is a NEW row, kind 'edit', undoes = the
-- upload it edits, rows = the set's whole new list (each card keeps its place key 'cid', so its card history stays).
-- The newest edit of an upload wins; an undo row (undoes = the edit's id) takes it back. by_who = who made the row.
alter table amal_uploads drop constraint if exists amal_uploads_kind_check;
alter table amal_uploads add constraint amal_uploads_kind_check check (kind in ('upload', 'undo', 'edit'));
alter table amal_uploads add column if not exists by_who text check (by_who is null or by_who in ('tutor', 'student'));
comment on table amal_uploads is 'Amal''s flashcard uploads from the Tutor page (a Google Sheet / Doc link or a file). Append-only; undo = a new row with undoes; edit = a new row (kind edit, undoes = the upload) with the whole new card list.';
