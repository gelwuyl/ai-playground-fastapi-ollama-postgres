"""GET /api/research/status?session_id= — return session + all steps (refresh recovery)."""
from urllib.parse import urlparse, parse_qs

from services.database import get_conn
from services.vercel_handler import VercelHandler


class handler(VercelHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        session_id = qs.get("session_id", [None])[0]
        if not session_id:
            return self.json_response({"detail": "session_id required."}, 400)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, query, status, final_report, score FROM research_sessions WHERE id=%s",
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return self.json_response({"detail": "Session not found."}, 404)
                session = {"id": row[0], "query": row[1], "status": row[2],
                           "final_report": row[3], "score": row[4]}
                cur.execute(
                    "SELECT step_number, reason, action, query, url, observation, chars_read "
                    "FROM research_steps WHERE session_id=%s ORDER BY step_number",
                    (session_id,),
                )
                cols = ["step_number", "reason", "action", "query", "url", "observation", "chars_read"]
                steps = [dict(zip(cols, r)) for r in cur.fetchall()]

        return self.json_response({"session": session, "steps": steps})
