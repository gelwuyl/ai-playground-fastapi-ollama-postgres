"""GET /api/history — return recent question-log interactions."""
import json

from services.interaction_service import fetch_recent_history


def handler(request):
    return json.dumps(fetch_recent_history())