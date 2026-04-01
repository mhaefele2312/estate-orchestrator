"""
Estate OS — Document Search Assistant
=======================================
A private, local document search interface for your estate vault.

Runs entirely on this machine. No internet connection. No AI. No cloud.
Searches your tokenized vault documents and displays matching passages
with real values restored from the Token Registry.

LAUNCH:
  From the estate-orchestrator project root:
    streamlit run behaviors/estate-assistant/estate_assistant.py

  Or use the desktop shortcut (launch_estate_assistant.bat).
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
            "**Estate OS Document Search**\n\n"
            "Running locally on this machine.\n"
            "No internet connection required.\n"
            "Your documents never leave this computer."
        ),
    },
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Top header bar */
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
    /* Local badge */
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
    /* Source card inside assistant responses */
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
    /* No results */
    .no-results {
        color: #6B7280;
        font-style: italic;
    }
    /* Disclaimer bar */
    .disclaimer {
        font-size: 0.75rem;
        color: #9CA3AF;
        text-align: center;
        padding: 0.5rem;
        border-top: 1px solid #E5E7EB;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Config and paths ──────────────────────────────────────────────────────────

@st.cache_data
def load_paths() -> tuple:
    """
    Resolve the Token Store path.
    Tries the real estate laptop path first; falls back to the test store
    on the dev machine if the real path does not exist.
    Returns (token_store_path, is_test_mode).
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


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar(engine, is_test: bool) -> None:
    with st.sidebar:
        st.markdown("## 🏛 Estate OS")
        st.markdown("### Document Search")
        st.divider()

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
        if gold_docs:
            st.markdown(f"📁 Gold — {len(gold_docs)} document{'s' if len(gold_docs) != 1 else ''}")
        else:
            st.markdown("📁 Gold — not indexed")
        if silver_docs:
            st.markdown(f"📁 Silver — {len(silver_docs)} document{'s' if len(silver_docs) != 1 else ''}")

        st.markdown(f"🔑 {len(engine.registry)} tokens in registry")
        st.divider()

        st.markdown("**Tips**")
        st.markdown(
            "- Use specific terms: *routing number*, *policy number*, *SSN*\n"
            "- Include institution names: *Vanguard*, *First National*\n"
            "- Try year or domain: *2022 tax*, *insurance*\n"
            "- Ask about documents: *trust*, *deed*, *bank statement*"
        )
        st.divider()

        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


# ── Response formatting ───────────────────────────────────────────────────────

def format_results(results: list) -> str:
    """Format search results as Markdown for display in the chat."""
    if not results:
        return (
            "<div class='no-results'>No matching documents found in your vault. "
            "Try different keywords or check that the vault has been tokenized recently.</div>"
        )

    count = len(results)
    noun  = "document" if count == 1 else "documents"
    html  = [f"Found **{count}** matching {noun} in your vault.\n"]

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


# ── Welcome message ───────────────────────────────────────────────────────────

WELCOME = (
    "Hello. I can search your vault documents and show you the matching passages "
    "with all sensitive values restored from your private token registry.\n\n"
    "**This runs entirely on this machine. Nothing leaves this computer.**\n\n"
    "Try asking:\n"
    "- *What is my routing number at First National Bank?*\n"
    "- *Show me my 2022 tax return*\n"
    "- *What life insurance policies do I have?*\n"
    "- *What is my Vanguard account number?*"
)


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
    render_sidebar(engine, is_test)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div class='estate-header'>"
        "<span class='estate-title'>Estate OS</span>"
        "<span class='estate-subtitle'>Document Search</span>"
        "<span class='local-badge'>🔒 Local</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6B7280;font-size:0.85rem;margin-top:0'>"
        "Searching your private vault &mdash; no AI synthesis, no cloud, no internet"
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Chat history ──────────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Search your vault documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching..."):
                results  = engine.search(prompt, top_k=3)
                response = format_results(results)
            st.markdown(response, unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": response})

    # ── Disclaimer bar ────────────────────────────────────────────────────────
    st.markdown(
        "<div class='disclaimer'>"
        "Estate OS &nbsp;|&nbsp; Document retrieval only &nbsp;|&nbsp; "
        "No AI &nbsp;|&nbsp; No internet &nbsp;|&nbsp; "
        "Real values restored from local Token Registry only"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
