"""
models/router.py
----------------
100% free multi-model router. Zero cost, no credit card needed.

Routing strategy:
  post_generation     → Groq / Llama 3.3 70B   (500k tokens/day free, best writing)
  cover_letter        → Groq / Llama 3.3 70B
  interview_question  → Groq / Llama 3.3 70B
  interview_feedback  → Groq / Llama 3.3 70B
  paper_summary       → Gemini 2.0 Flash        (1500 req/day free, large context)
  readme_update       → Gemini 2.0 Flash
  quick_classify      → Gemini 2.0 Flash
  rss_filter          → Gemini 2.0 Flash

Free keys (no credit card):
  Groq:   https://console.groq.com → API Keys
  Gemini: https://aistudio.google.com/app/apikey
"""

import os
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

_gemini_client = None

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

TASK_MODEL = {
    "post_generation":    "groq",
    "cover_letter":       "groq",
    "interview_question": "groq",
    "interview_feedback": "groq",
    "paper_summary":      "gemini",
    "readme_update":      "gemini",
    "quick_classify":     "gemini",
    "rss_filter":         "gemini",
}


def call(task: str, prompt: str, system: str = "", max_tokens: int = 1000) -> str:
    """Route a task to the right free model and return response text."""
    provider = TASK_MODEL.get(task, "groq")
    if provider == "groq":
        return _call_groq(prompt, system, max_tokens)
    return _call_gemini(prompt, max_tokens)


def _call_groq(prompt: str, system: str, max_tokens: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Get a free key (no credit card) at: https://console.groq.com\n"
            "Then add to .env: GROQ_API_KEY=gsk_..."
        )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.85},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq error {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"].strip()


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not set.\n"
                "Get a free key at: https://aistudio.google.com/app/apikey\n"
                "Then add to .env: GEMINI_API_KEY=AIza..."
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_gemini(prompt: str, max_tokens: int) -> str:
    client = _get_gemini()
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens),
    )
    return resp.text.strip()


def available_models() -> dict:
    return {
        "groq":          bool(os.environ.get("GROQ_API_KEY")),
        "gemini":        bool(os.environ.get("GEMINI_API_KEY")),
        "groq_model":    GROQ_MODEL,
        "gemini_model":  GEMINI_MODEL,
    }
