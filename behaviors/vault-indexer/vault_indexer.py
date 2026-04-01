"""
Estate OS — Vault Indexer (Phase 5 RAG)
========================================
Reads tokenized documents from the Token Store, chunks them into
passages, generates embeddings via Ollama's nomic-embed-text model,
and stores everything in a LanceDB vector database.

The vector index lives inside the Token Store:
  <token_store>/_vector_index/

This is safe to re-run. It tracks file hashes and only re-indexes
documents that have changed since the last run.

USAGE:
  python vault_indexer.py --vault gold
      Dry-run. Shows what would be indexed without writing anything.

  python vault_indexer.py --vault gold --confirm
      Index Gold vault tokenized documents. Writes to LanceDB.

  python vault_indexer.py --vault silver --confirm
      Index Silver vault.

  python vault_indexer.py --all --confirm
      Index all vaults (gold, silver, bronze) in one pass.

  python vault_indexer.py --test
      Index fake test documents. No real vault required.

  python vault_indexer.py --stats
      Show current index statistics without modifying anything.

DEPENDENCIES:
  pip install lancedb
  ollama pull nomic-embed-text

RULES:
  - Default is dry-run. --confirm required to write to the index.
  - Only reads from the Token Store (sanitized files). Never touches
    Gold, Silver, or Bronze vaults directly.
  - Embedding model runs locally via Ollama. No internet required.
  - Re-running is safe: unchanged files are skipped (SHA-256 tracking).
"""

import json
import hashlib
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


# ── Config ───────────────────────────────────────────────────────────────────

CHUNK_SIZE        = 500   # target tokens per chunk (approx words)
CHUNK_OVERLAP     = 50    # overlap between chunks in words
EMBED_MODEL       = "nomic-embed-text"
OLLAMA_BASE       = "http://localhost:11434"
EMBED_TIMEOUT     = 30    # seconds per embedding request
SUPPORTED_EXT     = {".md", ".txt"}
LANCE_TABLE       = "vault_chunks"


# ── Ollama embedding ─────────────────────────────────────────────────────────

def ollama_embed(text: str, model: str = EMBED_MODEL) -> list:
    """
    Call Ollama /api/embed to get a vector for the given text.
    Returns a list of floats.
    """
    payload = json.dumps({
        "model": model,
        "input": text,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    embeddings = data.get("embeddings", [])
    if not embeddings:
        raise RuntimeError(f"Ollama returned no embeddings for model {model}")
    return embeddings[0]


def check_ollama() -> bool:
    """Return True if Ollama is reachable and the embed model is installed."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=2) as resp:
            data = json.loads(resp.read().decode())
        models = [m["name"] for m in data.get("models", [])]
        # Check for exact match or prefix match (e.g., "nomic-embed-text:latest")
        return any(EMBED_MODEL in m for m in models)
    except Exception:
        return False


# ── Chunking ─────────────────────────────────────────────────────────────────

def chunk_document(text: str, chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> list:
    """
    Split text into overlapping chunks of approximately chunk_size words.
    Returns list of chunk strings. Each chunk has overlap words of context
    from the previous chunk to maintain coherence.
    """
    words = text.split()
    if not words:
        return []

    # If doc is small enough, return it as a single chunk
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start = end - overlap  # step back by overlap for next chunk
        if start >= len(words):
            break

    return chunks


# ── File hashing ─────────────────────────────────────────────────────────────

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── Config loading ───────────────────────────────────────────────────────────

def load_vault_config() -> dict:
    """Load vault_config.json from the standard location."""
    cfg_path = Path(__file__).parent.parent.parent / "config" / "vault_config.json"
    if not cfg_path.exists():
        print(f"ERROR: vault_config.json not found at {cfg_path}")
        sys.exit(1)
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def resolve_token_store(vault_config: dict, test_mode: bool) -> Path:
    """Return the Path to the token store root."""
    if test_mode:
        repo_root = Path(__file__).parent.parent.parent
        test_cfg = vault_config.get("_test_vaults", {})
        store = repo_root / test_cfg.get("token_store", "tests/fake-token-store")
    else:
        raw = vault_config.get("token_store", "").strip()
        if not raw:
            print("ERROR: token_store not configured in vault_config.json")
            sys.exit(1)
        store = Path(raw)

    if not store.exists():
        print(f"ERROR: Token Store not found: {store}")
        if not test_mode:
            print("Run vault_tokenizer.py first to create the Token Store.")
        sys.exit(1)

    return store


# ── File collection ──────────────────────────────────────────────────────────

def collect_tokenized_files(token_store: Path, vault_names: list) -> list:
    """
    Collect all supported files from the specified vault dirs in the token store.
    Returns list of (vault_name, relative_path, absolute_path) tuples.
    """
    files = []
    for vault in vault_names:
        vault_dir = token_store / vault
        if not vault_dir.exists():
            continue
        for p in sorted(vault_dir.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in SUPPORTED_EXT:
                continue
            if "_registry" in p.parts or "_provenance" in p.parts:
                continue
            rel = p.relative_to(vault_dir)
            files.append((vault, rel, p))
    return files


# ── Hash index ───────────────────────────────────────────────────────────────

def load_hash_index(index_dir: Path) -> dict:
    """Load the hash index that tracks which files have been indexed."""
    path = index_dir / "index_hashes.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_hash_index(index_dir: Path, hashes: dict) -> None:
    path = index_dir / "index_hashes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")


# ── Dry run ──────────────────────────────────────────────────────────────────

def run_dry_run(token_store: Path, vault_names: list) -> None:
    files = collect_tokenized_files(token_store, vault_names)
    index_dir = token_store / "_vector_index"
    hashes = load_hash_index(index_dir)

    print()
    print("=" * 60)
    print(f"  VAULT INDEXER — DRY RUN")
    print(f"  Token Store:   {token_store}")
    print(f"  Vaults:        {', '.join(vault_names)}")
    print(f"  Embed model:   {EMBED_MODEL}")
    print(f"  Chunk size:    ~{CHUNK_SIZE} words, {CHUNK_OVERLAP} overlap")
    print("=" * 60)
    print()

    total_chunks = 0
    new_files    = 0
    unchanged    = 0

    for vault, rel, abs_path in files:
        key = f"{vault}/{rel}"
        current_hash = file_sha256(abs_path)

        if hashes.get(key) == current_hash:
            print(f"  [unchanged]  {key}")
            unchanged += 1
            continue

        text = abs_path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_document(text)
        total_chunks += len(chunks)
        new_files += 1
        print(f"  [new/changed] {key}  ->  {len(chunks)} chunk{'s' if len(chunks) != 1 else ''}")

    print()
    print("=" * 60)
    print(f"  Files to index: {new_files}")
    print(f"  Unchanged:      {unchanged}")
    print(f"  Total chunks:   {total_chunks}")
    print(f"  Embeddings:     {total_chunks} calls to {EMBED_MODEL}")
    print()
    print("  Run with --confirm to write the vector index.")
    print()


# ── Live run ─────────────────────────────────────────────────────────────────

def run_confirm(token_store: Path, vault_names: list) -> None:
    import lancedb

    files = collect_tokenized_files(token_store, vault_names)
    index_dir = token_store / "_vector_index"
    hashes = load_hash_index(index_dir)

    print()
    print("=" * 60)
    print(f"  VAULT INDEXER — LIVE")
    print(f"  Token Store:   {token_store}")
    print(f"  Vaults:        {', '.join(vault_names)}")
    print(f"  Index dir:     {index_dir}")
    print(f"  Embed model:   {EMBED_MODEL}")
    print("=" * 60)
    print()

    # Determine which files need indexing
    to_index = []
    unchanged = 0
    for vault, rel, abs_path in files:
        key = f"{vault}/{rel}"
        current_hash = file_sha256(abs_path)
        if hashes.get(key) == current_hash:
            unchanged += 1
            continue
        to_index.append((vault, rel, abs_path, key, current_hash))

    if not to_index:
        print("  All files are up to date. Nothing to index.")
        print()
        return

    print(f"  {len(to_index)} file(s) to index, {unchanged} unchanged.")
    print()

    # Warm up: verify embedding model works with a test call
    print("  Testing embedding model... ", end="", flush=True)
    try:
        test_vec = ollama_embed("test")
        embed_dim = len(test_vec)
        print(f"OK ({embed_dim} dimensions)")
    except Exception as e:
        print(f"FAILED: {e}")
        print(f"\n  Make sure Ollama is running and {EMBED_MODEL} is installed:")
        print(f"    ollama pull {EMBED_MODEL}")
        sys.exit(1)

    # Open or create LanceDB
    db = lancedb.connect(str(index_dir / "lance_db"))

    # Build all new chunks
    all_rows = []
    indexed = 0
    errors = []

    for vault, rel, abs_path, key, current_hash in to_index:
        text = abs_path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_document(text)
        domain = rel.parts[0] if len(rel.parts) > 1 else ""

        print(f"  [{len(chunks)} chunks]  {key}  ", end="", flush=True)

        try:
            for i, chunk_text in enumerate(chunks):
                vector = ollama_embed(chunk_text)
                all_rows.append({
                    "vector":   vector,
                    "text":     chunk_text,
                    "vault":    vault,
                    "domain":   domain,
                    "filename": rel.name,
                    "rel_path": str(rel),
                    "chunk_idx": i,
                    "source_key": key,
                })
            hashes[key] = current_hash
            indexed += 1
            print("OK")
        except Exception as e:
            errors.append(f"{key}: {e}")
            print(f"ERROR: {e}")

    if not all_rows:
        print("\n  No chunks generated. Nothing to write.")
        return

    # Write to LanceDB — overwrite stale chunks, add new ones
    # Strategy: drop rows with matching source_key, then add all new rows
    print(f"\n  Writing {len(all_rows)} chunks to LanceDB... ", end="", flush=True)
    try:
        if LANCE_TABLE in db.list_tables().tables:
            table = db.open_table(LANCE_TABLE)
            # Delete stale chunks for re-indexed files
            indexed_keys = {r["source_key"] for r in all_rows}
            for sk in indexed_keys:
                try:
                    table.delete(f'source_key = "{sk}"')
                except Exception:
                    pass  # table might be empty or key not found
            table.add(all_rows)
        else:
            db.create_table(LANCE_TABLE, data=all_rows)
        print("OK")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append(f"LanceDB write: {e}")

    # Save updated hash index
    save_hash_index(index_dir, hashes)

    print()
    print("=" * 60)
    print(f"  Files indexed: {indexed}")
    print(f"  Unchanged:     {unchanged}")
    print(f"  Total chunks:  {len(all_rows)}")
    print(f"  Index dir:     {index_dir}")
    if errors:
        print(f"  Errors:        {len(errors)}")
        for e in errors:
            print(f"    {e}")
    print("=" * 60)
    print()


# ── Stats ────────────────────────────────────────────────────────────────────

def show_stats(token_store: Path) -> None:
    import lancedb

    index_dir = token_store / "_vector_index"
    if not index_dir.exists():
        print("\n  No vector index found. Run vault_indexer.py --all --confirm first.\n")
        return

    hashes = load_hash_index(index_dir)
    lance_path = index_dir / "lance_db"

    print()
    print("=" * 60)
    print(f"  VAULT INDEX STATS")
    print(f"  Token Store: {token_store}")
    print(f"  Index dir:   {index_dir}")
    print("=" * 60)
    print()
    print(f"  Files tracked:  {len(hashes)}")

    if lance_path.exists():
        try:
            db = lancedb.connect(str(lance_path))
            if LANCE_TABLE in db.list_tables().tables:
                table = db.open_table(LANCE_TABLE)
                count = table.count_rows()
                print(f"  Total chunks:   {count}")

                # Breakdown by vault
                for vault in ("gold", "silver", "bronze"):
                    try:
                        vault_count = table.count_rows(f'vault = "{vault}"')
                        if vault_count:
                            print(f"    {vault}: {vault_count} chunks")
                    except Exception:
                        pass
            else:
                print(f"  LanceDB table '{LANCE_TABLE}' not found.")
        except Exception as e:
            print(f"  LanceDB error: {e}")
    else:
        print("  LanceDB not created yet.")

    print()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    args      = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    vault_config = load_vault_config()

    test_mode = "--test" in arg_lower
    confirm   = "--confirm" in arg_lower
    stats     = "--stats" in arg_lower
    all_vaults = "--all" in arg_lower

    token_store = resolve_token_store(vault_config, test_mode)

    if stats:
        show_stats(token_store)
        return

    # Determine which vaults to index
    vault_names = []
    if all_vaults:
        vault_names = ["gold", "silver", "bronze"]
    elif "--vault" in arg_lower:
        idx = arg_lower.index("--vault")
        if idx + 1 < len(args):
            vault_names = [args[idx + 1].lower()]

    if test_mode and not vault_names:
        vault_names = ["gold"]

    if not vault_names:
        print()
        print("Usage:")
        print("  python vault_indexer.py --vault gold            Dry-run Gold")
        print("  python vault_indexer.py --vault gold --confirm  Index Gold")
        print("  python vault_indexer.py --all --confirm         Index all vaults")
        print("  python vault_indexer.py --stats                 Show index stats")
        print("  python vault_indexer.py --test                  Dry-run with test data")
        print("  python vault_indexer.py --test --confirm        Index test data")
        print()
        sys.exit(1)

    # Verify Ollama before starting
    if not check_ollama():
        print()
        print(f"  ERROR: Ollama is not running or {EMBED_MODEL} is not installed.")
        print()
        print(f"  1. Start Ollama:   ollama serve")
        print(f"  2. Pull model:     ollama pull {EMBED_MODEL}")
        print()
        sys.exit(1)

    if confirm:
        run_confirm(token_store, vault_names)
    else:
        run_dry_run(token_store, vault_names)


if __name__ == "__main__":
    main()
