"""
Estate OS — Ollama Client
==========================
Thin wrapper for the local Ollama API.
No external dependencies — uses urllib.request only.

Ollama must be installed and running for any of these functions to work.
is_available() checks this before any API call.

Install Ollama:  https://ollama.com/download
Start server:    ollama serve   (or it auto-starts after install)
Pull a model:    ollama pull mistral

Default base URL: http://localhost:11434
Override with OLLAMA_BASE_URL environment variable if needed.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Generator


BASE_URL        = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
AVAIL_TIMEOUT   = 2    # seconds for reachability check
GENERATE_TIMEOUT = 120  # seconds for model generation

# Model preference order for estate Q&A (first match wins)
MODEL_PREFERENCE = ["mistral", "llama3", "llama2", "gemma", "phi3", "phi"]

SYSTEM_PROMPT = """\
You are a private estate document assistant running entirely on the user's own computer.
You have been given excerpts from the user's private vault documents.

Rules:
- Answer ONLY from the provided documents. Do not add facts you made up.
- If the answer is not in the documents, say so clearly: "I don't see that in your vault."
- Be specific: name which document you're drawing from (use the filename or title).
- Keep answers concise and factual. No filler.
- Never reveal sensitive values like SSNs, account numbers, or passwords in full
  unless the user has specifically asked for that exact field.

Documents from vault:
{context}
"""


class OllamaError(Exception):
    pass


def is_available() -> bool:
    """Return True if Ollama is running and reachable."""
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/tags", timeout=AVAIL_TIMEOUT)
        return True
    except Exception:
        return False


def list_models() -> list:
    """Return list of installed model name strings. Returns [] if unavailable."""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/tags", timeout=AVAIL_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def preferred_model(models: list) -> str:
    """
    Pick the best installed model for estate Q&A from MODEL_PREFERENCE order.
    Returns the first model in the list if none match the preference list.
    Returns "" if models is empty.
    """
    for pref in MODEL_PREFERENCE:
        for m in models:
            if pref in m.lower():
                return m
    return models[0] if models else ""


def generate_stream(model: str, prompt: str) -> Generator:
    """
    Send a prompt to Ollama and yield text chunks as they stream back.
    Uses /api/generate with stream=true.

    Usage:
        for chunk in generate_stream(model, prompt):
            print(chunk, end="", flush=True)

    Raises OllamaError on connection or API failure.
    """
    payload = json.dumps({
        "model":  model,
        "prompt": prompt,
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=GENERATE_TIMEOUT) as resp:
            for raw_line in resp:
                line = raw_line.strip()
                if not line:
                    continue
                chunk = json.loads(line.decode("utf-8"))
                if chunk.get("response"):
                    yield chunk["response"]
                if chunk.get("done"):
                    break
    except urllib.error.URLError as e:
        raise OllamaError(f"Connection failed: {e}") from e
    except Exception as e:
        raise OllamaError(f"Generate failed: {e}") from e


def build_prompt(context_passages: list, question: str) -> str:
    """
    Build a full prompt string combining the system prompt, document context,
    and the user's question.

    context_passages: list of dicts with keys 'filename', 'vault', 'domain', 'excerpt'
    question: the user's query string
    """
    if not context_passages:
        context = "(No matching documents found in vault.)"
    else:
        lines = []
        for i, p in enumerate(context_passages, 1):
            vault = "Gold" if p.get("vault") == "gold" else "Silver"
            lines.append(
                f"--- Document {i}: {p['filename']} ({vault} / {p.get('domain', 'unknown')}) ---\n"
                f"{p['excerpt']}"
            )
        context = "\n\n".join(lines)

    system = SYSTEM_PROMPT.format(context=context)
    return f"{system}\n\nQuestion: {question}\n\nAnswer:"
