# Plan: Mr. Kaypoh — Research Agent on Vercel

**Goal:** Port Research Scout (ReAct research agent) into existing ai-playground Vercel/Gemini/Postgres stack as a 3rd app card ("Mr. Kaypoh").

> **Scope note:** The student guide's Prompts 1–5 literally build a standalone CLI file `research_agent.py`
> (OpenCode Zen `hy3-free`, `ddgs`, in-memory loop). This plan does NOT emit that file. It PORTS the
> guide's *behavioral requirements* into the existing web stack per the user's explicit instruction to
> integrate as a third app using the existing cloud endpoint (Gemini), same page, and a
> `research_sessions` table. Deviations from the literal guide are listed at the bottom.

## Key constraints discovered (from real deployed code, NOT app/ which is gitignored)
- Vercel uses legacy `BaseHTTPRequestHandler` pattern: `api/*.py` each expose `handler` class. NOT FastAPI in prod.
- No WebSockets. Per-invocation timeout = **300s** (verified via VERCEL_GET_PROJECTS: functionDefaultTimeout=300). Whole 8-step loop could fit in one call, but client-driven stepping still required (no WebSocket + need DB state for refresh).
- Brain = `services/llm_adapter.call_model` -> Gemini via google-genai. Returns plain text only (no JSON schema today).
- DB = `services/database.py` psycopg_pool ConnectionPool (min1 max5, lazy).
- Frontend = plain HTML/JS in `public/`, routed via vercel.json rewrites.
- Local `app/main.py` (FastAPI+Ollama) is excluded from Vercel (.vercelignore).

## Locked decisions (user grill answers)
1. Client-driven stepping: browser calls POST /api/research/step repeatedly; each call = ONE tool action.
2. Schema-enforced JSON + repair fallback (strip ```, retry 3x).
3. Direct SerpApi via httpx (no MCP/Composio overhead for the tool itself — but Composio SerpApi MCP verified working as the credential manager).
4. Cloud/Gemini-only (local Ollama not wired for agent).

## Files to create/modify
- sql/003_research.sql: research_sessions(id,query,final_report,status,score,created_at), research_steps(id,session_id FK,step_number,reason,action,query,url,observation,chars_read,created_at)
- services/gemini_service.py: add call_gemini_json(prompt, system_prompt, schema) with response_mime_type/schema + repair
- services/research_service.py (NEW): STEP_LIMIT=8, PAGE_LIMIT=3, PAGE_TEXT_LIMIT=5000; search_web (SerpApi httpx), read_webpage (httpx+bs4 cap 5000), build_state_prompt, decide_action, count_pages_read, evaluate_run (5 checks)
- services/research_engine.py (NEW, REFINEMENT b): pure-logic core extracted from handler — run_one_step(session, steps, env) returns next step dict WITHOUT touching HTTP/Vercel. Makes the ReAct decision + 3-page gate + tool execution unit-testable. research_step.py becomes a thin wrapper calling this.
- services/fixtures.py (REFINEMENT a): when USE_FIXTURES=1, search_web/read_webpage return saved canned results from a local JSON file (mirrors guide's saved-results fallback) so agent survives SerpApi quota death.
- api/research_start.py POST -> create session PENDING, return session_id
- api/research_step.py POST {session_id} -> thin: load session+steps, call research_engine.run_one_step, persist, return step+finished; step limit -> FAILED
- api/research_status.py GET ?session_id= -> session + steps (refresh recovery)
- api/research_eval.py POST {session_id} -> 6 checks + score (REFINEMENT c adds #6)
- public/research.html + card in index.html + vercel.json rewrite /research -> /research.html
- requirements.txt add beautifulsoup4; .env.example add SERPAPI_KEY, USE_FIXTURES=0

## Staged Build Runbook (CALL annotations)
- Stage 0 Pre-reqs: SERPAPI_SEARCH (Composio) to verify search shape; COMPOSIO_SEARCH_FETCH_URL_CONTENT for page-read test.
- Stage 1 DB: sql/003_research.sql (research_sessions + research_steps). Apply via Composio remote workbench OR psql $DATABASE_URL.
- Stage 2 Gemini JSON: services/gemini_service.call_gemini_json (schema + fence-strip + 3x retry). Verify SDK param name via brave MCP if uncertain.
- Stage 3 Core: services/research_service.py (search_web SerpApi httpx, read_webpage bs4 cap5000, evaluate 5chk), research_engine.py (pure run_one_step), fixtures.py (USE_FIXTURES).
- Stage 4 API: api/research_{start,step,status,eval}.py mirroring api/story.py handler(VercelHandler).
- Stage 5 Frontend: public/research.html + index card + vercel.json /research rewrite. Polls /api/research/step.
- Stage 6 Config: requirements.txt +beautifulsoup4; .env.example +SERPAPI_KEY +USE_FIXTURES=0.
- Stage 7 Deploy: Composio MCP VERCEL_CREATE_NEW_DEPLOYMENT + poll VERCEL_GET_DEPLOYMENT (if exposed) ELSE vercel --prod.
- Stage 8 Verify: vercel dev / deployed URL; CP2-CP5 + refresh + all-403 break.

## MCP availability (VERIFIED 2026-08-18)
- OpenRouter MCP: connected (ping pong) BUT send-message NOT available + credits ~1.6 -> Fusion research BLOCKED.
- Composio MCP: CONNECTED + ACTIVE (tools prefixed mcp_mcp-typescrip_COMPOSIO_*).
  - serpapi toolkit ACTIVE (acct serpapi_pipal-fister) -> SERPAPI_SEARCH works (returns results.organic_results[].{link,position,title}). USE THIS for Mr. Kaypoh SEARCH tool. No key mgmt needed.
  - vercel toolkit ACTIVE (acct vercel_amarin-larin, team_CXkg8eH3yWWK8GjVyinFyAPW, user gelwuyl@icloud.com). VERCEL_GET_PROJECTS works. functionDefaultTimeout=300s (5min). VERCEL_CREATE_NEW_DEPLOYMENT + VERCEL_GET_DEPLOYMENT for deploy.
  - composio_search ACTIVE -> COMPOSIO_SEARCH_WEB, COMPOSIO_SEARCH_FETCH_URL_CONTENT (Exa-based; good for READ tool fallback).
  - browser_tool ACTIVE.
- Brave/SerpApi/Firecrawl MCP: AVAILABLE but Composio serpapi preferred.

## Break points mitigated
timeout(1), non-JSON(2), 429(3), SerpApi empty(4), 403/0chars read(5), dup URL(6), premature FINISH(7), pool exhaustion(8), cold start(9), None text(10), refresh(11), local Ollama JSON(12)

## Residual risks
- SerpApi free = 100/mo; USE_FIXTURES fallback now built in (REFINEMENT a)
- Verify gemma-4-26b supports response_schema
- Pool size 5 fine for single user

## Refinements folded in (user chose "Refine further")
(a) USE_FIXTURES=1 -> services/fixtures.py returns canned SerpApi/reads. Toggle in .env.example.
(b) research_engine.py pure-logic split -> testable without Vercel runtime.
(c) 6th eval check: FAIL if any finding ends with [no source] (guide's optional hardening).

## Port contract (the hard part: restructuring, not logic)

`research_agent.py` runs the ENTIRE ReAct loop in one process with an in-memory `state` list.
Mr. Kaypoh RESTRUCTURES that same logic into **stateless per-step HTTP calls backed by Postgres**.
The loop is NOT copied 1:1 — it is split so the browser drives it and each step is persisted.

### `research_engine.run_one_step(session: dict, steps: list[dict]) -> dict`
- `session` = `{"id", "query", "status", "final_report"}` (loaded from `research_sessions`).
- `steps` = list of prior step dicts loaded from `research_steps` (oldest→newest).
- Returns ONE new `step` dict (never mutates inputs). The API handler persists it and returns it.

### Returned step dict shape (persisted as one `research_steps` row)
```
{
  "step_number":   int,
  "reason":        str,
  "action":        "SEARCH" | "READ" | "FINISH" | "REFUSED",
  "query":         str | None,
  "url":           str | None,
  "observation":   str,
  "chars_read":    int,            # >0 only for successful READ
  "report":        str | None      # present only on accepted FINISH
}
```
Special `action` values:
- `REFUSED` — FINISH blocked by 3-page rule, or duplicate READ, or step limit exceeded, or model JSON error.
- `FINISH` — accepted only when `count_pages_read(steps) >= PAGE_LIMIT (3)`.

### What was ported verbatim vs swapped
| From research_agent.py | In Mr. Kaypoh | Change |
|---|---|---|
| `parse_action` fence+substring repair | `gemini_service._strip_fences` + `call_gemini_json` retry(3x) | Kept repair logic; moved into JSON-mode call |
| `read_webpage` tag-stripping (script/style/nav/footer/header/aside decompose) | `research_service.read_webpage` | Kept verbatim; cap 5000 |
| `TOOL_DESCRIPTIONS` (incl. 3-page FINISH rule) | `research_service.TOOL_DESCRIPTIONS` | Kept verbatim |
| `build_prompt` state formatting | `research_service.build_state_prompt` | Kept; reads from step dicts |
| `evaluate` 5(+1) checks | `research_service.evaluate_run` | Kept; 6th `[no source]` check |
| `ddgs` search | `research_service.search_web` (SerpApi httpx) | Swapped per user |
| raw-HTTP model call | `call_gemini_json` (google-genai) | Swapped per user |
| in-memory `state` list | `research_steps` Postgres table | Restructured |

### API handler responsibilities (api/research_step.py)
1. Load session + steps from DB.
2. If status COMPLETED → return existing report (idempotent).
3. Call `run_one_step(session, steps)`.
4. Persist step; if FINISH → save `final_report` + status COMPLETED; if REFUSED past limit → FAILED.
5. Return `{step, finished, pages_read, step_limit}` to browser.

Browser polls `/api/research/step` every ~1.5s until `finished` or REFUSED-at-limit.

## Deviations from the literal guide (Prompts 1–5)
| Guide | Literal | This plan | Why |
|---|---|---|---|
| Endpoint | OpenCode Zen hy3-free (raw HTTP) | Gemini via llm_adapter | User: "same cloud endpoint as existing app" |
| Search | ddgs (DuckDuckGo scrape) | SerpApi (Composio) | Cloud deploy can't scrape DDG reliably; user approved SerpApi |
| State | in-memory Python list | Postgres research_steps table | User: "create research_sessions table" |
| Runtime | single CLI process, one loop | client-driven stepping (browser polls /api/research/step) | Vercel serverless: no WebSockets, need refresh-safe state |
| Deliverable | research_agent.py (CLI) | web app card + api handlers | User: "integrate as third app Mr. Kaypoh" |

All behavioral requirements preserved: 3-page rule enforced in code, findings end [url]/[no source], two source lists, 5 (+1) eval checks, failure resilience, step limit constant.
