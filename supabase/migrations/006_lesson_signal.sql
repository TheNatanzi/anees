-- new bucket: keep the lesson-only signal beside the bucket
alter table word_stats add column if not exists lesson_signal text;
