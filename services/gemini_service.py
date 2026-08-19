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


import json
import re


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if the model wrapped its JSON."""
    text = text.strip()
    if text.startswith("```"):
        # drop opening fence, optional language tag
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def call_gemini_json(prompt: str, system_prompt: str | None, schema: dict) -> dict:
    """Call Gemini and force a JSON object matching `schema`.

    Uses response_mime_type + response_schema for structured output, then
    strips any stray markdown fences and retries up to 3x on parse failure.
    Raises ValueError if a valid JSON object cannot be obtained.
    """
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
    )

    last_err = None
    for _ in range(3):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()
            text = _strip_fences(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            continue
        except Exception as e:  # network/API errors
            last_err = e
            continue

    raise ValueError(f"Gemini did not return valid JSON: {last_err}")