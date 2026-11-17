"""
retrieval.py - hybrid search over the chunked documentation.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

One question goes through four stages:

    1. Dense search  : embed the question with OpenAI, ask Chroma for the
                       nearest chunks (good at meaning: "make training cheaper").
    2. Keyword search: BM25 over the same chunks (good at exact words:
                       "LoraConfig", "lora_alpha", error strings).
    3. Fusion        : Reciprocal Rank Fusion merges both ranked lists.
    4. Budget        : keep the best chunks until the token budget is full.

Both searches are filtered to the sources the student selected in the UI.
"""

import json
import re
from functools import lru_cache

import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi

from app.config import (
    BM25_TOP_K, CHROMA_COLLECTION, CHROMA_DIR, CHUNKS_FILE, CONTEXT_TOKEN_BUDGET,
    DENSE_TOP_K, EMBED_MODEL, FINAL_TOP_K, RRF_K,
)


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens for BM25 (keeps snake_case names like lora_alpha)."""
    return re.findall(r"[a-z0-9_]+", text.lower())


class HybridRetriever:
    def __init__(self) -> None:
        # All chunks in memory: needed for BM25 and to look chunks up by id.
        self.chunks = [json.loads(line) for line in CHUNKS_FILE.open(encoding="utf-8")]
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokenize(c["search_text"]) for c in self.chunks])

        self.openai = OpenAI()
        db = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = db.get_collection(CHROMA_COLLECTION)

    # -- stage 1 -----------------------------------------------------------
    def dense_search(self, query: str, sources: list[str]) -> list[str]:
        """Chunk ids ranked by embedding similarity to the question."""
        embedding = self.openai.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=DENSE_TOP_K,
            where={"source": {"$in": sources}},  # source filter happens inside Chroma
        )
        return result["ids"][0]

    # -- stage 2 -----------------------------------------------------------
    def keyword_search(self, query: str, sources: list[str]) -> list[str]:
        """Chunk ids ranked by BM25 keyword score."""
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        ids = []
        for i in ranked:
            if scores[i] <= 0:
                break
            if self.chunks[i]["source"] in sources:
                ids.append(self.chunks[i]["chunk_id"])
            if len(ids) == BM25_TOP_K:
                break
        return ids

    # -- stages 3 + 4 --------------------------------------------------------
    def search(self, query: str, sources: list[str]) -> list[dict]:
        """Full hybrid pipeline. Returns the passages the agent will read."""
        dense_ids = self.dense_search(query, sources)
        keyword_ids = self.keyword_search(query, sources)

        # Reciprocal Rank Fusion: score = sum over lists of 1 / (k + rank).
        # A chunk ranked high in BOTH lists beats one that is first in only one.
        fused: dict[str, float] = {}
        for ranked_ids in (dense_ids, keyword_ids):
            for rank, chunk_id in enumerate(ranked_ids, start=1):
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

        results, used_tokens = [], 0
        for chunk_id, score in sorted(fused.items(), key=lambda kv: kv[1], reverse=True):
            chunk = self.by_id[chunk_id]
            if used_tokens + chunk["tokens"] > CONTEXT_TOKEN_BUDGET:
                continue  # too big for what is left of the budget; try the next one
            used_tokens += chunk["tokens"]
            results.append({
                "rank": len(results) + 1,
                "score": round(score, 4),
                "found_by": [name for name, ids in (("vector", dense_ids), ("keyword", keyword_ids))
                             if chunk_id in ids],
                "source": chunk["source"],
                "title": chunk["title"],
                "heading": chunk["heading"],
                "url": chunk["url"],
                "text": chunk["text"],
            })
            if len(results) == FINAL_TOP_K:
                break
        return results


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    """Build the retriever once (loading BM25 + Chroma takes a moment) and reuse it."""
    return HybridRetriever()
