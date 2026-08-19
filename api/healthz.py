"""GET /api/healthz — report OpenRouter and Postgres connectivity."""
from services.database import get_conn
from services.vercel_handler import VercelHandler


class handler(VercelHandler):
    def do_GET(self):
        status = {"openrouter": False, "postgres": False}

        try:
            from services.openrouter_service import OPENROUTER_API_KEY
            status["openrouter"] = bool(OPENROUTER_API_KEY)
        except Exception:
            pass

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            status["postgres"] = True
        except Exception:
            pass

        return self.json_response(status)