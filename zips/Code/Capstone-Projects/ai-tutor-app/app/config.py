"""
config.py - one place for every setting the AI Tutor uses.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Everything else imports from here: model names, folder paths, the list of
documentation sources, and the retrieval knobs. Change a value here and the
whole app (pipeline + API) picks it up.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that holds app/, pipeline/ and frontend/.
ROOT = Path(__file__).resolve().parent.parent

# Read OPENAI_API_KEY (and optional overrides) from the .env file.
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Models (OpenAI only)
# ---------------------------------------------------------------------------
# Chat model that runs the agent loop and writes the answers.
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.4-mini")
# Embedding model for the vector index. The SAME model must be used to embed
# chunks (pipeline) and questions (retrieval), or the vectors won't match.
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Folders and files produced by the pipeline
# ---------------------------------------------------------------------------
DATA_DIR = ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"  # step 1: raw markdown downloaded from GitHub
DOCUMENTS_FILE = DATA_DIR / "documents.jsonl"  # step 2: one cleaned doc per line
CHUNKS_FILE = DATA_DIR / "chunks.jsonl"  # step 2: search-sized chunks
KB_DIR = DATA_DIR / "kb"  # step 3: browsable knowledge base (raw/ wiki/ generated/)
CHROMA_DIR = DATA_DIR / "chroma"  # step 4: vector database on disk
CHROMA_COLLECTION = "tutor_chunks"

# ---------------------------------------------------------------------------
# Documentation sources = the tutor's syllabus.
# Single source of truth: the pipeline, the API's source picker and the
# agent's prompt all read this dict. To add a source, add one entry here and
# re-run the pipeline.
# ---------------------------------------------------------------------------
SOURCES = {
    "peft": {
        "label": "PEFT (LoRA & adapters)",
        "repo": "https://github.com/huggingface/peft.git",
        "docs_path": "docs/source",
        "url_base": "https://huggingface.co/docs/peft/",
        "exclude": [],
    },
    "trl": {
        "label": "TRL (SFT, DPO, GRPO)",
        "repo": "https://github.com/huggingface/trl.git",
        "docs_path": "docs/source",
        "url_base": "https://huggingface.co/docs/trl/",
        "exclude": [],
    },
    "openai_agents": {
        "label": "OpenAI Agents SDK",
        "repo": "https://github.com/openai/openai-agents-python.git",
        "docs_path": "docs",
        "url_base": "https://openai.github.io/openai-agents-python/",
        # Skip translations, auto-generated API stubs and build scripts.
        "exclude": ["ja/", "ko/", "zh/", "ref/", "scripts/"],
    },
}

# ---------------------------------------------------------------------------
# Chunking (pipeline step 2)
# ---------------------------------------------------------------------------
CHUNK_TOKENS = 600  # target size of one chunk
# Token counts are estimated as len(text) / 4 (about 4 characters per token in
# English). Exact counts are not needed for sizing chunks or a context budget.

# ---------------------------------------------------------------------------
# Retrieval (app/retrieval.py)
# ---------------------------------------------------------------------------
DENSE_TOP_K = 15  # candidates from vector search
BM25_TOP_K = 15  # candidates from keyword search
RRF_K = 60  # Reciprocal Rank Fusion constant (60 is the standard default)
FINAL_TOP_K = 6  # passages returned to the agent per tool call
CONTEXT_TOKEN_BUDGET = 4000  # max tokens of passages per tool call

# ---------------------------------------------------------------------------
# Knowledge-base shell (app/kb_shell.py)
# ---------------------------------------------------------------------------
KB_COMMAND_LIMIT = 8  # max run_kb_command calls per user question
KB_COMMAND_TIMEOUT = 8  # seconds per command
KB_MAX_OUTPUT_CHARS = 12_000  # cut long outputs so they don't flood the context
