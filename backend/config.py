"""Central configuration, read from the environment / .env file."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Any OpenAI-compatible chat API. The default is Google's Gemini API, which has a free
# tier: get a key at https://aistudio.google.com/apikey. See .env.example for others.
LLM_API_BASE_URL: str = os.getenv(
    "LLM_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
).rstrip("/")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
# `cd backend && python helper.py` lists the models your key can use.
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
# The header that carries the key. "Authorization" sends "Bearer <key>", which most
# providers expect; the UvA proxy wants its own header, x-litellm-api-key.
LLM_AUTH_HEADER: str = os.getenv("LLM_AUTH_HEADER", "Authorization")
# Gemini 3 models are tuned for temperature 1.0 and Google advises against lowering it,
# so every request uses this. Leave it empty to use each request's own temperature.
_temperature = os.getenv("LLM_TEMPERATURE", "1.0")
LLM_TEMPERATURE: float | None = float(_temperature) if _temperature else None

# Number of characters of uploaded material sent to the LLM.
MAX_UPLOAD_CHARS: int = int(os.getenv("MAX_UPLOAD_CHARS", "20000"))
MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "20"))

# AI calls one visitor (by IP address) may make, so a public demo's free quota is shared.
# VISITOR_IP_HEADER names the header in which the host's proxy puts the visitor's real IP
# (True-Client-IP on Render, see render.yaml). Never use X-Forwarded-For: visitors can add
# their own entries to it. When empty, the connecting address is used, as in local runs.
VISITOR_IP_HEADER: str = os.getenv("VISITOR_IP_HEADER", "")
VISITOR_AI_CALLS_PER_MINUTE: int = int(os.getenv("VISITOR_AI_CALLS_PER_MINUTE", "8"))
VISITOR_AI_CALLS_PER_DAY: int = int(os.getenv("VISITOR_AI_CALLS_PER_DAY", "60"))

# Preload a Peer Reviewer and help requests for presenting (see demo.py).
DEMO: bool = os.getenv("DEMO", "").lower() in {"1", "true", "yes"}
