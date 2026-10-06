
-- Medi 2026-10-06: a third button on every flashcard, "Attention": he asks Amal a question or raises a concern about the card;
-- it lands on her Tutor To do list ("Questions from the student") and her reply comes back to his Student tab. Same access
-- pattern as 022/023: anon read + insert, append-only, undo = a new row with undoes. Her reply is a row kind 'reply' with ref.
create table if not exists card_attention (
  id text primary key check (char_length(id) between 8 and 64),
  kind text not null check (kind in ('note', 'reply', 'undo')),
  undoes text,
  ref text,                                                        -- reply: the note it answers
  card_key text check (card_key is null or char_length(card_key) <= 200),
  arabizi text check (arabizi is null or char_length(arabizi) <= 300),
  arabic text check (arabic is null or char_length(arabic) <= 300),
  english text check (english is null or char_length(english) <= 500),
  text text check (text is null or char_length(text) <= 2000),
  by_who text not null check (by_who in ('student', 'teacher')),
  token text,
  created_at timestamptz not null default now()
);
create index if not exists card_attention_ref on card_attention(ref);
alter table card_attention enable row level security;
revoke update, delete on card_attention from anon, authenticated;
drop policy if exists card_attention_read on card_attention;
create policy card_attention_read on card_attention for select to anon using (true);
drop policy if exists card_attention_insert on card_attention;
create policy card_attention_insert on card_attention for insert to anon with check (true);
