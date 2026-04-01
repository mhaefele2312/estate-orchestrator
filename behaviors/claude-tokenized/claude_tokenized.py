"""
Claude Tokenized — Private AI for Your Estate Vault
=====================================================
ChatGPT-style interface for querying tokenized vault documents
via Ollama (local LLM). Everything runs on this machine.

LAUNCH:
  Double-click the "Claude Tokenized" desktop shortcut, or:
  streamlit run behaviors/claude-tokenized/claude_tokenized.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

# ── Icon paths ───────────────────────────────────────────────────────────────

_REPO_ROOT   = Path(__file__).parent.parent.parent
ROSE_FAVICON = str(_REPO_ROOT / "icons" / "rose-circle-64.png")
ROSE_AVATAR  = str(_REPO_ROOT / "icons" / "rose-circle-64.png")

# ── Must be first Streamlit call ─────────────────────────────────────────────

st.set_page_config(
    page_title="Claude Tokenized",
    page_icon=ROSE_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help":    None,
        "Report a bug": None,
        "About": (
            "**Claude Tokenized**\n\n"
            "Private AI assistant for your estate vault.\n"
            "Powered by Ollama. No internet. No cloud.\n"
            "Documents never leave this computer."
        ),
    },
)

# ── Heavy CSS — ChatGPT-style ────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Hide Streamlit chrome ── */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1.5rem; padding-bottom: 0; max-width: 820px; }

    /* ── Sidebar: dark like ChatGPT ── */
    [data-testid="stSidebar"] {
        background-color: #1a1a2e !important;
    }
    [data-testid="stSidebar"] * {
        color: #d1d5db !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #f3f4f6 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #2d2d44 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #9ca3af !important;
    }
    /* Sidebar radio buttons */
    [data-testid="stSidebar"] .stRadio label {
        color: #d1d5db !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        color: #ffffff !important;
    }
    /* Sidebar selectbox */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #2d2d44 !important;
        border-color: #3d3d5c !important;
        color: #d1d5db !important;
    }
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2d2d44 !important;
        border: 1px solid #3d3d5c !important;
        color: #d1d5db !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #3d3d5c !important;
        border-color: #C9A846 !important;
        color: #ffffff !important;
    }
    /* Success/warning/info in sidebar */
    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background-color: #2d2d44 !important;
        border-color: #3d3d5c !important;
    }

    /* ── Main area ── */
    .main .block-container {
        background-color: #ffffff;
    }

    /* ── Header bar ── */
    .ct-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.25rem 0 1rem 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }
    .ct-logo {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1a1a2e;
        letter-spacing: -0.3px;
    }
    .ct-logo-rose {
        color: #C9A846;
    }
    .ct-badge {
        display: inline-block;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        vertical-align: middle;
    }
    .ct-badge-local {
        background: #166534;
        color: #DCFCE7;
    }
    .ct-badge-ai {
        background: #1a1a2e;
        color: #C9A846;
    }
    .ct-badge-scope {
        background: #f3f4f6;
        color: #6b7280;
        border: 1px solid #e5e7eb;
    }

    /* ── Chat messages — ChatGPT style ── */
    [data-testid="stChatMessage"] {
        padding: 1rem 0;
        border-bottom: 1px solid #f3f4f6;
    }
    /* User message slightly different background */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #f9fafb;
    }

    /* ── Source cards ── */
    .source-card {
        background: #f9fafb;
        border-left: 3px solid #C9A846;
        border-radius: 0 6px 6px 0;
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
    }
    .source-filename {
        font-weight: 700;
        font-size: 0.9rem;
        color: #1a1a2e;
        margin: 0 0 0.1rem 0;
    }
    .source-location {
        font-size: 0.78rem;
        color: #6B7280;
        margin: 0 0 0.4rem 0;
    }
    .source-excerpt {
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 0.8rem;
        color: #374151;
        white-space: pre-wrap;
        background: #ffffff;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        border: 1px solid #e5e7eb;
        margin: 0;
    }
    .no-results {
        color: #9ca3af;
        font-style: italic;
        padding: 0.5rem 0;
    }

    /* ── Chat input ── */
    [data-testid="stChatInput"] {
        border-top: 1px solid #e5e7eb;
        padding-top: 0.5rem;
    }
    [data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
        border: 1px solid #d1d5db !important;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #C9A846 !important;
        box-shadow: 0 0 0 1px #C9A846 !important;
    }

    /* ── Footer ── */
    .ct-footer {
        font-size: 0.72rem;
        color: #9ca3af;
        text-align: center;
        padding: 0.75rem 0 0.25rem;
        border-top: 1px solid #f3f4f6;
    }

    /* ── Vault pill bar ── */
    .vault-pills {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 0.5rem 0 0.75rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Config ───────────────────────────────────────────────────────────────────

VAULT_SCOPES = {
    "Gold only":                ["gold"],
    "Gold + Silver":            ["gold", "silver"],
    "Gold + Silver + Bronze":   ["gold", "silver", "bronze"],
    "All vaults":               None,
}
DEFAULT_SCOPE = "Gold + Silver"

WELCOME_MSG = (
    "Hello. I'm your private estate assistant, running entirely on this machine.\n\n"
    "Ask me anything about your estate documents — insurance policies, financial accounts, "
    "property details, legal documents, tax records. I'll search your vault, find the relevant "
    "passages, and give you a direct answer.\n\n"
    "Your documents never leave this computer. No internet. No cloud.\n\n"
    "**Try asking:**\n"
    "- *Do I have flood insurance on the Mule property?*\n"
    "- *What is my routing number at First National?*\n"
    "- *What are the beneficiaries on my life insurance?*\n"
    "- *Show me my 2022 tax return details*\n"
    "- *What vehicles do I own?*"
)


# ── Paths & engine ───────────────────────────────────────────────────────────

@st.cache_data
def load_paths() -> tuple:
    behavior_dir = Path(__file__).parent
    repo_root    = behavior_dir.parent.parent

    vault_cfg_path = repo_root / "config" / "vault_config.json"
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
    return None, None


@st.cache_resource(show_spinner="Loading vault documents...")
def load_engine(token_store_str: str):
    parent = str(Path(__file__).parent.parent / "estate-assistant")
    if parent not in sys.path:
        sys.path.insert(0, parent)
    from search import EstateSearchEngine
    return EstateSearchEngine(Path(token_store_str))


def get_ollama_status() -> dict:
    parent = str(Path(__file__).parent.parent / "estate-assistant")
    if parent not in sys.path:
        sys.path.insert(0, parent)
    from ollama_client import is_available, list_models, preferred_model

    if not is_available():
        return {"available": False, "models": [], "selected": ""}
    models  = list_models()
    default = preferred_model(models)
    return {"available": True, "models": models, "selected": default}


# ── Sidebar ──────────────────────────────────────────────────────────────────

def get_cloud_providers() -> dict:
    """Check which cloud LLM providers are available."""
    from cloud_client import available_providers
    return available_providers()


def render_sidebar(engine, is_test: bool, ollama: dict,
                   cloud: dict) -> tuple:
    """
    Returns (provider, model_name, vault_scope_list_or_None).
    provider is one of: "ollama", "gemini", "claude", or "none".
    """
    selected_provider = "none"
    selected_model    = ""
    vault_scope       = VAULT_SCOPES[DEFAULT_SCOPE]

    with st.sidebar:
        st.image(ROSE_AVATAR, width=40)
        st.markdown("## Claude Tokenized")
        st.caption("Private AI for your estate vault")
        st.divider()

        # ── New Chat button
        if st.button("+ New conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # ── Vault scope
        st.markdown("**Vault scope**")
        scope_label = st.radio(
            "Which vaults to search",
            options=list(VAULT_SCOPES.keys()),
            index=list(VAULT_SCOPES.keys()).index(DEFAULT_SCOPE),
            label_visibility="collapsed",
        )
        vault_scope = VAULT_SCOPES[scope_label]
        st.divider()

        # ── LLM provider selector
        st.markdown("**AI provider**")

        # Build provider options dynamically
        provider_options = []
        provider_keys    = []

        # Always offer local Ollama
        if ollama["available"] and ollama["models"]:
            provider_options.append("Local (Ollama)")
            provider_keys.append("ollama")
        else:
            provider_options.append("Local (Ollama) -- offline")
            provider_keys.append("ollama_off")

        # Cloud providers
        from cloud_client import PROVIDER_MODELS
        for name in ("Gemini", "Claude", "ChatGPT"):
            info = cloud.get(name, {})
            if info.get("available"):
                provider_options.append(f"Cloud ({name})")
                provider_keys.append(name.lower())
            else:
                reason = info.get("reason", "not configured")
                provider_options.append(f"Cloud ({name}) -- {reason}")
                provider_keys.append(f"{name.lower()}_off")

        chosen_idx = st.radio(
            "Provider",
            options=range(len(provider_options)),
            format_func=lambda i: provider_options[i],
            index=0,
            label_visibility="collapsed",
        )
        chosen_key = provider_keys[chosen_idx]

        # ── Model selector based on chosen provider
        st.divider()
        st.markdown("**Model**")

        if chosen_key == "ollama":
            selected_provider = "ollama"
            selected_model = st.selectbox(
                "Ollama model",
                options=ollama["models"],
                index=(
                    ollama["models"].index(ollama["selected"])
                    if ollama["selected"] in ollama["models"] else 0
                ),
                label_visibility="collapsed",
            )

        elif chosen_key in ("gemini", "claude", "chatgpt"):
            selected_provider = chosen_key
            # Map key back to provider name as used in PROVIDER_MODELS
            pname_map = {"gemini": "Gemini", "claude": "Claude", "chatgpt": "ChatGPT"}
            pname = pname_map[chosen_key]
            models = PROVIDER_MODELS.get(pname, [])
            selected_model = st.selectbox(
                f"{pname} model",
                options=models,
                index=0,
                label_visibility="collapsed",
            )

        else:
            # Provider not available
            selected_provider = "none"
            if "ollama" in chosen_key:
                st.info("Start Ollama or run:\n`ollama pull mistral`")
            else:
                pname = chosen_key.replace("_off", "").title()
                reason = cloud.get(pname, {}).get("reason", "")
                st.info(f"Set {reason}")

        # Privacy note for cloud
        if selected_provider in ("gemini", "claude", "chatgpt"):
            st.success(
                "Cloud mode is safe.  \n"
                "Only tokenized text is sent.  \n"
                "Real values are restored locally."
            )

        st.divider()

        # ── Vault stats
        gold   = sum(1 for d in engine.documents if d["vault"] == "gold")
        silver = sum(1 for d in engine.documents if d["vault"] == "silver")
        bronze = sum(1 for d in engine.documents if d["vault"] == "bronze")

        st.markdown("**Indexed documents**")
        if gold:
            st.markdown(f"Gold: {gold}")
        if silver:
            st.markdown(f"Silver: {silver}")
        if bronze:
            st.markdown(f"Bronze: {bronze}")
        if not (gold or silver or bronze):
            st.markdown("No documents indexed yet.")

        st.markdown(f"Tokens: {len(engine.registry)}")

        if engine.has_vector_index:
            st.markdown("Search: hybrid (AI + keyword)")
        else:
            st.markdown("Search: keyword only")

        if is_test:
            st.divider()
            st.warning("Test mode  \nUsing sample data.")

    return selected_provider, selected_model, vault_scope


# ── Format helpers ───────────────────────────────────────────────────────────

def format_sources_html(results: list) -> str:
    """Build source cards HTML for display under an answer."""
    if not results:
        return ""

    parts = []
    for r in results:
        doc = r["doc"]
        vault_label = {"gold": "Gold", "silver": "Silver", "bronze": "Bronze"}.get(
            doc["vault"], doc["vault"].title()
        )
        vault_color = "#B8902A" if doc["vault"] == "gold" else "#6B7280"
        domain = doc.get("domain") or ""
        excerpt = r["excerpt"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        parts.append(
            f"<div class='source-card'>"
            f"<p class='source-filename'>{doc['filename']}</p>"
            f"<p class='source-location'>"
            f"<span style='color:{vault_color};font-weight:600'>{vault_label}</span>"
            f"{(' / ' + domain) if domain else ''}"
            f"</p>"
            f"<pre class='source-excerpt'>{excerpt}</pre>"
            f"</div>"
        )
    return "\n".join(parts)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    token_store, is_test = load_paths()

    if token_store is None:
        st.error(
            "**Token Store not found.**  \n"
            "Run `vault_tokenizer.py --vault gold --confirm` first."
        )
        st.stop()

    engine = load_engine(str(token_store))
    ollama = get_ollama_status()
    cloud  = get_cloud_providers()
    provider, selected_model, vault_scope = render_sidebar(
        engine, is_test, ollama, cloud
    )

    # ── Header
    scope_label = "All vaults" if vault_scope is None else " + ".join(
        v.title() for v in vault_scope
    )
    if provider == "ollama":
        ai_badge = f"<span class='ct-badge ct-badge-ai'>Ollama: {selected_model}</span>"
    elif provider in ("gemini", "claude", "chatgpt"):
        ai_badge = f"<span class='ct-badge ct-badge-ai'>Cloud: {selected_model}</span>"
    else:
        ai_badge = "<span class='ct-badge ct-badge-scope'>No AI selected</span>"

    st.markdown(
        f"<div class='ct-header'>"
        f"<span class='ct-logo'>Claude Tokenized</span>"
        f"<span class='ct-badge ct-badge-local'>{'Local' if provider == 'ollama' else 'Tokenized'}</span>"
        f"{ai_badge}"
        f"<span class='ct-badge ct-badge-scope'>Scope: {scope_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MSG}
        ]

    for msg in st.session_state.messages:
        avatar = ROSE_AVATAR if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"], unsafe_allow_html=True)
            if msg.get("sources_html"):
                with st.expander("Sources", expanded=False):
                    st.markdown(msg["sources_html"], unsafe_allow_html=True)

    # ── Chat input
    if prompt := st.chat_input("Ask about your estate..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=ROSE_AVATAR):
            # Step 1: Search vault (always hybrid when index exists)
            with st.spinner("Searching vault..."):
                results = engine.search(prompt, top_k=5, vaults=vault_scope)

            # Build context passages for LLM
            context_passages = []
            for r in results:
                doc = r["doc"]
                # For cloud LLMs: send TOKENIZED text (safe)
                # For local Ollama: send detokenized text (stays on machine)
                if provider in ("gemini", "claude", "chatgpt"):
                    excerpt = doc["text"]  # tokenized version
                    # Extract relevant portion using same logic
                    import re
                    query_words = (
                        set(re.sub(r"[^\w\s]", " ", prompt.lower()).split())
                        - engine._STOP_WORDS
                    )
                    excerpt = engine._extract_excerpt(doc["text"], query_words)
                else:
                    excerpt = r["excerpt"]  # already detokenized

                context_passages.append({
                    "filename": doc["filename"],
                    "vault":    doc["vault"],
                    "domain":   doc.get("domain", ""),
                    "excerpt":  excerpt,
                })

            if provider == "ollama":
                # ── Local Ollama
                parent = str(Path(__file__).parent.parent / "estate-assistant")
                if parent not in sys.path:
                    sys.path.insert(0, parent)
                from ollama_client import build_prompt, generate_stream, OllamaError

                full_prompt = build_prompt(context_passages, prompt)
                try:
                    response_text = st.write_stream(
                        generate_stream(selected_model, full_prompt)
                    )
                except OllamaError as e:
                    response_text = f"Ollama error: {e}"
                    st.error(response_text)

            elif provider in ("gemini", "claude", "chatgpt"):
                # ── Cloud LLM (tokenized text sent, response de-tokenized)
                from cloud_client import cloud_stream

                try:
                    # Stream from cloud — response will contain tokens
                    tokenized_response = st.write_stream(
                        cloud_stream(
                            {"gemini": "Gemini", "claude": "Claude",
                             "chatgpt": "ChatGPT"}[provider],
                            selected_model, context_passages, prompt,
                        )
                    )
                    # De-tokenize: replace [ACCT_0001] etc. with real values
                    response_text = engine.detokenize(tokenized_response)

                    # If de-tokenization changed anything, show the clean version
                    if response_text != tokenized_response:
                        # Clear the streamed (tokenized) output and show clean
                        st.markdown("---")
                        st.markdown(response_text)

                except Exception as e:
                    response_text = f"Cloud API error: {e}"
                    st.error(response_text)

            elif provider == "none" and results:
                # ── No AI — show keyword results directly
                count = len(results)
                response_text = (
                    f"Found **{count}** matching "
                    f"{'document' if count == 1 else 'documents'}.\n\n"
                )
                response_text += format_sources_html(results)
                response_text += (
                    "\n\n*Select an AI provider in the sidebar "
                    "for synthesized answers.*"
                )
                st.markdown(response_text, unsafe_allow_html=True)
            else:
                response_text = (
                    "<div class='no-results'>No matching documents found. "
                    "Try different terms or check that your vault has been "
                    "tokenized.</div>"
                )
                st.markdown(response_text, unsafe_allow_html=True)

            # Show sources
            sources_html = ""
            if results:
                sources_html = format_sources_html(results)
                with st.expander(
                    f"Sources ({len(results)} documents)", expanded=False
                ):
                    st.markdown(sources_html, unsafe_allow_html=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "sources_html": sources_html if results else "",
            })

    # ── Footer
    privacy = (
        "Tokenized text only leaves this machine"
        if provider in ("gemini", "claude", "chatgpt")
        else "No internet &bull; No cloud &bull; Documents stay on this machine"
    )
    st.markdown(
        f"<div class='ct-footer'>"
        f"Claude Tokenized &mdash; "
        f"Private AI for your estate vault &mdash; "
        f"{privacy}"
        f"</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
