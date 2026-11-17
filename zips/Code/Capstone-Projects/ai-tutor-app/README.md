# AI Tutor: Agentic RAG over AI-engineering docs

**Author:** Shivank Agrawal · Future with Shivank

A tutor chatbot that answers questions about **PEFT (LoRA)**, **TRL** and the
**OpenAI Agents SDK** from their official documentation, with citations.
The agent decides on its own when to search, what to search for, and when to
open a page in its knowledge base.

- **Agent:** LangChain `create_agent` (LangGraph) + OpenAI `gpt-5.4-mini`
- **Tool 1, `retrieve_tutor_context`:** hybrid search (OpenAI embeddings in Chroma + BM25, fused with RRF)
- **Tool 2, `run_kb_command`:** read-only, path-jailed shell (`rg`, `grep`, `cat`, ...) over a file-based knowledge base
- **API:** FastAPI, streaming answers as Server-Sent Events
- **UI:** one HTML page, no build step

## Project layout

```
app/
  config.py       settings, models, sources (single source of truth)
  retrieval.py    hybrid search: vector + BM25 -> RRF -> token budget
  kb_shell.py     safe read-only shell over data/kb/
  prompts.py      system prompt
  agent.py        agent, two tools, memory, streaming events
  api.py          FastAPI: /api/tools, /api/chat (SSE), serves the UI
pipeline/
  download_docs.py       1. sparse-clone docs from GitHub
  build_corpus.py        2. clean + heading-aware chunks
  build_kb.py            3. knowledge base: raw/ + generated/ + wiki/
  build_vector_store.py  4. embed chunks into Chroma
frontend/index.html      chat page
ask.py                   terminal client (shows every agent step)
```

## Run it

Requires Python 3.11+, `git`, and an OpenAI API key. `ripgrep` (`rg`) is
recommended (`brew install ripgrep`); without it the agent falls back to `grep`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your OPENAI_API_KEY in .env

# Build the data (about 2-3 minutes, a few cents of API usage)
python -m pipeline.download_docs
python -m pipeline.build_corpus
python -m pipeline.build_kb
python -m pipeline.build_vector_store

# Ask from the terminal
python ask.py "How do I choose the LoRA rank and alpha in PEFT?"

# Or run the web app, then open http://127.0.0.1:8000
python -m app.api
```

## Add a documentation source

Add one entry to `SOURCES` in `app/config.py` (GitHub repo, docs folder,
public URL), then re-run the four pipeline steps. The source picker, the
retrieval filter and the prompt pick it up automatically.

---

Architecture inspired by Towards AI's open-source
[ai-tutor-app](https://github.com/towardsai/ai-tutor-app) (Apache-2.0).
This is an independent, simplified implementation for learning.
