"""
Estate OS — Ollama Setup Script
================================
Checks and sets up Ollama for the Phase 5 RAG layer.
Run this on the estate laptop after cloning the repo.

WHAT IT DOES:
  1. Checks if Ollama is installed
  2. Checks if Ollama server is running
  3. Pulls required models (nomic-embed-text for embeddings, mistral for Q&A)
  4. Verifies models work with a test embed + test generate
  5. Reports status

USAGE:
  python setup_ollama.py
      Check status only. Does not install or pull anything.

  python setup_ollama.py --confirm
      Pull missing models and verify they work.

  python setup_ollama.py --test
      Quick smoke test: embed one sentence, generate one answer.

REQUIREMENTS:
  - Ollama must be installed first: https://ollama.com/download
  - Ollama must be running: run 'ollama serve' or launch the Ollama app

This script does NOT install Ollama itself — that requires admin privileges
and a browser download. It handles everything after Ollama is installed.
"""

import sys
import json
import urllib.request
import urllib.error
import shutil
import subprocess
import time

BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODELS = ["mistral", "llama3", "llama2", "gemma", "phi3", "phi"]


def check_ollama_installed():
    """Check if ollama binary is on PATH."""
    return shutil.which("ollama") is not None


def check_ollama_running():
    """Check if Ollama server is responding."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def start_ollama():
    """Try to start Ollama server in background. Returns True if started."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        # Wait for it to come up
        for _ in range(10):
            time.sleep(1)
            if check_ollama_running():
                return True
        return False
    except Exception:
        return False


def list_models():
    """Return list of installed model names."""
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


def pull_model(model_name):
    """Pull a model via ollama CLI. Shows progress."""
    print(f"    Pulling {model_name}... (this may take a few minutes)")
    result = subprocess.run(
        ["ollama", "pull", model_name],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def test_embed(model_name):
    """Test embedding with a sample sentence."""
    payload = json.dumps({
        "model": model_name,
        "input": "This is a test document about estate planning.",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        embeddings = data.get("embeddings", [])
        if embeddings and len(embeddings[0]) > 0:
            return len(embeddings[0])
        return 0
    except Exception as e:
        print(f"    Error: {e}")
        return 0


def test_generate(model_name):
    """Test generation with a simple question."""
    payload = json.dumps({
        "model": model_name,
        "prompt": "In one sentence, what is estate planning?",
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        response = data.get("response", "").strip()
        return response[:100] if response else ""
    except Exception as e:
        print(f"    Error: {e}")
        return ""


def preferred_chat_model(installed):
    """Return the best available chat model from preference list."""
    for model in CHAT_MODELS:
        if model in installed:
            return model
    return None


def run_status():
    """Check and report current Ollama status."""
    print()
    print("=" * 60)
    print("  OLLAMA SETUP — STATUS CHECK")
    print("=" * 60)
    print()

    # Check installed
    installed = check_ollama_installed()
    if installed:
        print("  [OK]   Ollama binary found on PATH")
    else:
        print("  [FAIL] Ollama not installed")
        print()
        print("  Install Ollama from: https://ollama.com/download")
        print("  Then run this script again.")
        print()
        return False

    # Check running
    running = check_ollama_running()
    if running:
        print("  [OK]   Ollama server is running")
    else:
        print("  [WARN] Ollama server is not running")
        print("         Start it with: ollama serve")
        print("         Or launch the Ollama desktop app")
        print()
        return False

    # Check models
    models = list_models()
    print(f"  [INFO] Installed models: {models if models else '(none)'}")
    print()

    # Check embedding model
    if EMBED_MODEL in models:
        print(f"  [OK]   Embedding model: {EMBED_MODEL}")
    else:
        print(f"  [MISS] Embedding model: {EMBED_MODEL} not installed")
        print(f"         Run: ollama pull {EMBED_MODEL}")

    # Check chat model
    chat = preferred_chat_model(models)
    if chat:
        print(f"  [OK]   Chat model: {chat}")
    else:
        print(f"  [MISS] No chat model installed")
        print(f"         Run: ollama pull mistral")

    print()
    print("=" * 60)

    has_embed = EMBED_MODEL in models
    has_chat = chat is not None

    if has_embed and has_chat:
        print("  Ollama is fully set up. Estate Assistant and Vault Indexer are ready.")
    elif has_embed:
        print("  Vault Indexer is ready. Pull a chat model for Estate Assistant Ask tab.")
    elif has_chat:
        print("  Estate Assistant Ask tab is ready. Pull nomic-embed-text for Vault Indexer.")
    else:
        print("  Run with --confirm to pull required models.")

    print("=" * 60)
    print()
    return has_embed and has_chat


def run_confirm():
    """Pull missing models and verify."""
    print()
    print("=" * 60)
    print("  OLLAMA SETUP — INSTALLING MODELS")
    print("=" * 60)
    print()

    if not check_ollama_installed():
        print("  Ollama not installed. Download from: https://ollama.com/download")
        print()
        return False

    if not check_ollama_running():
        print("  Ollama not running. Starting...")
        if start_ollama():
            print("  [OK] Ollama server started")
        else:
            print("  [FAIL] Could not start Ollama. Run 'ollama serve' manually.")
            print()
            return False

    models = list_models()
    success = True

    # Pull embedding model
    if EMBED_MODEL not in models:
        print(f"  Pulling embedding model: {EMBED_MODEL}")
        if pull_model(EMBED_MODEL):
            print(f"  [OK] {EMBED_MODEL} installed")
        else:
            print(f"  [FAIL] Failed to pull {EMBED_MODEL}")
            success = False
    else:
        print(f"  [OK] {EMBED_MODEL} already installed")

    # Pull chat model (first preference that isn't installed)
    chat = preferred_chat_model(models)
    if not chat:
        target = CHAT_MODELS[0]  # mistral
        print(f"  Pulling chat model: {target}")
        if pull_model(target):
            print(f"  [OK] {target} installed")
            chat = target
        else:
            print(f"  [FAIL] Failed to pull {target}")
            success = False
    else:
        print(f"  [OK] Chat model already installed: {chat}")

    print()

    # Verify
    if success:
        print("  Verifying models...")
        dims = test_embed(EMBED_MODEL)
        if dims:
            print(f"  [OK] Embedding test passed ({dims}-dim vectors)")
        else:
            print(f"  [FAIL] Embedding test failed")
            success = False

        if chat:
            answer = test_generate(chat)
            if answer:
                print(f"  [OK] Generation test passed")
                print(f"       Response: {answer}...")
            else:
                print(f"  [FAIL] Generation test failed")
                success = False

    print()
    print("=" * 60)
    if success:
        print("  Ollama is fully set up. Ready for Estate Assistant and Vault Indexer.")
    else:
        print("  Setup incomplete. Check errors above.")
    print("=" * 60)
    print()
    return success


def run_test():
    """Quick smoke test of embed + generate."""
    print()
    print("=" * 60)
    print("  OLLAMA SETUP — SMOKE TEST")
    print("=" * 60)
    print()

    if not check_ollama_running():
        print("  Ollama not running. Start with 'ollama serve' first.")
        print()
        return False

    models = list_models()
    ok = True

    # Test embed
    if EMBED_MODEL in models:
        dims = test_embed(EMBED_MODEL)
        if dims:
            print(f"  [OK] Embed: {EMBED_MODEL} -> {dims}-dim vector")
        else:
            print(f"  [FAIL] Embed: {EMBED_MODEL} failed")
            ok = False
    else:
        print(f"  [SKIP] {EMBED_MODEL} not installed")

    # Test generate
    chat = preferred_chat_model(models)
    if chat:
        answer = test_generate(chat)
        if answer:
            print(f"  [OK] Generate: {chat} responded")
            print(f"       {answer}...")
        else:
            print(f"  [FAIL] Generate: {chat} failed")
            ok = False
    else:
        print(f"  [SKIP] No chat model installed")

    print()
    print("=" * 60)
    if ok:
        print("  Smoke test passed.")
    else:
        print("  Some tests failed. Check output above.")
    print("=" * 60)
    print()
    return ok


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--confirm" in args:
        run_confirm()
    elif "--test" in args:
        run_test()
    else:
        run_status()
