"""POST /api/ask — ask a question, get a Gemini answer, save to history."""
from services.llm_adapter import call_model
from services.interaction_service import save_interaction, fetch_recent_history
from services.vercel_handler import VercelHandler

SYSTEM_PROMPT = (
    "You are a concise, helpful assistant. "
    "Answer in one short paragraph (under 80 words). "
    "If you don't know, say so plainly."
)


class handler(VercelHandler):
    def do_POST(self):
        try:
            body = self.read_json()
        except Exception:
            return self.json_response({"detail": "Invalid JSON body."}, 400)

        question = (body.get("question") or "").strip()
        if not question:
            return self.json_response({"detail": "Please enter a question."}, 400)

        answer = call_model(question, system_prompt=SYSTEM_PROMPT)
        save_interaction(question, answer)

        return self.json_response(
            {"answer": answer, "history": fetch_recent_history()}
        )