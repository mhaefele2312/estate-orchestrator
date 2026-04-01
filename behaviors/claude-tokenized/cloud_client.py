"""
Estate OS — Cloud LLM Client
==============================
Sends tokenized vault passages to cloud LLMs (Gemini, Claude, or ChatGPT)
and returns the response. The cloud LLM only ever sees tokenized text —
real values like SSNs and account numbers are replaced with placeholder
tokens before leaving this machine.

De-tokenization happens AFTER the response comes back, locally.

API keys are read from environment variables:
  GEMINI_API_KEY     — for Google Gemini
  ANTHROPIC_API_KEY  — for Anthropic Claude
  OPENAI_API_KEY     — for OpenAI ChatGPT

SUPPORTED PROVIDERS:
  "Gemini"   — Google Gemini (gemini-2.0-flash or gemini-1.5-pro)
  "Claude"   — Anthropic Claude (claude-sonnet-4-20250514)
  "ChatGPT"  — OpenAI (gpt-4o, gpt-4o-mini)
"""

import os
from typing import Generator


# ── System prompt (same intent as the Ollama one) ────────────────────────────

SYSTEM_PROMPT = """\
You are a private estate document assistant. You have been given excerpts
from the user's estate vault documents. These documents have been tokenized
for privacy — sensitive values like names, account numbers, and SSNs appear
as placeholders like [ACCT_0001] or [NAME_0003]. Use them as-is in your
answers; the system will restore the real values after you respond.

Rules:
- Answer ONLY from the provided documents. Do not invent facts.
- If the answer is not in the documents, say so clearly.
- Be specific: name which document you found the information in.
- Keep answers concise and factual.
- Use the token placeholders exactly as they appear (e.g., [SSN_0001]).
  Do not try to guess what they represent.

Documents from vault:
{context}
"""


# ── Provider detection ───────────────────────────────────────────────────────

def available_providers() -> dict:
    """
    Return a dict of provider_name -> status_dict for each cloud provider.
    Status dict has: available (bool), reason (str if not available).
    """
    providers = {}

    # Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            import google.generativeai  # noqa: F401
            providers["Gemini"] = {"available": True}
        except ImportError:
            providers["Gemini"] = {"available": False,
                                   "reason": "google-generativeai not installed"}
    else:
        providers["Gemini"] = {"available": False,
                               "reason": "GEMINI_API_KEY not set"}

    # Claude
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if claude_key:
        try:
            import anthropic  # noqa: F401
            providers["Claude"] = {"available": True}
        except ImportError:
            providers["Claude"] = {"available": False,
                                   "reason": "anthropic package not installed"}
    else:
        providers["Claude"] = {"available": False,
                               "reason": "ANTHROPIC_API_KEY not set"}

    # ChatGPT
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            import openai  # noqa: F401
            providers["ChatGPT"] = {"available": True}
        except ImportError:
            providers["ChatGPT"] = {"available": False,
                                    "reason": "openai package not installed"}
    else:
        providers["ChatGPT"] = {"available": False,
                                "reason": "OPENAI_API_KEY not set"}

    return providers


# ── Context builder ──────────────────────────────────────────────────────────

def build_context(passages: list) -> str:
    """
    Build the document context string from search results.
    passages: list of dicts with 'filename', 'vault', 'domain', 'excerpt'
    The excerpts contain TOKENIZED text (placeholders, not real values).
    """
    if not passages:
        return "(No matching documents found in vault.)"

    lines = []
    for i, p in enumerate(passages, 1):
        vault = p.get("vault", "unknown").title()
        domain = p.get("domain", "")
        lines.append(
            f"--- Document {i}: {p['filename']} ({vault}"
            f"{' / ' + domain if domain else ''}) ---\n"
            f"{p['excerpt']}"
        )
    return "\n\n".join(lines)


# ── Gemini ───────────────────────────────────────────────────────────────────

def gemini_stream(passages: list, question: str,
                  model: str = "gemini-2.0-flash") -> Generator:
    """
    Send tokenized passages + question to Gemini and yield response chunks.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    context = build_context(passages)
    system = SYSTEM_PROMPT.format(context=context)
    full_prompt = f"{system}\n\nQuestion: {question}\n\nAnswer:"

    model_obj = genai.GenerativeModel(model)
    response = model_obj.generate_content(full_prompt, stream=True)

    for chunk in response:
        if chunk.text:
            yield chunk.text


# ── Claude ───────────────────────────────────────────────────────────────────

def claude_stream(passages: list, question: str,
                  model: str = "claude-sonnet-4-20250514") -> Generator:
    """
    Send tokenized passages + question to Claude and yield response chunks.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    context = build_context(passages)
    system = SYSTEM_PROMPT.format(context=context)

    with client.messages.stream(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": question}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── ChatGPT ──────────────────────────────────────────────────────────────────

def chatgpt_stream(passages: list, question: str,
                   model: str = "gpt-4o") -> Generator:
    """
    Send tokenized passages + question to OpenAI ChatGPT and yield chunks.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    context = build_context(passages)
    system = SYSTEM_PROMPT.format(context=context)

    stream = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# ── Unified interface ────────────────────────────────────────────────────────

PROVIDER_MODELS = {
    "Gemini":  ["gemini-2.0-flash", "gemini-1.5-pro"],
    "Claude":  ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
    "ChatGPT": ["gpt-4o", "gpt-4o-mini"],
}

PROVIDER_LABELS = {
    "Gemini":  "Google Gemini",
    "Claude":  "Anthropic Claude",
    "ChatGPT": "OpenAI ChatGPT",
}


def cloud_stream(provider: str, model: str,
                 passages: list, question: str) -> Generator:
    """
    Route to the correct cloud provider's streaming function.
    """
    if provider == "Gemini":
        yield from gemini_stream(passages, question, model=model)
    elif provider == "Claude":
        yield from claude_stream(passages, question, model=model)
    elif provider == "ChatGPT":
        yield from chatgpt_stream(passages, question, model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")
