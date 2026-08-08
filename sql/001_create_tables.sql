-- Combined schema for the Vercel (Gemini) deployment.
-- Run against Vercel Postgres (or local Postgres for dev).

-- Table 1: LLM Question Log
CREATE TABLE IF NOT EXISTS interactions (
    id          SERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    model_name  TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Bedtime Story Generator
CREATE TABLE IF NOT EXISTS stories (
    id          SERIAL PRIMARY KEY,
    prompt      TEXT NOT NULL,
    story       TEXT NOT NULL,
    model_name  TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);