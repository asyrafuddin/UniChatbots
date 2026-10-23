-- Database schema for the University Assistant.
-- Run once in Supabase → SQL Editor → New query → paste → Run. Safe to re-run.

-- pgvector adds a "vector" column type and similarity operators to Postgres.
create extension if not exists vector with schema extensions;

-- One row per document chunk (from data/processed/chunks.jsonl) with its bge-m3 embedding.
create table if not exists public.chunks (
  id          text primary key,
  text        text not null,
  source      text not null,
  page_or_url text not null,               -- page number or URL, stored as text
  section     text not null default '',
  embedding   extensions.vector(1024) not null   -- BAAI/bge-m3 vectors have 1024 numbers
);
-- No vector index on purpose: with ~1,700 rows an exact scan takes milliseconds and gives the
-- same results as the local FAISS index. Add an HNSW index if this grows past ~100k rows.

-- One row per question asked on the website.
create table if not exists public.chats (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  question    text not null,
  language    text,                          -- en / ms / ko / mixed (the website's guess)
  answer      text not null,
  citations   jsonb not null default '[]',   -- the sources shown under the answer
  found       boolean not null,              -- false when the documents didn't contain the answer
  model       text not null,                 -- which LLM wrote the answer
  latency_ms  integer
);

-- Row Level Security with NO policies: the website's publishable key can't read or write
-- these tables. Only the Python backend, using the secret key, can.
alter table public.chunks enable row level security;
alter table public.chats  enable row level security;

-- Vector search: the chunks closest to a question's embedding.
-- Vectors are unit length, so inner product (<#> returns it negated) equals cosine similarity.
create or replace function public.match_chunks(query_embedding extensions.vector(1024), match_count int)
returns table (id text, text text, source text, page_or_url text, section text, similarity float)
language sql stable
set search_path = public, extensions
as $$
  select c.id, c.text, c.source, c.page_or_url, c.section, -(c.embedding <#> query_embedding) as similarity
  from public.chunks c
  order by c.embedding <#> query_embedding
  limit match_count;
$$;
revoke execute on function public.match_chunks(extensions.vector, int) from public, anon, authenticated;

-- Public settings the website reads with its publishable key, e.g. the backend's current address
-- (a free Cloudflare quick tunnel gets a new random URL every time it starts).
create table if not exists public.public_config (
  key         text primary key,
  value       text not null,
  updated_at  timestamptz not null default now()
);
alter table public.public_config enable row level security;
drop policy if exists "Anyone can read public config" on public.public_config;
create policy "Anyone can read public config" on public.public_config for select to anon, authenticated using (true);
-- No insert/update policy: only the backend (secret key) can change these values.
