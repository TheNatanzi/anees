-- Derived fields only. Raw speech, card answers, access rules and bucket IDs are unchanged.
begin;
alter table public.word_stats add column if not exists independent_uses integer;
alter table public.word_stats add column if not exists mastery_streak integer;
alter table public.word_stats add column if not exists mastery_days jsonb;
alter table public.word_stats add column if not exists progress_context jsonb;
comment on column public.word_stats.times_seen is 'Medi lesson word occurrences only; includes prompted attempts. Not tutor exposure.';
comment on column public.word_stats.independent_uses is 'Medi occurrences explicitly unprompted, not corrected and not asked; transcript-derived, not human-verified.';
comment on column public.word_stats.mastery_streak is 'Consecutive qualifying lesson/card successes. At most one lesson contribution per word/date.';
comment on column public.word_stats.progress_context is 'Versioned derived lesson signals and card metadata for deterministic cross-device/offline progress replay. No audio or transcript text.';
notify pgrst, 'reload schema';
commit;
