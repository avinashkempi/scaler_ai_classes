"""
ClaimSense — Agentic Motor Insurance Claims Processor
Author : Shivank Agrawal
File   : app/policy_rag.py
Purpose: Retrieval over the policy wording, so the coverage decision can quote the exact clause.

Design choices:
  * Chunk by CLAUSE, not by fixed 500-token windows. A clause is the unit a claims officer cites
    ("rejected under EXC-4"), so each chunk must be one complete clause with its ID.
  * No vector database. ~20 clauses fit in a numpy array; cosine similarity is one matrix multiply.
    A vector DB (pgvector, OpenSearch) becomes worth it with thousands of documents
    (many products, endorsements, regulator circulars).
  * Embeddings are cached in data/policy_index.json and rebuilt automatically if the wording changes.
"""

import hashlib
import json
import re

import numpy as np

from app import config, llm

HEADING = re.compile(r"^## \[(?P<id>[A-Z0-9-]+)\] (?P<title>.+)$", re.MULTILINE)
_index_cache: tuple[list[dict], np.ndarray] | None = None


def load_clauses() -> list[dict]:
    """Split policy_wording.md into clauses: [{"id": "EXC-4", "title": ..., "text": ...}, ...]."""
    text = config.POLICY_WORDING_PATH.read_text(encoding="utf-8")
    matches = list(HEADING.finditer(text))
    clauses = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clauses.append({"id": match["id"], "title": match["title"], "text": text[match.end():end].strip()})
    return clauses


def get_index() -> tuple[list[dict], np.ndarray]:
    """Return (clauses, clause_vectors). Builds and caches the embeddings on first use."""
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    wording_hash = hashlib.sha256(config.POLICY_WORDING_PATH.read_bytes()).hexdigest()
    if config.POLICY_INDEX_PATH.exists():
        saved = json.loads(config.POLICY_INDEX_PATH.read_text())
        if saved["wording_hash"] == wording_hash and saved["model"] == config.EMBEDDING_MODEL:
            _index_cache = (saved["clauses"], np.array(saved["vectors"], dtype=np.float32))
            return _index_cache

    clauses = load_clauses()
    vectors, usage = llm.embed("index:policy_wording",
                               [f"[{c['id']}] {c['title']}\n{c['text']}" for c in clauses])
    config.POLICY_INDEX_PATH.write_text(json.dumps({
        "wording_hash": wording_hash, "model": config.EMBEDDING_MODEL,
        "clauses": clauses, "vectors": vectors.tolist()}))
    print(f"Built policy index: {len(clauses)} clauses, {usage['input_tokens']} tokens, Rs.{usage['cost_inr']}")
    _index_cache = (clauses, vectors)
    return _index_cache


def retrieve(query: str, k: int = config.RETRIEVAL_TOP_K) -> tuple[list[dict], dict]:
    """Top-k clauses most similar to the query, each with its similarity score."""
    clauses, vectors = get_index()
    query_vector, usage = llm.embed("coverage:embed_query", [query])
    scores = vectors @ query_vector[0]          # cosine similarity (all vectors are unit length)
    top = np.argsort(-scores)[:k]
    return [{**clauses[i], "score": round(float(scores[i]), 3)} for i in top], usage
