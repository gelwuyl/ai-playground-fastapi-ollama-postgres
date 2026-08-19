"""LLM adapter that selects an implementation at runtime.

Priority:
 - If OPENROUTER_API_KEY is set, use services.openrouter_service.call_openrouter
 - Else if OLLAMA_BASE_URL is set, use app.services.ollama_service.call_ollama
 - Otherwise raise a clear error.

This keeps business logic shared while allowing local Ollama testing and cloud OpenRouter deployment.
"""
import os
from typing import Optional

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL")

# Lazy imports so importing this module in different runtimes doesn't fail at import time.

def call_model(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Call the configured model and return text.

    Args:
        prompt: user prompt
        system_prompt: optional system instruction
    """
    if OPENROUTER_KEY:
        from services.openrouter_service import call_openrouter

        return call_openrouter(prompt, system_prompt=system_prompt)

    if OLLAMA_BASE:
        try:
            from app.services.ollama_service import call_ollama
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Failed to import local Ollama service") from exc
        return call_ollama(prompt)

    raise RuntimeError("No LLM backend configured. Set OPENROUTER_API_KEY or OLLAMA_BASE_URL.")
