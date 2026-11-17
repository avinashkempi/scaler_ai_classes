"""
ask.py - ask the tutor from the terminal and watch every agent step.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Several questions in one command share ONE conversation (same thread_id),
so the second question can say "it" and the tutor knows what you mean.

Examples (from the project root):
    python ask.py "How do I choose the LoRA rank and alpha in PEFT?"
    python ask.py "What is a handoff?" "Show me a minimal example" --sources openai_agents
"""

import argparse
import asyncio
import json
import uuid

from app.agent import stream_chat
from app.config import SOURCES


async def ask(question: str, thread_id: str, sources: list[str]) -> None:
    print(f"\n{'=' * 78}\nSTUDENT: {question}\n{'=' * 78}")
    answer_started = False
    async for event in stream_chat(question, thread_id, sources):
        kind = event["type"]
        if kind == "tool-call":
            print(f"  -> tool call  : {event['name']}({json.dumps(event['args'], ensure_ascii=False)})")
        elif kind == "tool-result":
            first_line = event["preview"].strip().splitlines()[0] if event["preview"].strip() else ""
            print(f"  <- tool result: {event['name']} | {first_line[:90]}")
        elif kind == "text-delta":
            if not answer_started:
                print("\nTUTOR:")
                answer_started = True
            print(event["delta"], end="", flush=True)
        elif kind == "sources":
            print("\n\nSOURCES:")
            for s in event["sources"]:
                print(f"  - [{s['source']}] {s['title']}: {s['url']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the AI Tutor from the terminal.")
    parser.add_argument("questions", nargs="+", help="one or more questions (same conversation)")
    parser.add_argument("--sources", default=",".join(SOURCES),
                        help=f"comma-separated source keys (default: all) - {', '.join(SOURCES)}")
    args = parser.parse_args()

    thread_id = str(uuid.uuid4())
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    for question in args.questions:
        await ask(question, thread_id, sources)


if __name__ == "__main__":
    asyncio.run(main())
