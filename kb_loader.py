# -*- coding: utf-8 -*-
"""
kb_loader.py
────────────
Loads and indexes Knowledge_base/kb.md into the existing FAISS RAG engine.

How it works
────────────
1. Reads kb.md and computes an MD5 hash of its content.
2. Compares against a stored hash in rag_index/kb_hash.txt.
3. If the file has not changed since last index run → skip (fast startup).
4. If the file is new or changed:
   a. Remove any previously loaded kb.md chunks from the FAISS index.
   b. Parse the Markdown into sections split on ## headings.
   c. Build a citation map from the References section at the bottom.
   d. Attach the canonical source URL to every chunk.
   e. Split large sections into ≤900-char overlapping sub-chunks.
   f. Call rag_engine.add_document() for every chunk.
   g. Save the new hash so the next startup is instant.

Refreshing the knowledge base
──────────────────────────────
Edit Knowledge_base/kb.md and restart the Flask server.
The loader detects the change automatically and re-indexes.

To force a full re-index without changing kb.md:
  Delete  rag_index/kb_hash.txt  and restart.
"""

import os
import re
import hashlib

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
KB_PATH   = os.path.join(_BASE, "Knowledge_base", "kb.md")
HASH_FILE = os.path.join(os.getenv("RAG_INDEX_DIR", os.path.join(_BASE, "rag_index")), "kb_hash.txt")

# Tag used to identify kb.md chunks in the vector index
KB_SOURCE_TAG = "kb_md"

# ─────────────────────────────────────────────────────────────────────────────
# Citation map — resolved from the [N] References at the bottom of kb.md
# ─────────────────────────────────────────────────────────────────────────────

def _parse_citations(text: str) -> dict[str, str]:
    """
    Parse citation lines like:
      [1] Fee Structure | JNTU-GV https://jntugvcev.edu.in/...
    Returns {citation_number: url}.
    """
    citations: dict[str, str] = {}
    for m in re.finditer(
        r'^\[(\d+)\][^\n]*?(https?://[^\s\n]+)',
        text,
        re.MULTILINE,
    ):
        citations[m.group(1)] = m.group(2).strip()
    return citations


def _best_url(text: str, citations: dict[str, str]) -> str:
    """
    Find the most specific URL for a chunk.
    Priority:
      1. First inline URL in the text itself.
      2. URL of the first [N] citation reference found in the text.
      3. Default college homepage.
    """
    # Inline URL
    m = re.search(r'https?://[^\s\)\]]+', text)
    if m:
        return m.group(0).rstrip(".,;")

    # Citation reference
    refs = re.findall(r'\[(\d+)\]', text)
    for ref in refs:
        if ref in citations:
            return citations[ref]

    return "https://jntugvcev.edu.in/"


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → chunks
# ─────────────────────────────────────────────────────────────────────────────

def _split_sections(text: str) -> list[dict]:
    """
    Split kb.md on ## headings.  Each section becomes one or more chunks with:
      title   — the ## heading text
      body    — the section body (may be further split if too long)
    """
    # Find the citations block (starts with "Citations:" line) and strip it
    citations_start = text.find("\nCitations:")
    main_text = text[:citations_start] if citations_start != -1 else text

    sections: list[dict] = []
    pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(main_text))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(main_text)
        body  = main_text[start:end].strip()
        if body:
            sections.append({"title": title, "body": body})

    return sections


def _sub_chunk(title: str, body: str, size: int = 900, overlap: int = 100
               ) -> list[tuple[str, str]]:
    """
    Split a section body into ≤size-char sub-chunks on paragraph boundaries.
    Returns list of (chunk_title, chunk_text).
    """
    # Split on blank lines (paragraph boundaries)
    paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]

    chunks: list[tuple[str, str]] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paras:
        para_len = len(para) + 2  # +2 for double newline
        if current_len + para_len > size and current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunks.append((title, chunk_text))
            # Keep last paragraph as overlap
            current_parts = [current_parts[-1]] if current_parts else []
            current_len   = len(current_parts[0]) + 2 if current_parts else 0
        current_parts.append(para)
        current_len += para_len

    if current_parts:
        chunks.append((title, "\n\n".join(current_parts)))

    return chunks if chunks else [(title, body[:size])]


# ─────────────────────────────────────────────────────────────────────────────
# Hash helpers
# ─────────────────────────────────────────────────────────────────────────────

def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _stored_hash() -> str:
    try:
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _save_hash(h: str) -> None:
    os.makedirs(os.path.dirname(HASH_FILE), exist_ok=True)
    with open(HASH_FILE, "w") as f:
        f.write(h)


# ─────────────────────────────────────────────────────────────────────────────
# Remove previously loaded kb.md chunks from the index
# ─────────────────────────────────────────────────────────────────────────────

def _remove_old_kb_chunks(rag_engine) -> int:
    """Delete all documents whose source == KB_SOURCE_TAG. Returns count."""
    try:
        all_docs = rag_engine.get_all_documents()
        # Collect indices (in reverse so deletion doesn't shift positions)
        to_delete = [
            i for i, d in enumerate(all_docs)
            if d.get("source") == KB_SOURCE_TAG
        ]
        for idx in reversed(to_delete):
            try:
                rag_engine.delete_document(idx)
            except Exception as e:
                print(f"[KB] Warning: could not delete doc {idx}: {e}")
        return len(to_delete)
    except Exception as e:
        print(f"[KB] Warning: could not remove old chunks: {e}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def init_kb(rag_engine) -> None:
    """
    Load kb.md into the RAG index if it has changed since the last run.
    Call this once at application startup after rag_engine is ready.

    Parameters
    ----------
    rag_engine : RAGEngine
        The module-level singleton from rag.py.
    """
    # ── File existence check ────────────────────────────────────────────
    if not os.path.exists(KB_PATH):
        print(f"[KB] kb.md not found at {KB_PATH} — skipping.")
        return

    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            kb_text = f.read()
    except Exception as e:
        print(f"[KB] Could not read kb.md: {e}")
        return

    # ── Hash check — skip if unchanged ──────────────────────────────────
    current_hash = _md5(kb_text)
    if current_hash == _stored_hash():
        try:
            # Count how many kb chunks are already in the index
            existing = [d for d in rag_engine.get_all_documents()
                        if d.get("source") == KB_SOURCE_TAG]
            print(f"[KB] kb.md unchanged — {len(existing)} chunks already indexed.")
        except Exception:
            print("[KB] kb.md unchanged — skipping re-index.")
        return

    print("[KB] kb.md changed (or first run) — re-indexing …")

    # ── Remove stale chunks ──────────────────────────────────────────────
    removed = _remove_old_kb_chunks(rag_engine)
    if removed:
        print(f"[KB] Removed {removed} old kb.md chunks from index.")

    # ── Parse ────────────────────────────────────────────────────────────
    citations = _parse_citations(kb_text)
    sections  = _split_sections(kb_text)
    print(f"[KB] Parsed {len(sections)} sections, {len(citations)} citations.")

    # ── Index ────────────────────────────────────────────────────────────
    loaded = 0
    for section in sections:
        title  = section["title"]
        body   = section["body"]
        url    = _best_url(body, citations)

        sub_chunks = _sub_chunk(title, body)

        for i, (chunk_title, chunk_body) in enumerate(sub_chunks):
            t = (
                f"KB — {chunk_title}"
                if len(sub_chunks) == 1
                else f"KB — {chunk_title} [{i+1}/{len(sub_chunks)}]"
            )

            # Append the source URL so the LLM can cite it
            content = f"{chunk_body}\n\nSource URL: {url}"

            try:
                rag_engine.add_document(
                    title    = t,
                    content  = content,
                    source   = KB_SOURCE_TAG,
                    added_by = "kb_loader",
                )
                loaded += 1
            except Exception as e:
                print(f"[KB] Error indexing chunk '{t}': {e}")

    # ── Save hash ────────────────────────────────────────────────────────
    _save_hash(current_hash)

    print(f"[KB] Indexed {loaded} chunks from kb.md. "
          f"Total RAG documents: {rag_engine.doc_count}")
