"""GET /api/stories — return recent bedtime stories."""
import json

from services.story_service import fetch_recent_stories


def handler(request):
    return json.dumps(fetch_recent_stories())