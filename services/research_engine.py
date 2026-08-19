"""Mr. Kaypoh — pure ReAct engine (no HTTP/Vercel imports).

run_one_step takes the current session + prior steps, asks the model for the
next action, executes ONE tool, enforces the 3-page gate, and returns the new
step dict. The API handler persists it and returns it to the browser.
"""
from services import research_service as rs


def run_one_step(session: dict, steps: list[dict]) -> dict:
    """Execute exactly one ReAct step. Returns a step dict to persist.

    step keys: step_number, reason, action, query, url, observation, chars_read
    Special action 'REFUSED' is used when FINISH is blocked by the 3-page rule.
    """
    step_number = len(steps) + 1

    # Step limit reached -> refuse to continue
    if step_number > rs.STEP_LIMIT:
        return {
            "step_number": step_number,
            "reason": "Step limit reached.",
            "action": "REFUSED",
            "query": None,
            "url": None,
            "observation": f"Step limit of {rs.STEP_LIMIT} reached without FINISH.",
            "chars_read": 0,
        }

    try:
        action = rs.decide_action(session["query"], steps)
    except Exception as e:
        return {
            "step_number": step_number,
            "reason": f"Model error: {e}",
            "action": "REFUSED",
            "query": None,
            "url": None,
            "observation": f"Model failed to return valid JSON: {e}",
            "chars_read": 0,
        }

    act = action.get("action")
    reason = action.get("reason", "")

    if act == "SEARCH":
        q = action.get("query", "")
        results = rs.search_web(q)
        summary = f"{len(results)} results"
        return {
            "step_number": step_number,
            "reason": reason,
            "action": "SEARCH",
            "query": q,
            "url": None,
            "observation": summary,
            "chars_read": 0,
        }

    if act == "READ":
        url = action.get("url", "")
        # Refuse duplicate reads
        already = {s["url"] for s in steps if s["action"] == "READ"}
        if url in already:
            return {
                "step_number": step_number,
                "reason": reason,
                "action": "READ",
                "query": None,
                "url": url,
                "observation": "REFUSED: already read this URL.",
                "chars_read": 0,
            }
        text, chars = rs.read_webpage(url)
        summary = f"{chars} chars" if chars > 0 else "0 chars (refused)"
        return {
            "step_number": step_number,
            "reason": reason,
            "action": "READ",
            "query": None,
            "url": url,
            "observation": summary,
            "chars_read": chars,
        }

    if act == "FINISH":
        report = action.get("report", "")
        pages_read = rs.count_pages_read(steps)
        if pages_read < rs.PAGE_LIMIT:
            obs = (f"FINISH refused: only {pages_read} pages read, "
                   f"{rs.PAGE_LIMIT} required. Choose READ next.")
            return {
                "step_number": step_number,
                "reason": reason,
                "action": "REFUSED",
                "query": None,
                "url": None,
                "observation": obs,
                "chars_read": 0,
                "report": report,
            }
        if not report.strip():
            obs = "FINISH refused: report is empty. Choose READ next."
            return {
                "step_number": step_number,
                "reason": reason,
                "action": "REFUSED",
                "query": None,
                "url": None,
                "observation": obs,
                "chars_read": 0,
                "report": report,
            }
        # Accepted
        return {
            "step_number": step_number,
            "reason": reason,
            "action": "FINISH",
            "query": None,
            "url": None,
            "observation": "Report accepted.",
            "chars_read": 0,
            "report": report,
        }

    # Unknown action
    return {
        "step_number": step_number,
        "reason": reason,
        "action": "REFUSED",
        "query": None,
        "url": None,
        "observation": f"Unknown action '{act}', ignoring.",
        "chars_read": 0,
    }
