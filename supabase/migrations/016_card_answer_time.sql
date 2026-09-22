-- Flashcards: how long each card took (Medi 2026-09-21: "track the time for how long I swipe").
-- Visible time only: time while the tab is hidden is not counted.
alter table card_results add column if not exists flip_ms integer check (flip_ms is null or flip_ms >= 0);
alter table card_results add column if not exists answer_ms integer check (answer_ms is null or answer_ms >= 0);
comment on column card_results.flip_ms is 'visible time from card shown to flip, ms (tab-hidden time excluded)';
comment on column card_results.answer_ms is 'visible time from card shown to swipe/answer, ms (tab-hidden time excluded)';
