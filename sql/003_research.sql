-- Mr. Kaypoh (Research Agent) tables for the Vercel (Gemini) deployment.
-- Run against Vercel Postgres (or local Postgres for dev).

-- Table 1: Research sessions (one row per research question submitted)
CREATE TABLE IF NOT EXISTS research_sessions (
    id          SERIAL PRIMARY KEY,
    query      TEXT NOT NULL,
    final_report TEXT,
    status     TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | RUNNING | COMPLETED | FAILED
    score      INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: Research steps (one row per ReAct loop step; the agentic trace)
CREATE TABLE IF NOT EXISTS research_steps (
    id           SERIAL PRIMARY KEY,
    session_id   INT NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    step_number  INT NOT NULL,
    reason       TEXT,
    action       TEXT NOT NULL,   -- SEARCH | READ | FINISH | REFUSED
    query        TEXT,
    url          TEXT,
    observation  TEXT,
    chars_read   INT DEFAULT 0,
    report       TEXT,          -- present only on accepted FINISH steps
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_steps_session
    ON research_steps(session_id);
