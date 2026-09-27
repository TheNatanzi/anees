-- Flashcards: the timezone each answer was given in (2026-09-27 audit, bug 6).
-- The Hourly breakdown on Progress & Stats used the browser's local clock at read time; answers carried no
-- timezone of their own, so a phone abroad or a laptop in another zone would move the bars. Each new
-- card_results row now stores the clock it was answered in: minutes east of UTC (JS -getTimezoneOffset())
-- and the IANA name when the browser knows it. Old rows stay null; the chart falls back to the browser clock
-- for them and says so.
-- The clients (docs/cards.html, docs/js/flashcard-progress.js) tolerate this column being absent: a 400 that
-- names it makes them read and write without it for that page load. Apply when convenient; nothing breaks before.
alter table card_results add column if not exists tz_offset_min smallint check (tz_offset_min is null or tz_offset_min between -840 and 840);
alter table card_results add column if not exists tz text check (tz is null or char_length(tz) <= 64);
comment on column card_results.tz_offset_min is 'minutes east of UTC of the clock the answer was given in (JS -getTimezoneOffset()); null before migration 017';
comment on column card_results.tz is 'IANA timezone name of that clock (Intl resolvedOptions().timeZone), when the browser knows it';
-- Insert grants and the anon insert policy (001_spine.sql) are table-wide, so no grant change is needed.
