"""POST /api/research/eval — run the 6 evaluation checks on a completed session."""
from services.database import get_conn
from services.vercel_handler import VercelHandler
from services import research_service as rs


class handler(VercelHandler):
    def do_POST(self):
        try:
            body = self.read_json()
        except Exception:
            return self.json_response({"detail": "Invalid JSON body."}, 400)

        session_id = body.get("session_id")
        if not session_id:
            return self.json_response({"detail": "session_id required."}, 400)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT query, final_report FROM research_sessions WHERE id=%s", (session_id,)
                )
                row = cur.fetchone()
                if not row:
                    return self.json_response({"detail": "Session not found."}, 404)
                query, report = row
                cur.execute(
                    "SELECT step_number, reason, action, query, url, observation, chars_read "
                    "FROM research_steps WHERE session_id=%s ORDER BY step_number",
                    (session_id,),
                )
                cols = ["step_number", "reason", "action", "query", "url", "observation", "chars_read"]
                steps = [dict(zip(cols, r)) for r in cur.fetchall()]

        result = rs.evaluate_run(steps, report)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE research_sessions SET score=%s WHERE id=%s", (result["score"], session_id))
            conn.commit()

        return self.json_response(result)
