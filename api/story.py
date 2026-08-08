"""POST /api/story — generate a bedtime story with Gemini, save it."""
from services.llm_adapter import call_model
from services.story_service import save_story, fetch_recent_stories
from services.vercel_handler import VercelHandler

SYSTEM_PROMPT = (
    "You are a warm, imaginative bedtime storyteller for children. "
    "Write a gentle, calming story of 150-250 words with a happy ending. "
    "Use simple, soothing language."
)


class handler(VercelHandler):
    def do_POST(self):
        try:
            body = self.read_json()
        except Exception:
            return self.json_response({"detail": "Invalid JSON body."}, 400)

        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            return self.json_response({"detail": "Please describe the story you want."}, 400)

        story = call_model(prompt, system_prompt=SYSTEM_PROMPT)
        save_story(prompt, story)

        return self.json_response(
            {"story": story, "history": fetch_recent_stories()}
        )