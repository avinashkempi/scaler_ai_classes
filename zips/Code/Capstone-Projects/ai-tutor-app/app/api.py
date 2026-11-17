"""
api.py - FastAPI server: streaming chat endpoint + the chat web page.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Endpoints
    GET  /           -> the chat page (frontend/index.html)
    GET  /api/tools  -> model name, tools and the source picker for the UI
    POST /api/chat   -> streams one answer as Server-Sent Events (SSE)

Why streaming? An agent may search 2-4 times before it answers. With SSE the
student sees each step live ("searching LoRA rank...") and the answer appears
word by word, instead of staring at a spinner for 10+ seconds.

Each SSE message is one line:  data: {"type": "...", ...}\n\n

Run from the project root:
    python -m app.api        (then open http://127.0.0.1:8000)
"""

import json
import os
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.agent import retrieve_tutor_context, run_kb_command, stream_chat
from app.config import CHAT_MODEL, DOCUMENTS_FILE, ROOT, SOURCES

app = FastAPI(title="AI Tutor (Agentic RAG)")


class ChatRequest(BaseModel):
    message: str  # only the NEW message; history lives on the server
    threadId: str | None = None  # empty/None = start a new conversation
    sources: list[str] | None = None  # None = all sources


def page_counts() -> dict[str, int]:
    """How many pages each source has (shown next to the checkbox)."""
    counts = {key: 0 for key in SOURCES}
    if DOCUMENTS_FILE.exists():
        for line in DOCUMENTS_FILE.open(encoding="utf-8"):
            counts[json.loads(line)["source"]] += 1
    return counts


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/tools")
def tools() -> dict:
    counts = page_counts()
    return {
        "model": CHAT_MODEL,
        "tools": [{"name": t.name, "description": t.description}
                  for t in (retrieve_tutor_context, run_kb_command)],
        "sources": [{"key": key, "label": cfg["label"], "pages": counts[key]}
                    for key, cfg in SOURCES.items()],
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="message is empty")
    sources = request.sources or list(SOURCES)
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown sources: {unknown}")
    thread_id = request.threadId or str(uuid.uuid4())

    async def event_stream():
        def sse(event: dict) -> str:
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # First event tells the client which conversation this is, so it can
        # send the same threadId with the next question (that's the memory).
        yield sse({"type": "thread", "threadId": thread_id})
        try:
            async for event in stream_chat(request.message, thread_id, sources):
                yield sse(event)
        except Exception as error:  # show the problem in the UI instead of a silent hang
            yield sse({"type": "error", "message": f"{type(error).__name__}: {error}"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
