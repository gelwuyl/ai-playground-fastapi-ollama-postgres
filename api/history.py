"""GET /api/history — return recent question-log interactions."""
from services.interaction_service import fetch_recent_history
from services.vercel_handler import VercelHandler


class handler(VercelHandler):
    def do_GET(self):
        return self.json_response(fetch_recent_history())