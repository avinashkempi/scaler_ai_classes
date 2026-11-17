"""
Step 4 of the data pipeline: embed every chunk and store it in ChromaDB.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Each chunk's `search_text` (contextual header + body) is turned into a vector
with OpenAI's embedding model and saved, with its metadata, in a local Chroma
database at data/chroma/. We use `upsert`, so re-running the script after
adding a source only adds/updates chunks; nothing has to be deleted.

Run from the project root (needs OPENAI_API_KEY):
    python -m pipeline.build_vector_store
"""

import json

import chromadb
from openai import OpenAI

from app.config import CHROMA_COLLECTION, CHROMA_DIR, CHUNKS_FILE, EMBED_MODEL

BATCH_SIZE = 100  # chunks per embeddings API call


def main() -> None:
    chunks = [json.loads(line) for line in CHUNKS_FILE.open(encoding="utf-8")]
    client = OpenAI()

    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Cosine distance is the usual choice for OpenAI embeddings.
    collection = db.get_or_create_collection(
        name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBED_MODEL, input=[c["search_text"] for c in batch]
        )
        collection.upsert(
            ids=[c["chunk_id"] for c in batch],
            embeddings=[item.embedding for item in response.data],
            documents=[c["text"] for c in batch],
            metadatas=[
                {"source": c["source"], "doc_id": c["doc_id"], "title": c["title"],
                 "url": c["url"], "heading": c["heading"]}
                for c in batch
            ],
        )
        print(f"embedded {min(start + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")

    print(f"Done. Collection '{CHROMA_COLLECTION}' has {collection.count()} vectors "
          f"({EMBED_MODEL}) in data/chroma/")


if __name__ == "__main__":
    main()
