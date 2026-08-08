"""GET /api/stories — return recent bedtime stories."""
from services.story_service import fetch_recent_stories
from services.vercel_handler import VercelHandler


class handler(VercelHandler):
    def do_GET(self):
        return self.json_response(fetch_recent_stories())