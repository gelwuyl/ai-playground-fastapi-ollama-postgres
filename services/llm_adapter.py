"""LLM adapter that selects an implementation at runtime.

Priority:
 - If GEMINI_API_KEY is set, use services.gemini_service.call_gemini
 - Else if OLLAMA_BASE_URL is set, use app.services.ollama_service.call_ollama
 - Otherwise raise a clear error.

This keeps business logic shared while allowing local Ollama testing and cloud Gemini deployment.
"""
import os
from typing import Optional

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL")

# Lazy imports so importing this module in different runtimes doesn't fail at import time.

def call_model(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Call the configured model and return text.

    Args:
        prompt: user prompt
        system_prompt: optional system instruction (used by Gemini; Ollama uses its own system prompt)
    """
    if GEMINI_KEY:
        # Use Gemini service
        from services.gemini_service import call_gemini

        return call_gemini(prompt, system_prompt=system_prompt)

    if OLLAMA_BASE:
        # Use local Ollama service (app.services.ollama_service)
        # Import from the app package to reuse the existing Ollama helper
        try:
            from app.services.ollama_service import call_ollama
        except Exception as exc:  # pragma: no cover - import-time fallbacks
            raise RuntimeError("Failed to import local Ollama service") from exc
        # ollama_service.call_ollama already applies a system prompt internally
        return call_ollama(prompt)

    raise RuntimeError("No LLM backend configured. Set GEMINI_API_KEY or OLLAMA_BASE_URL.")
