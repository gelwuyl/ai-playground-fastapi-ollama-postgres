"""POST /api/ask — ask a question, get a Gemini answer, save to history."""
import json

from services.llm_adapter import call_model
from services.interaction_service import save_interaction, fetch_recent_history

SYSTEM_PROMPT = (
    "You are a concise, helpful assistant. "
    "Answer in one short paragraph (under 80 words). "
    "If you don't know, say so plainly."
)


def handler(request):
    try:
        body = request.json()
    except Exception:
        return json.dumps({"detail": "Invalid JSON body."}), 400

    question = (body.get("question") or "").strip()
    if not question:
        return json.dumps({"detail": "Please enter a question."}), 400

    answer = call_model(question, system_prompt=SYSTEM_PROMPT)
    save_interaction(question, answer)

    return json.dumps({"answer": answer, "history": fetch_recent_history()})