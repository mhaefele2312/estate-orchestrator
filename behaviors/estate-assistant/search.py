"""
Estate OS — Search Engine (Hybrid)
====================================
Two search modes:

  Keyword:  Scans all tokenized documents for query terms, scores by
            frequency + proximity, returns passages with PII restored.

  Hybrid:   If a LanceDB vector index exists, runs semantic search via
            Ollama embeddings PLUS keyword search, merges and re-ranks
            results. Falls back to keyword-only if the index doesn't exist
            or Ollama is not running.

No network calls beyond localhost (Ollama). Runs entirely on this machine.

The de-tokenization step happens in memory — real values from the Token
Registry are restored only when building search results for display.
They are never written back to disk.
"""

import json
import re
import urllib.request
from pathlib import Path


EMBED_MODEL  = "nomic-embed-text"
OLLAMA_BASE  = "http://localhost:11434"
LANCE_TABLE  = "vault_chunks"


class EstateSearchEngine:

    def __init__(self, token_store_path: Path):
        self.token_store_path = token_store_path
        self.registry  = self._load_registry()
        self.documents = self._load_documents()
        self._lance_table = self._open_lance_index()

    # ── Registry ──────────────────────────────────────────────────────────────

    def _load_registry(self) -> dict:
        """
        Load token → original value mapping from token_registry.json.
        Returns empty dict if registry does not exist yet.
        """
        path = self.token_store_path / "_registry" / "token_registry.json"
        if not path.exists():
            return {}
        records = json.loads(path.read_text(encoding="utf-8"))
        return {r["token"]: r["original"] for r in records}

    def detokenize(self, text: str) -> str:
        """Replace all [TYPE_NNNN] tokens with their original values."""
        for token, original in self.registry.items():
            text = text.replace(token, original)
        return text

    # ── Document loading ──────────────────────────────────────────────────────

    def _load_documents(self) -> list:
        """
        Load all supported documents from the Token Store into memory.
        Each document is stored with both tokenized and de-tokenized text.
        De-tokenized text is what gets searched and displayed.
        """
        docs = []
        for vault in ("gold", "silver", "bronze"):
            vault_path = self.token_store_path / vault
            if not vault_path.exists():
                continue
            for p in sorted(vault_path.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in (".md", ".txt", ".pdf"):
                    continue
                if "_registry" in p.parts or "_provenance" in p.parts:
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                rel    = p.relative_to(vault_path)
                domain = rel.parts[0] if len(rel.parts) > 1 else ""

                docs.append({
                    "path":        p,
                    "vault":       vault,
                    "domain":      domain,
                    "filename":    p.name,
                    "text":        text,
                    "detokenized": self.detokenize(text),
                })
        return docs

    # ── Vector index ─────────────────────────────────────────────────────────

    def _open_lance_index(self):
        """
        Try to open the LanceDB vector index.
        Returns the LanceDB table or None if the index doesn't exist.
        """
        lance_path = self.token_store_path / "_vector_index" / "lance_db"
        if not lance_path.exists():
            return None
        try:
            import lancedb
            db = lancedb.connect(str(lance_path))
            if LANCE_TABLE in db.list_tables().tables:
                return db.open_table(LANCE_TABLE)
        except Exception:
            pass
        return None

    @property
    def has_vector_index(self) -> bool:
        return self._lance_table is not None

    def _ollama_embed(self, text: str) -> list:
        """Get embedding vector from Ollama. Returns [] on failure."""
        try:
            payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            embeddings = data.get("embeddings", [])
            return embeddings[0] if embeddings else []
        except Exception:
            return []

    def _vector_search(self, query: str, top_k: int = 10,
                       vaults: list = None) -> list:
        """
        Semantic search via LanceDB + Ollama embeddings.
        Returns list of dicts with 'text', 'vault', 'domain', 'filename',
        'rel_path', 'distance'.
        """
        if not self._lance_table:
            return []

        query_vec = self._ollama_embed(query)
        if not query_vec:
            return []

        try:
            results = (
                self._lance_table
                .search(query_vec)
                .limit(top_k * 3)  # over-fetch so we can filter by vault
                .to_list()
            )
        except Exception:
            return []

        allowed = set(vaults) if vaults else None
        filtered = []
        for r in results:
            if allowed and r.get("vault") not in allowed:
                continue
            filtered.append(r)
            if len(filtered) >= top_k:
                break

        return filtered

    # ── Search ────────────────────────────────────────────────────────────────

    # Common words that carry no signal in estate documents
    _STOP_WORDS = {
        "what", "is", "my", "the", "a", "an", "in", "on", "at", "for", "and",
        "or", "of", "to", "do", "i", "how", "when", "where", "was", "are",
        "have", "has", "did", "does", "can", "show", "me", "tell", "about",
        "find", "get", "give", "please", "from", "with", "this", "that",
        "it", "its", "all", "any", "which", "who", "if", "than",
    }

    def search(self, query: str, top_k: int = 3,
               vaults: list = None) -> list:
        """
        Hybrid search: keyword + vector (semantic), merged and re-ranked.

        If a LanceDB vector index exists and Ollama is reachable, runs both
        keyword and semantic search, then merges by reciprocal rank fusion.
        Otherwise falls back to keyword-only.

        vaults:  optional list of vault names to restrict the search.
                 Accepted values: "gold", "silver", "bronze".
                 None (default) searches all loaded vaults.

        Returns up to top_k results, each with source metadata and an excerpt
        showing the most relevant passage with real values restored.
        """
        keyword_results = self._keyword_search(query, top_k=top_k * 2,
                                                vaults=vaults)

        # Try vector search; merge if we get results
        if self._lance_table:
            vector_results = self._vector_search(query, top_k=top_k * 2,
                                                  vaults=vaults)
            if vector_results:
                return self._merge_results(keyword_results, vector_results,
                                           query, top_k)

        # Fallback: keyword only
        return keyword_results[:top_k]

    def _keyword_search(self, query: str, top_k: int = 6,
                        vaults: list = None) -> list:
        """Pure keyword search over loaded documents."""
        query_words = (
            set(re.sub(r"[^\w\s]", " ", query.lower()).split())
            - self._STOP_WORDS
        )
        if not query_words:
            return []

        allowed_vaults = set(vaults) if vaults else None

        results = []
        for doc in self.documents:
            if allowed_vaults and doc["vault"] not in allowed_vaults:
                continue
            text_lower = doc["detokenized"].lower()
            score  = 0
            matched = set()

            for word in query_words:
                count = text_lower.count(word)
                if count:
                    score += count
                    matched.add(word)

            if matched:
                word_count  = max(len(text_lower.split()), 1)
                norm_score  = score / (word_count ** 0.35)
                excerpt     = self._extract_excerpt(doc["detokenized"], query_words)

                results.append({
                    "doc":     doc,
                    "score":   norm_score,
                    "matched": matched,
                    "excerpt": excerpt,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _merge_results(self, keyword_results: list, vector_results: list,
                       query: str, top_k: int) -> list:
        """
        Reciprocal rank fusion: combine keyword and vector results.
        Each result gets 1/(k+rank) from each list where it appears.
        k=60 is a standard RRF constant.
        """
        k = 60
        scores = {}  # filename → fused score
        source = {}  # filename → result dict (from keyword results)

        # Score keyword results
        for rank, r in enumerate(keyword_results):
            fname = r["doc"]["filename"]
            scores[fname] = scores.get(fname, 0) + 1.0 / (k + rank)
            source[fname] = r

        # Score vector results
        query_words = (
            set(re.sub(r"[^\w\s]", " ", query.lower()).split())
            - self._STOP_WORDS
        )

        for rank, vr in enumerate(vector_results):
            fname = vr.get("filename", "")
            scores[fname] = scores.get(fname, 0) + 1.0 / (k + rank)

            # If this file wasn't found by keyword search, build a result
            if fname not in source:
                # Find the matching loaded doc to get detokenized text
                doc = self._find_doc_by_filename(fname, vr.get("vault"))
                if doc:
                    excerpt = self._extract_excerpt(
                        doc["detokenized"], query_words
                    ) if query_words else self.detokenize(vr.get("text", ""))
                    source[fname] = {
                        "doc":     doc,
                        "score":   0,
                        "matched": query_words,
                        "excerpt": excerpt,
                    }

        # Sort by fused score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for fname, _ in ranked:
            if fname in source:
                results.append(source[fname])
            if len(results) >= top_k:
                break

        return results

    def _find_doc_by_filename(self, filename: str, vault: str = None) -> dict:
        """Find a loaded document by filename (and optionally vault)."""
        for doc in self.documents:
            if doc["filename"] == filename:
                if vault is None or doc["vault"] == vault:
                    return doc
        return None

    def _extract_excerpt(self, text: str, query_words: set,
                         context_lines: int = 7) -> str:
        """
        Find the passage in the document most relevant to the query
        and return it with a few lines of surrounding context.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return "(no content)"

        # Score each line by how many query words appear in it
        best_idx   = 0
        best_score = 0
        for i, line in enumerate(lines):
            ll    = line.lower()
            score = sum(1 for w in query_words if w in ll)
            if score > best_score:
                best_score = score
                best_idx   = i

        start = max(0, best_idx - 1)
        end   = min(len(lines), best_idx + context_lines)
        return "\n".join(lines[start:end])
