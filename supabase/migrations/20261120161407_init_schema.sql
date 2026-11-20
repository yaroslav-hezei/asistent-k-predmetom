-- Schema v1 of the assistant.
--
-- Access model: the browser talks only to the FastAPI backend; it uses Supabase only to log in.
-- The backend connects to Postgres directly as the table owner (`postgres`), which bypasses RLS.
-- The Supabase Data API (REST) is reachable with the public key, so every table here has RLS
-- enabled with no policies and no grants for the API roles `anon` / `authenticated`:
-- nothing in these tables can be read or written through the Data API.
-- Every later migration that adds a table must do the same (a test checks it).

create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------------------------------------
-- Course catalogue: a copy of the committed MAIS snapshot (data/mais/<year>/), loaded by
-- backend/scripts/import_catalog.py. IDs are MAIS ids kept as text.
-- The import never deletes programs or courses, and user content (chats, questions, notes,
-- knowledge) references courses without cascade: removing a course can never delete it silently.
-- ---------------------------------------------------------------------------------------------

create table public.programs (
    id            text primary key,                     -- MAIS program id
    code          text not null unique,                 -- e.g. HI_Bc_D_sk
    name          text not null,
    degree        text not null check (degree in ('bc', 'bc_po', 'ing')),
    language      text not null check (language in ('sk', 'en')),
    method        text not null check (method in ('prezencna', 'kombinovana')),
    years         smallint not null check (years between 1 and 6),
    academic_year text not null                         -- e.g. 2026/2027
);

create table public.courses (
    id               text primary key,                  -- MAIS predmetId of the information sheet
    code             text not null,
    name             text not null,
    credits          smallint not null check (credits >= 0),
    semesters        text[] not null
        check (cardinality(semesters) > 0 and semesters <@ array['ZS', 'LS']),
    academic_year    text not null,
    source_url       text not null,                     -- permanent link to the sheet in MAIS
    sheet_changed_on date,                              -- "Dátum poslednej zmeny"; null if missing
    fetched_at       timestamptz not null,              -- when the sheet was scraped
    unique (academic_year, code)
);

create table public.program_courses (
    program_id text not null references public.programs (id) on delete cascade,
    course_id  text not null references public.courses (id) on delete cascade,
    year       smallint not null check (year between 1 and 6),
    semester   text not null check (semester in ('ZS', 'LS')),
    type       text not null check (type in ('P', 'PV', 'V')),
    state_exam boolean not null,
    primary key (program_id, course_id, year, semester, type, state_exam)
);

create index program_courses_course_idx on public.program_courses (course_id);

-- ---------------------------------------------------------------------------------------------
-- Users. Accounts live in Supabase Auth (auth.users); this is the app's profile of each account.
-- ---------------------------------------------------------------------------------------------

create table public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    nickname    text not null unique check (char_length(nickname) between 2 and 40),
    role        text not null default 'student' check (role in ('student', 'vyucujuci')),
    -- "Moje predmety": program, year and semester of a student; all three or none
    program_id  text references public.programs (id),
    year        smallint check (year between 1 and 6),
    semester    text check (semester in ('ZS', 'LS')),
    testovacie  boolean not null default false,
    created_at  timestamptz not null default now(),
    check ((program_id is null) = (year is null) and (year is null) = (semester is null))
);

-- Courses a teacher may verify answers for and write "Aktuálna informácia k predmetu" to.
create table public.teacher_courses (
    teacher_id uuid not null references public.profiles (id) on delete cascade,
    course_id  text not null references public.courses (id) on delete cascade,
    primary key (teacher_id, course_id)
);

create index teacher_courses_course_idx on public.teacher_courses (course_id);

-- ---------------------------------------------------------------------------------------------
-- Chat with the assistant: one chat = one course.
-- ---------------------------------------------------------------------------------------------

create table public.chats (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles (id) on delete cascade,
    course_id   text not null references public.courses (id),
    title       text check (char_length(title) <= 200),   -- shown in "História"
    testovacie  boolean not null default false,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index chats_user_idx on public.chats (user_id, updated_at desc);

create table public.chat_messages (
    id          uuid primary key default gen_random_uuid(),
    chat_id     uuid not null references public.chats (id) on delete cascade,
    role        text not null check (role in ('user', 'assistant')),
    content     text not null check (char_length(content) between 1 and 20000),
    language    text check (language in ('sk', 'en')),
    -- assistant messages only: found = false is a "Neviem" answer; sources = the sources exactly
    -- as shown under the answer (type, section, quote, URL, date, author, verified)
    found       boolean,
    sources     jsonb,
    created_at  timestamptz not null default now(),
    check ((role = 'assistant') = (found is not null)),
    check (role = 'assistant' or sources is null)
);

create index chat_messages_chat_idx on public.chat_messages (chat_id, created_at);

-- ---------------------------------------------------------------------------------------------
-- "Otázky komunity": published questions and people's answers.
-- A question is open while it has no visible answer; the status is derived, not stored.
-- ---------------------------------------------------------------------------------------------

create table public.questions (
    id                uuid primary key default gen_random_uuid(),
    course_id         text not null references public.courses (id),
    author_id         uuid not null references public.profiles (id) on delete cascade,
    text              text not null check (char_length(text) between 3 and 1000),
    language          text check (language in ('sk', 'en')),
    -- the "Neviem" answer the question was published from (null if written directly)
    source_message_id uuid references public.chat_messages (id) on delete set null,
    -- for "similar questions" before publishing
    embedding         extensions.vector(768),
    embed_model       text,
    hidden_at         timestamptz,                      -- hidden as spam by a teacher
    hidden_by         uuid references public.profiles (id) on delete set null,
    testovacie        boolean not null default false,
    created_at        timestamptz not null default now(),
    check ((embedding is null) = (embed_model is null))
);

create index questions_course_idx on public.questions (course_id, created_at desc);
create index questions_author_idx on public.questions (author_id);

create table public.answers (
    id          uuid primary key default gen_random_uuid(),
    question_id uuid not null references public.questions (id) on delete cascade,
    author_id   uuid not null references public.profiles (id) on delete cascade,
    text        text not null check (char_length(text) between 1 and 4000),
    -- 'teacher' = a teacher's own answer, verified from the start; a teacher never edits a
    -- student's answer, they verify it or add their own
    kind        text not null check (kind in ('student', 'teacher')),
    verified_at timestamptz,                            -- null = "Neoverené"
    verified_by uuid references public.profiles (id) on delete set null,
    hidden_at   timestamptz,                            -- hidden as spam by a teacher
    hidden_by   uuid references public.profiles (id) on delete set null,
    testovacie  boolean not null default false,
    created_at  timestamptz not null default now(),
    check (kind = 'student' or verified_at is not null)
);

create index answers_question_idx on public.answers (question_id, created_at);
create index answers_author_idx on public.answers (author_id);

-- "Poďakovať": at most once per user and answer.
create table public.answer_thanks (
    answer_id  uuid not null references public.answers (id) on delete cascade,
    user_id    uuid not null references public.profiles (id) on delete cascade,
    testovacie boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (answer_id, user_id)
);

-- "Aktuálna informácia k predmetu": one current text per course, written by a teacher.
-- The assistant uses it as verified and ranks it above the sheet; the MAIS sheet is not changed.
create table public.course_notes (
    course_id  text primary key references public.courses (id),
    text       text not null check (char_length(text) between 1 and 4000),
    author_id  uuid not null references public.profiles (id) on delete cascade,
    testovacie boolean not null default false,
    updated_at timestamptz not null default now()
);

-- "Upozornenia": e.g. "someone answered your question".
create table public.notifications (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references public.profiles (id) on delete cascade,
    type        text not null check (type in ('question_answered')),
    question_id uuid references public.questions (id) on delete cascade,
    answer_id   uuid references public.answers (id) on delete cascade,
    read_at     timestamptz,
    created_at  timestamptz not null default now()
);

create index notifications_user_idx on public.notifications (user_id, created_at desc);

-- ---------------------------------------------------------------------------------------------
-- Knowledge base: everything the assistant searches, per course.
--   sheet        a part of the MAIS information sheet (section + text)
--   answer       a community answer (verified or not: see answers.verified_at)
--   course_note  the teacher's "Aktuálna informácia k predmetu"
-- Written only through one backend function (embedding + cache invalidation live there).
-- Sources, dates and authors shown to the user come from these rows and their parents,
-- never from the model.
-- ---------------------------------------------------------------------------------------------

create table public.knowledge_chunks (
    id           uuid primary key default gen_random_uuid(),
    course_id    text not null references public.courses (id),
    source_type  text not null check (source_type in ('sheet', 'answer', 'course_note')),
    answer_id    uuid references public.answers (id) on delete cascade,
    section      text,                                  -- sheet section label, e.g. "Stručná osnova"
    chunk_index  smallint not null default 0 check (chunk_index >= 0),
    content      text not null check (char_length(content) > 0),
    content_hash text not null,                         -- re-embed only when the text changes
    embedding    extensions.vector(768),
    embed_model  text,                                  -- vectors of different models never mix
    created_at   timestamptz not null default now(),
    check ((source_type = 'answer') = (answer_id is not null)),
    check ((source_type = 'sheet') = (section is not null)),
    check ((embedding is null) = (embed_model is null))
);

create index knowledge_chunks_course_idx on public.knowledge_chunks (course_id, source_type);
create unique index knowledge_chunks_sheet_key
    on public.knowledge_chunks (course_id, section, chunk_index) where source_type = 'sheet';
create unique index knowledge_chunks_answer_key
    on public.knowledge_chunks (answer_id, chunk_index) where source_type = 'answer';
create unique index knowledge_chunks_note_key
    on public.knowledge_chunks (course_id, chunk_index) where source_type = 'course_note';

-- ---------------------------------------------------------------------------------------------
-- Close the Data API: RLS on, no policies, no grants for the public API roles.
-- ---------------------------------------------------------------------------------------------

alter table public.programs         enable row level security;
alter table public.courses          enable row level security;
alter table public.program_courses  enable row level security;
alter table public.profiles         enable row level security;
alter table public.teacher_courses  enable row level security;
alter table public.chats            enable row level security;
alter table public.chat_messages    enable row level security;
alter table public.questions        enable row level security;
alter table public.answers          enable row level security;
alter table public.answer_thanks    enable row level security;
alter table public.course_notes     enable row level security;
alter table public.notifications    enable row level security;
alter table public.knowledge_chunks enable row level security;

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
