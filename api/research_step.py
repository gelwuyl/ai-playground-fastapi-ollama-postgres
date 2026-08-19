"""POST /api/research/step — execute ONE ReAct step for a session."""
import json

from services.database import get_conn
from services.vercel_handler import VercelHandler
from services import research_engine as engine
from services import research_service as rs


def _load(session_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, query, status, final_report FROM research_sessions WHERE id=%s",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None, None
            session = {"id": row[0], "query": row[1], "status": row[2], "final_report": row[3]}
            cur.execute(
                "SELECT step_number, reason, action, query, url, observation, chars_read, report "
                "FROM research_steps WHERE session_id=%s ORDER BY step_number",
                (session_id,),
            )
            cols = ["step_number", "reason", "action", "query", "url", "observation", "chars_read", "report"]
            steps = [dict(zip(cols, r)) for r in cur.fetchall()]
    return session, steps


def _persist(session_id, step):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO research_steps "
                "(session_id, step_number, reason, action, query, url, observation, chars_read, report) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (session_id, step["step_number"], step["reason"], step["action"],
                 step.get("query"), step.get("url"), step.get("observation"),
                 step.get("chars_read", 0), step.get("report")),
            )
            # If FINISH accepted, save report + mark completed
            if step["action"] == "FINISH":
                cur.execute(
                    "UPDATE research_sessions SET status='COMPLETED', final_report=%s WHERE id=%s",
                    (step.get("report", ""), session_id),
                )
            elif step["step_number"] >= rs.STEP_LIMIT:
                # Step limit reached (whether REFUSED or not) -> FAILED
                cur.execute("UPDATE research_sessions SET status='FAILED' WHERE id=%s", (session_id,))
            else:
                cur.execute("UPDATE research_sessions SET status='RUNNING' WHERE id=%s", (session_id,))
        conn.commit()


class handler(VercelHandler):
    def do_POST(self):
        try:
            body = self.read_json()
        except Exception:
            return self.json_response({"detail": "Invalid JSON body."}, 400)

        session_id = body.get("session_id")
        if not session_id:
            return self.json_response({"detail": "session_id required."}, 400)

        session, steps = _load(session_id)
        if not session:
            return self.json_response({"detail": "Session not found."}, 404)
        if session["status"] == "COMPLETED":
            return self.json_response({"finished": True, "already_done": True, "report": session["final_report"]}, 200)

        step = engine.run_one_step(session, steps)
        _persist(session_id, step)

        finished = step["action"] == "FINISH"
        return self.json_response({
            "step": step,
            "finished": finished,
            "pages_read": rs.count_pages_read(steps + [step]),
            "step_limit": rs.STEP_LIMIT,
        })
