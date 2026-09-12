-- Medi's manual review of conservative draft word matches.
create table if not exists public.draft_word_reviews (
  id text primary key,
  lesson_date date not null references public.lessons(date) on delete cascade,
  word_key text not null references public.words(key),
  row_id text not null,
  timeline_start real not null check (timeline_start >= 0),
  text text not null,
  verdict text not null check (verdict in ('correct', 'incorrect', 'inaudible')),
  reviewed_at timestamptz not null default now()
);

alter table public.draft_word_reviews enable row level security;
grant select, insert, update on public.draft_word_reviews to anon;

drop policy if exists draft_word_reviews_read on public.draft_word_reviews;
create policy draft_word_reviews_read on public.draft_word_reviews for select to anon using (true);
drop policy if exists draft_word_reviews_insert on public.draft_word_reviews;
create policy draft_word_reviews_insert on public.draft_word_reviews for insert to anon with check (true);
drop policy if exists draft_word_reviews_update on public.draft_word_reviews;
create policy draft_word_reviews_update on public.draft_word_reviews for update to anon using (true) with check (true);
