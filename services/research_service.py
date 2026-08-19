"""Mr. Kaypoh — research agent tools and helpers.

Pure-ish service layer: search_web, read_webpage, prompt building, evaluation.
No Vercel/HTTP imports here so the logic stays testable.
"""
import os
import httpx
from bs4 import BeautifulSoup

STEP_LIMIT = 10
PAGE_LIMIT = 3
PAGE_TEXT_LIMIT = 5000
SEARCH_RESULTS = 5

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

USE_FIXTURES = os.environ.get("USE_FIXTURES", "0") == "1"

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "action": {"type": "string", "enum": ["SEARCH", "READ", "FINISH"]},
        "query": {"type": "string"},
        "url": {"type": "string"},
        "report": {"type": "string"},
    },
    "required": ["reason", "action"],
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def search_web(query: str) -> list[dict]:
    """Search the web and return up to 5 results, each with title, url, snippet."""
    if USE_FIXTURES:
        from services.fixtures import FIXTURE_SEARCH
        return [r for r in FIXTURE_SEARCH if query.lower() in r.get("query", "").lower()][:SEARCH_RESULTS] or FIXTURE_SEARCH[:SEARCH_RESULTS]

    try:
        resp = httpx.get(
            "https://serpapi.com/search.json",
            params={"q": query, "num": SEARCH_RESULTS, "api_key": os.environ["SERPAPI_KEY"]},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        organic = resp.json().get("organic_results", [])
    except Exception as e:
        print(f"Search failed: {type(e).__name__}: {e}")
        return []

    out = []
    for r in organic[:SEARCH_RESULTS]:
        out.append({
            "title": r.get("title", ""),
            "url": r.get("link") or r.get("url", ""),
            "snippet": r.get("snippet", ""),
        })
    return out


def read_webpage(url: str) -> tuple[str, int]:
    """Open one web page and return (visible_text_capped, chars_read)."""
    if USE_FIXTURES:
        from services.fixtures import FIXTURE_PAGES
        text = FIXTURE_PAGES.get(url, "")
        return text[:PAGE_TEXT_LIMIT], len(text[:PAGE_TEXT_LIMIT])

    try:
        r = httpx.get(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=30, follow_redirects=True)
    except Exception as e:
        print(f"Page fetch failed: {url}: {type(e).__name__}: {e}")
        return "", 0
    if r.status_code != 200:
        print(f"Page fetch failed: status {r.status_code} {url}")
        return "", 0

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)[:PAGE_TEXT_LIMIT]
    return cleaned, len(cleaned)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------
TOOL_DESCRIPTIONS = f"""You have three tools:

SEARCH  Search the web for a query. Returns a list of results with title, url, snippet.
        Use this when you need to find sources.
        Call with: {{"action": "SEARCH", "query": "..."}}

READ    Read one web page and return its text. Returns the visible text (capped).
        Use this to gather evidence from a specific url.
        Call with: {{"action": "READ", "url": "..."}}

FINISH  Write the report. Only choose this after you have read at least three
        different web pages. Base the report on the text of those pages. Search
        result titles and snippets are not enough on their own. Price tickers,
        shop pages and product listings give you a number but no explanation, so
        prefer news articles, analysis and official sources when you choose what
        to read.
        Call with: {{"action": "FINISH", "report": "..."}}
"""


def build_state_prompt(goal: str, steps: list[dict]) -> str:
    system = (
        "You are a research agent. You decide what to do next by reasoning, then act "
        "with one tool, then observe the result. Repeat until you have enough evidence.\n\n"
        f"You may take at most {STEP_LIMIT} steps total.\n\n"
        + TOOL_DESCRIPTIONS +
        "Reply with ONLY a JSON object, one of these three shapes:\n"
        '{"reason": "one short sentence", "action": "SEARCH", "query": "..."}\n'
        '{"reason": "one short sentence", "action": "READ", "url": "..."}\n'
        '{"reason": "one short sentence", "action": "FINISH", "report": "..."}\n\n'
        "End every finding in the report with the URL it came from in square brackets. "
        "If a finding comes from what you already knew rather than from a page you read, "
        "end it with [no source] instead.\n"
    )
    history = "\n".join(
        f"STEP {s['step_number']}: {s['action']} {s.get('query') or s.get('url') or ''}\n  -> {s.get('observation', '')}"
        for s in steps
    ) or "(no steps taken yet)"
    return (
        system
        + f"\nGOAL: {goal}\n\nWHAT HAS HAPPENED SO FAR:\n{history}\n\nNext action as JSON:"
    )


def decide_action(goal: str, steps: list[dict]) -> dict:
    """Ask the model for the next action. Returns a parsed dict."""
    from services.openrouter_service import call_openrouter_json  # lazy: keeps module SDK-free at import
    prompt = build_state_prompt(goal, steps)
    return call_openrouter_json(prompt, system_prompt=None, schema=ACTION_SCHEMA)


def count_pages_read(steps: list[dict]) -> int:
    """Count distinct URLs successfully read (chars_read > 0)."""
    return len({s["url"] for s in steps if s["action"] == "READ" and s.get("chars_read", 0) > 0})


# ---------------------------------------------------------------------------
# Evaluation (6 checks)
# ---------------------------------------------------------------------------
def evaluate_run(steps: list[dict], report: str) -> dict:
    used_search = any(s["action"] == "SEARCH" for s in steps)
    read_urls = {s["url"] for s in steps if s["action"] == "READ" and s.get("chars_read", 0) > 0}
    finished = any(s["action"] == "FINISH" for s in steps)
    checks = [
        ("the search tool was used at least once", used_search),
        ("more than one distinct source was consulted", len(read_urls) > 1),
        ("the run stayed within the step limit", finished),
        ("the brief contains a recommendation", "recommend" in (report or "").lower()),
        ("the brief lists at least three sources", len(read_urls) >= 3),
        ("no finding ends with [no source]", "[no source]" not in (report or "")),
    ]
    score = sum(1 for _, ok in checks if ok)
    return {"score": score, "total": len(checks), "checks": [
        {"name": n, "pass": ok} for n, ok in checks
    ]}
