"""
Estate OS — Document Search + AI Assistant
============================================
Two modes in one interface:

  Search tab  — keyword search over tokenized vault documents.
                Returns matching passages with PII restored from the
                Token Registry. No AI. No internet.

  Ask tab     — natural-language Q&A powered by Ollama (local LLM).
                Finds relevant passages via keyword search, then asks
                the local model to synthesize an answer. Everything
                stays on this machine.

If Ollama is not running, the Ask tab shows install instructions and
the Search tab continues to work normally.

LAUNCH:
  streamlit run behaviors/estate-assistant/estate_assistant.py
  Or: double-click the Estate OS shortcut on the desktop.
"""

import json
import sys
from pathlib import Path

import streamlit as st

# ── Page config — must be first Streamlit call ────────────────────────────────

st.set_page_config(
    page_title="Estate OS",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help":    None,
        "Report a bug": None,
        "About": (
            "**Estate OS — Private Document Assistant**\n\n"
            "Running locally on this machine.\n"
            "No internet connection required.\n"
            "Your documents never leave this computer."
        ),
    },
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .estate-header {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }
    .estate-title {
        font-size: 2rem;
        font-weight: 800;
        color: #C9A846;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .estate-subtitle {
        font-size: 0.95rem;
        color: #6B7280;
        margin: 0;
    }
    .local-badge {
        display: inline-block;
        background: #166534;
        color: #DCFCE7;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        margin-left: 0.5rem;
        vertical-align: middle;
    }
    .ai-badge {
        display: inline-block;
        background: #1e3a5f;
        color: #bfdbfe;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        margin-left: 0.3rem;
        vertical-align: middle;
    }
    .source-card {
        background: #FFFFFF;
        border-left: 4px solid #C9A846;
        border-radius: 0 6px 6px 0;
        padding: 0.6rem 1rem;
        margin: 0.5rem 0 0 0;
    }
    .source-filename {
        font-weight: 700;
        font-size: 0.95rem;
        color: #1A2744;
        margin: 0 0 0.15rem 0;
    }
    .source-location {
        font-size: 0.8rem;
        color: #6B7280;
        margin: 0 0 0.5rem 0;
    }
    .source-excerpt {
        font-family: monospace;
        font-size: 0.82rem;
        color: #374151;
        white-space: pre-wrap;
        background: #F9FAFB;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        margin: 0;
    }
    .no-results {
        color: #6B7280;
        font-style: italic;
    }
    .disclaimer {
        font-size: 0.75rem;
        color: #9CA3AF;
        text-align: center;
        padding: 0.5rem;
        border-top: 1px solid #E5E7EB;
        margin-top: 1rem;
    }
    .ollama-install-box {
        background: #1e3a5f;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        color: #e2e8f0;
        margin-top: 1rem;
    }
    .ollama-install-box code {
        background: #0f2036;
        color: #93c5fd;
        padding: 0.15rem 0.4rem;
        border-radius: 3px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Config and paths ──────────────────────────────────────────────────────────

@st.cache_data
def load_paths() -> tuple:
    """
    Resolve the Token Store path.
    Tries the real path from vault_config.json first; falls back to the
    test store on the dev machine.
    Returns (token_store_path_or_None, is_test_mode_bool_or_None).
    """
    behavior_dir = Path(__file__).parent
    repo_root    = behavior_dir.parent.parent

    cfg_path = behavior_dir / "config.json"
    if not cfg_path.exists():
        return None, None

    behavior_cfg   = json.loads(cfg_path.read_text(encoding="utf-8"))
    vault_cfg_path = (behavior_dir / behavior_cfg["vault_config_path"]).resolve()
    if not vault_cfg_path.exists():
        return None, None

    vault_cfg  = json.loads(vault_cfg_path.read_text(encoding="utf-8"))
    real_store = Path(vault_cfg.get("token_store", "")).expanduser()
    test_cfg   = vault_cfg.get("_test_vaults", {})
    test_store = repo_root / test_cfg.get("token_store", "tests/fake-token-store")

    if real_store.exists():
        return real_store, False
    elif test_store.exists():
        return test_store, True
    else:
        return None, None


@st.cache_resource(show_spinner="Loading vault documents...")
def load_engine(token_store_str: str):
    """Load and cache the search engine. Reloads only if the path changes."""
    sys.path.insert(0, str(Path(__file__).parent))
    from search import EstateSearchEngine
    return EstateSearchEngine(Path(token_store_str))


# ── Ollama helpers ────────────────────────────────────────────────────────────

def get_ollama_status() -> dict:
    """
    Check Ollama availability and return a status dict.
    Not cached — called fresh on each Ask tab render to reflect current state.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from ollama_client import is_available, list_models, preferred_model

    if not is_available():
        return {"available": False, "models": [], "selected": ""}

    models  = list_models()
    default = preferred_model(models)
    return {"available": True, "models": models, "selected": default}


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(engine, is_test: bool, ollama: dict) -> str:
    """
    Render the sidebar. Returns the selected Ollama model name (may be "").
    """
    selected_model = ollama.get("selected", "")

    with st.sidebar:
        st.markdown("## 🏛 Estate OS")
        st.divider()

        # Vault status
        if is_test:
            st.warning("**Test mode**  \nUsing sample documents.  \nNo real vault connected.")
        else:
            st.success("**Live vault connected**")

        st.markdown("**🔒 Running locally**  \nNo internet connection.  \nDocuments stay on this machine.")
        st.divider()

        # Vault stats
        gold_docs   = [d for d in engine.documents if d["vault"] == "gold"]
        silver_docs = [d for d in engine.documents if d["vault"] == "silver"]
        st.markdown("**Vault contents**")
        st.markdown(
            f"📁 Gold — {len(gold_docs)} doc{'s' if len(gold_docs) != 1 else ''}"
            if gold_docs else "📁 Gold — not indexed"
        )
        if silver_docs:
            st.markdown(f"📁 Silver — {len(silver_docs)} doc{'s' if len(silver_docs) != 1 else ''}")
        st.markdown(f"🔑 {len(engine.registry)} tokens in registry")
        st.divider()

        # Ollama status
        st.markdown("**AI status (Ollama)**")
        if ollama["available"]:
            st.success("Ollama running")
            if ollama["models"]:
                selected_model = st.selectbox(
                    "Model",
                    options=ollama["models"],
                    index=ollama["models"].index(ollama["selected"]) if ollama["selected"] in ollama["models"] else 0,
                    label_visibility="collapsed",
                )
            else:
                st.warning("No models installed.  \nRun: `ollama pull mistral`")
        else:
            st.info("Ollama not running  \nSearch tab works without it.")
        st.divider()

        # Tips
        st.markdown("**Search tips**")
        st.markdown(
            "- Specific terms: *routing number*, *policy*\n"
            "- Include names: *Vanguard*, *First National*\n"
            "- By year/domain: *2022 tax*, *insurance*\n"
        )
        st.divider()

        if st.button("Clear conversation", use_container_width=True):
            for key in ("search_messages", "ask_messages"):
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    return selected_model


# ── Search tab helpers ────────────────────────────────────────────────────────

def format_search_results(results: list) -> str:
    """Format keyword search results as HTML/Markdown for display."""
    if not results:
        return (
            "<div class='no-results'>No matching documents found in your vault. "
            "Try different keywords or check that the vault has been tokenized recently.</div>"
        )

    count = len(results)
    html  = [f"Found **{count}** matching {'document' if count == 1 else 'documents'} in your vault.\n"]

    for r in results:
        doc          = r["doc"]
        vault_label  = "Gold Vault" if doc["vault"] == "gold" else "Silver Vault"
        vault_color  = "#B8902A" if doc["vault"] == "gold" else "#6B7280"
        domain       = doc["domain"] or "root"
        excerpt_html = r["excerpt"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html.append(
            f"<div class='source-card'>"
            f"<p class='source-filename'>📄 {doc['filename']}</p>"
            f"<p class='source-location'>"
            f"<span style='color:{vault_color};font-weight:600'>{vault_label}</span>"
            f" &rsaquo; {domain}"
            f"</p>"
            f"<pre class='source-excerpt'>{excerpt_html}</pre>"
            f"</div>"
        )

    return "\n".join(html)


SEARCH_WELCOME = (
    "Hello. I can search your vault documents and show you the matching passages "
    "with all sensitive values restored from your private token registry.\n\n"
    "**This runs entirely on this machine. Nothing leaves this computer.**\n\n"
    "Try:\n"
    "- *What is my routing number at First National Bank?*\n"
    "- *Show me my 2022 tax return*\n"
    "- *What life insurance policies do I have?*\n"
    "- *What is my Vanguard account number?*"
)


def render_search_tab(engine) -> None:
    if "search_messages" not in st.session_state:
        st.session_state.search_messages = [
            {"role": "assistant", "content": SEARCH_WELCOME}
        ]

    for msg in st.session_state.search_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Search your vault documents...", key="search_input"):
        st.session_state.search_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                results  = engine.search(prompt, top_k=3)
                response = format_search_results(results)
            st.markdown(response, unsafe_allow_html=True)

        st.session_state.search_messages.append({"role": "assistant", "content": response})


# ── Ask tab helpers ───────────────────────────────────────────────────────────

OLLAMA_INSTALL_INSTRUCTIONS = """\
**Ollama is not running.** The Ask tab needs a local AI model to synthesize answers.

**To set it up (one-time, ~5 minutes):**

1. Download Ollama from **https://ollama.com/download** and install it
2. Open a terminal and run:
   ```
   ollama pull mistral
   ```
   This downloads the Mistral model (~4 GB). Other good options: `llama3`, `gemma`.
3. Ollama starts automatically after install. If it's not running, open a terminal and run:
   ```
   ollama serve
   ```
4. Refresh this page — the Ask tab will activate automatically.

**The Search tab works right now** — try that while Ollama downloads.
"""

ASK_WELCOME = (
    "Hello. I can answer questions about your estate using your private vault documents.\n\n"
    "I find the most relevant passages from your vault, then use a local AI model "
    "to synthesize a direct answer. **Everything runs on this machine — no internet.**\n\n"
    "Try:\n"
    "- *Do I have flood insurance on the Mule property?*\n"
    "- *What are the beneficiaries on my life insurance policy?*\n"
    "- *When does my auto insurance renew?*\n"
    "- *What is the mortgage balance on 2312?*"
)


def render_ask_tab(engine, ollama: dict, selected_model: str) -> None:
    sys.path.insert(0, str(Path(__file__).parent))

    if not ollama["available"]:
        st.markdown(OLLAMA_INSTALL_INSTRUCTIONS)
        st.info("**Search tab is fully functional** — use it while Ollama is being set up.")
        return

    if not ollama["models"]:
        st.warning(
            "Ollama is running but no models are installed.\n\n"
            "Open a terminal and run:\n```\nollama pull mistral\n```"
        )
        return

    # Session state for ask chat
    if "ask_messages" not in st.session_state:
        st.session_state.ask_messages = [
            {"role": "assistant", "content": ASK_WELCOME}
        ]

    # Show which model is active
    st.caption(f"Using: **{selected_model}** — answers are synthesized from your vault documents only")

    for msg in st.session_state.ask_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your estate...", key="ask_input"):
        st.session_state.ask_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            from ollama_client import build_prompt, generate_stream, OllamaError

            # Step 1: Find relevant passages
            with st.spinner("Searching vault..."):
                raw_results = engine.search(prompt, top_k=5)

            # Build context passages for the prompt
            context_passages = []
            for r in raw_results:
                doc = r["doc"]
                context_passages.append({
                    "filename": doc["filename"],
                    "vault":    doc["vault"],
                    "domain":   doc.get("domain", ""),
                    "excerpt":  r["excerpt"],
                })

            # Step 2: Stream LLM answer
            full_prompt = build_prompt(context_passages, prompt)
            try:
                response_text = st.write_stream(generate_stream(selected_model, full_prompt))
            except OllamaError as e:
                response_text = f"Ollama error: {e}. Check that `ollama serve` is running."
                st.error(response_text)

            # Step 3: Show sources used
            if context_passages:
                with st.expander(f"Sources ({len(context_passages)} documents searched)", expanded=False):
                    st.markdown(format_search_results(raw_results), unsafe_allow_html=True)

        st.session_state.ask_messages.append({"role": "assistant", "content": response_text})


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    token_store, is_test = load_paths()

    if token_store is None:
        st.error(
            "**Token Store not found.**  \n"
            "Run `vault_tokenizer.py --vault gold --confirm` on the estate laptop first."
        )
        st.stop()

    engine = load_engine(str(token_store))
    ollama = get_ollama_status()
    selected_model = render_sidebar(engine, is_test, ollama)

    # ── Header ────────────────────────────────────────────────────────────────
    ai_badge = (
        "<span class='ai-badge'>🤖 AI Ready</span>"
        if ollama["available"] and ollama["models"]
        else ""
    )
    st.markdown(
        f"<div class='estate-header'>"
        f"<span class='estate-title'>Estate OS</span>"
        f"<span class='estate-subtitle'>Document Search + AI Q&amp;A</span>"
        f"<span class='local-badge'>🔒 Local</span>"
        f"{ai_badge}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6B7280;font-size:0.85rem;margin-top:0'>"
        "Your private vault — no cloud, no internet, documents never leave this machine"
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_labels = [
        "🔍 Search Documents",
        "🤖 Ask with AI" + (" ✓" if ollama["available"] and ollama["models"] else " (setup needed)"),
    ]
    tab1, tab2 = st.tabs(tab_labels)

    with tab1:
        render_search_tab(engine)

    with tab2:
        render_ask_tab(engine, ollama, selected_model)

    # ── Footer ────────────────────────────────────────────────────────────────
    disclaimer_ai = (
        "AI answers from local Ollama model"
        if ollama["available"] and ollama["models"]
        else "AI tab needs Ollama"
    )
    st.markdown(
        f"<div class='disclaimer'>"
        f"Estate OS &nbsp;|&nbsp; {disclaimer_ai} &nbsp;|&nbsp; "
        f"No internet &nbsp;|&nbsp; Real values from local Token Registry only"
        f"</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
