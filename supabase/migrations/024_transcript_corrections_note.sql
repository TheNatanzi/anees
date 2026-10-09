-- 024 PG-37 (Medi 2026-10-08 "Can we turn this into just 1 box and we can write the correction, not try and separate
-- into so many boxes?"): the Lessons page's one-box fix saves his words as kind 'note' when no shape fits; the hourly
-- job reads them (scripts/correction_parse.py). Same table, same append-only rules; payload carries raw (his words).
alter table transcript_corrections drop constraint if exists transcript_corrections_kind_check;
alter table transcript_corrections add constraint transcript_corrections_kind_check
  check (kind in ('text', 'speaker', 'time', 'missing', 'not-slip', 'was-wrong', 'classify', 'add', 'not-use', 'undo', 'rule-answer', 'note'));
