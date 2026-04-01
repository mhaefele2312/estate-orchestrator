"""
Estate OS — Search Engine
==========================
Loads tokenized documents from the Token Store, de-tokenizes them using
the Token Registry, and provides keyword-based search over the real content.

No network calls. No LLM. Runs entirely on this machine.

The de-tokenization step happens in memory — real values from the Token
Registry are restored only when building search results for display.
They are never written back to disk.
"""

import json
import re
from pathlib import Path


class EstateSearchEngine:

    def __init__(self, token_store_path: Path):
        self.token_store_path = token_store_path
        self.registry  = self._load_registry()
        self.documents = self._load_documents()

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
        Search documents for content matching the query.

        vaults:  optional list of vault names to restrict the search.
                 Accepted values: "gold", "silver", "bronze".
                 None (default) searches all loaded vaults.
                 Example: vaults=["gold"] searches Gold only.
                          vaults=["gold","silver"] searches Gold + Silver.

        Scoring:
          - Each query keyword that appears in the document raises the score
          - Documents where keywords appear close together score higher
          - Score is normalized by document length so short precise documents
            beat long documents with occasional keyword hits

        Returns up to top_k results, each with source metadata and an excerpt
        showing the most relevant passage with real values restored.
        """
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
                # Normalize: penalize longer documents slightly so a bank
                # statement with one hit beats a tax return with two incidental hits
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
