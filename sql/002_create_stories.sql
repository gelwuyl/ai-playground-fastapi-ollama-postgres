-- Bedtime Story Generator table (Vercel / Gemini app)
CREATE TABLE IF NOT EXISTS stories (
    id          SERIAL PRIMARY KEY,
    prompt      TEXT NOT NULL,
    story       TEXT NOT NULL,
    model_name  TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);