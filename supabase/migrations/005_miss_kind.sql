-- M9: what kind of miss was it? word | article | gender | tense | plural | pronunciation | unclear (never guessed: unclear stays unclear)
alter table word_events add column if not exists miss_kind text;
alter table word_events add column if not exists miss_why text;
alter table word_stats add column if not exists grammar_misses int not null default 0;
alter table word_stats add column if not exists grammar_kinds text[] not null default '{}';
