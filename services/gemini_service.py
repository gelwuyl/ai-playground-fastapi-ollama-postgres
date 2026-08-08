"""Gemini API service — replaces local Ollama.

Uses the google-genai SDK to call the Gemini API.
"""
import os

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemma-4-26b-a4b-it")

_client = genai.Client(api_key=GEMINI_API_KEY)


def call_gemini(prompt: str, system_prompt: str | None = None) -> str:
    """Send a prompt to Gemini and return the text response."""
    config = None
    if system_prompt:
        config = types.GenerateContentConfig(system_instruction=system_prompt)

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return response.text