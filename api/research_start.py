"""POST /api/research/start — create a research session, return session_id."""
from services.database import get_conn
from services.vercel_handler import VercelHandler


class handler(VercelHandler):
    def do_POST(self):
        try:
            body = self.read_json()
        except Exception:
            return self.json_response({"detail": "Invalid JSON body."}, 400)

        query = (body.get("query") or "").strip()
        if not query:
            return self.json_response({"detail": "Please enter a research question."}, 400)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO research_sessions (query, status) VALUES (%s, 'PENDING') RETURNING id",
                    (query,),
                )
                session_id = cur.fetchone()[0]
            conn.commit()

        return self.json_response({"session_id": session_id, "query": query})
