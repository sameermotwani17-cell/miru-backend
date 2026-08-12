-- MIRU initial schema.
--
-- The backend also creates these tables on first connect (store/db.py), so a
-- fresh deployment self-heals. This file exists so the schema is reviewable,
-- diffable and applied deliberately rather than as a side effect of the first
-- request that happens to reach the database.
--
-- APPLIED: Supabase project `gomi-snap` (ref govvyvhfkynupdbvghna,
-- ap-south-1). MIRU shares that project's database because the free plan
-- caps an organization at two projects. The three tables below are the only
-- ones MIRU touches; gomi-snap's own tables (cities, materials,
-- waste_categories, rules, healthcheck) are untouched and unrelated.
--
-- Sharing means one connection pool and one storage quota across two
-- applications. Move MIRU to its own project when the org has a free slot or
-- moves to Pro.

-- Final debrief payload per session: radar scores, transcript, coaching
-- feedback and the final report, stored as one document.
CREATE TABLE IF NOT EXISTS interview_results (
    session_id TEXT PRIMARY KEY,
    results    JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Candidate identity, company, language, CV context and interview timer.
-- Previously an in-process dict, which cannot work across serverless
-- invocations: session/start and the next interview/turn may land on
-- different instances.
CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id TEXT PRIMARY KEY,
    state      JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Turn-by-turn transcript, one JSONB array per session. This is the single
-- source of truth the backend rebuilds conversation history from; client-sent
-- history is never trusted, which is what makes the prompt-injection
-- guarantee hold.
CREATE TABLE IF NOT EXISTS interview_turns (
    session_id TEXT PRIMARY KEY,
    turns      JSONB        NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Supports pruning abandoned sessions. Nothing currently deletes old rows, so
-- these tables grow without bound; a scheduled cleanup is worth adding before
-- this sees real traffic.
CREATE INDEX IF NOT EXISTS interview_sessions_updated_at_idx
    ON interview_sessions (updated_at);
CREATE INDEX IF NOT EXISTS interview_turns_updated_at_idx
    ON interview_turns (updated_at);
CREATE INDEX IF NOT EXISTS interview_results_updated_at_idx
    ON interview_results (updated_at);

-- Enable RLS with no policies.
--
-- The backend reaches these tables over a direct Postgres connection as the
-- `postgres` role, which has BYPASSRLS, so this does not affect the app. What
-- it does do is deny the `anon` and `authenticated` roles entirely — so if the
-- project's anon key is ever exposed in a client bundle, candidate CVs,
-- transcripts and scores are still not readable through PostgREST.
--
-- This is safe precisely because nothing here is accessed via the Supabase
-- client libraries. Do not copy this pattern to a table your frontend queries
-- directly: RLS with no policies blocks all such access.
ALTER TABLE interview_results   ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_turns     ENABLE ROW LEVEL SECURITY;
