-- M10a: Amal's house spelling (mined from her typed WhatsApp lines; scripts/house_spelling.py). Display only; key unchanged.
alter table words add column if not exists house_spelling text;
alter table words add column if not exists house_n int not null default 0;

-- M10b: tutor-typed lines (Meet chat sidecar + WhatsApp) as ground truth per lesson minute. Written by scripts, read by anyone.
create table if not exists chat_lines (
  id bigserial primary key,
  lesson_date date not null references lessons(date) on delete cascade,
  t_rel real not null,            -- seconds into the recording
  source text not null,           -- meet | whatsapp
  who text not null default 'Amal',
  text text not null,
  word_keys text[] not null default '{}',   -- Doc words found in the line (trusted tiers only)
  created_at timestamptz not null default now(),
  unique (lesson_date, source, t_rel, text)
);
create index if not exists chat_lines_date on chat_lines(lesson_date);
alter table chat_lines enable row level security;
drop policy if exists chat_lines_read on chat_lines;
create policy chat_lines_read on chat_lines for select to anon using (true);
alter table word_events add column if not exists typed_line_id bigint references chat_lines(id) on delete set null;
