"""POST /api/story — generate a bedtime story with Gemini, save it."""
import json

from services.llm_adapter import call_model
from services.story_service import save_story, fetch_recent_stories

SYSTEM_PROMPT = (
    "You are a warm, imaginative bedtime storyteller for children. "
    "Write a gentle, calming story of 150-250 words with a happy ending. "
    "Use simple, soothing language."
)


def handler(request):
    try:
        body = request.json()
    except Exception:
        return json.dumps({"detail": "Invalid JSON body."}), 400

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return json.dumps({"detail": "Please describe the story you want."}), 400

    story = call_model(prompt, system_prompt=SYSTEM_PROMPT)
    save_story(prompt, story)

    return json.dumps({"story": story, "history": fetch_recent_stories()})