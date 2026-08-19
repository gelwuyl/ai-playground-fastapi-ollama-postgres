"""OpenRouter API service — replaces the Gemini SDK with OpenAI-compatible HTTP.

Uses httpx to call OpenRouter's /chat/completions endpoint.
OpenRouter is OpenAI-compatible, so this is the same format the student
guide's Prompt 1 describes.
"""
import os
import json
import re
import httpx

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def call_openrouter(prompt: str, system_prompt: str | None = None) -> str:
    """Send a prompt to OpenRouter and return the text response."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = httpx.post(
        OPENROUTER_BASE_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        json={"model": OPENROUTER_MODEL, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if the model wrapped its JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def call_openrouter_json(prompt: str, system_prompt: str | None, schema: dict) -> dict:
    """Call OpenRouter and request a JSON object matching `schema`.

    Uses response_format json_object where supported, plus fence-stripping
    and retry up to 3x on parse failure.
    Raises ValueError if a valid JSON object cannot be obtained.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    last_err = None
    for _ in range(3):
        try:
            resp = httpx.post(
                OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
                json=body,
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            text = _strip_fences(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue

    raise ValueError(f"OpenRouter did not return valid JSON: {last_err}")
