-- Separate derived scores. No raw lesson/card evidence or access rules are changed.
begin;
alter table public.word_stats add column if not exists progress_scores jsonb;
comment on column public.word_stats.progress_scores is 'Versioned isolated Speaking and Flashcards scores; never averaged or allowed to advance each other.';
comment on column public.word_stats.bucket is 'Speaking-only status. Flashcard status is progress_scores.flashcards.bucket.';
comment on column public.word_stats.last_reviewed is 'Last eligible Medi spoken lesson date only. Card practice date is progress_scores.flashcards.last_reviewed.';
comment on column public.word_stats.times_missed is 'Spoken Medi word misses only; excludes card answers and typed homework.';
comment on column public.word_stats.times_seen is 'Timed recorded Medi word occurrences only, including helped uses; excludes tutor, typed homework and untimed evidence.';
comment on column public.word_stats.mastery_streak is 'Speaking-only consecutive independent lesson successes; maximum one per word/lesson date. Cards have a separate streak.';
comment on column public.word_stats.progress_context is 'Version 3: separate lesson signals, card metadata and source-filtered Speaking summary for deterministic replay. No audio or transcript text.';
notify pgrst, 'reload schema';
commit;
