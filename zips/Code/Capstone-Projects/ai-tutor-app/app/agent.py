"""
agent.py - the agent: one chat model, two tools, memory per conversation.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

This is "agentic RAG": instead of always retrieving once and then answering,
the model DECIDES each step whether to search, what to search for, whether
to open a page in the knowledge base, and when it has enough to answer.

    student question
          |
          v
    +-----------+   tool call    +--------------------------+
    |   model   | -------------> | retrieve_tutor_context   |  hybrid search
    | (GPT-5.4  | <------------- | run_kb_command           |  read-only KB shell
    |   mini)   |   tool result  +--------------------------+
    +-----------+
          |  (loop until the model stops calling tools)
          v
    streamed answer + citations

Built with LangChain's create_agent (a LangGraph graph under the hood):
- InMemorySaver checkpointer -> remembers each conversation by thread_id.
- @dynamic_prompt middleware -> system prompt with the selected sources.
- ToolCallLimitMiddleware    -> caps KB commands per question.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import AsyncIterator

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ToolCallLimitMiddleware, dynamic_prompt
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from app.config import CHAT_MODEL, KB_COMMAND_LIMIT
from app.kb_shell import execute_kb_command, manifest_by_path
from app.prompts import build_system_prompt
from app.retrieval import get_retriever


@dataclass(frozen=True)
class TutorContext:
    """Per-request data the tools can read (not part of the chat history)."""
    sources: tuple[str, ...]  # source keys the student ticked in the UI


# ---------------------------------------------------------------------------
# Tools. The docstring is the description the model sees.
# response_format="content_and_artifact": the tool returns (text for the
# model, citations for the UI). The model only sees the text.
# ---------------------------------------------------------------------------
@tool(response_format="content_and_artifact")
def retrieve_tutor_context(query: str, runtime: ToolRuntime[TutorContext]) -> tuple[str, list[dict]]:
    """Search the course documentation with hybrid vector + keyword search.
    Returns the most relevant passages with their title and URL.
    Pass exactly ONE focused query string per call."""
    passages = get_retriever().search(query, list(runtime.context.sources))
    if not passages:
        return "No passages found in the selected sources. Try other keywords or run_kb_command.", []
    content = json.dumps({"query": query, "passages": passages}, ensure_ascii=False, indent=1)
    citations = [{"title": p["title"], "url": p["url"], "source": p["source"]} for p in passages]
    return content, citations


@tool(response_format="content_and_artifact")
def run_kb_command(command: str) -> tuple[str, list[dict]]:
    """Run ONE read-only command inside the knowledge base folder:
    rg, grep, find, ls, `sed -n START,ENDp FILE`, head, cat or wc.
    Paths are relative to the KB root: raw/, wiki/, generated/.
    No pipes, redirects or chaining."""
    result = execute_kb_command(command)
    manifest = manifest_by_path()
    citations = [
        {"title": manifest[p]["title"], "url": manifest[p]["url"], "source": manifest[p]["source"]}
        for p in result.read_paths if p in manifest
    ]
    return result.output, citations


# ---------------------------------------------------------------------------
# Middleware: rebuild the system prompt on every model call.
# ---------------------------------------------------------------------------
@dynamic_prompt
def tutor_system_prompt(request: ModelRequest) -> str:
    return build_system_prompt(request.runtime.context.sources)


# ---------------------------------------------------------------------------
# The agent (built once, shared by all requests)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_agent():
    return create_agent(
        model=ChatOpenAI(model=CHAT_MODEL),
        tools=[retrieve_tutor_context, run_kb_command],
        middleware=[
            tutor_system_prompt,
            # After N KB commands in one question, further calls get an error
            # message telling the model to answer with what it has.
            ToolCallLimitMiddleware(tool_name="run_kb_command", run_limit=KB_COMMAND_LIMIT),
        ],
        context_schema=TutorContext,
        checkpointer=InMemorySaver(),  # conversation memory, keyed by thread_id
    )


async def stream_chat(message: str, thread_id: str, sources: list[str]) -> AsyncIterator[dict]:
    """Run one student turn and yield UI events as they happen.

    Event types: tool-call, tool-result, text-delta, sources, finish.
    """
    agent = get_agent()
    citations: dict[str, dict] = {}  # url -> citation, de-duplicated

    # stream_mode="messages" gives answer tokens as they are generated;
    # stream_mode="updates" gives each finished step (tool calls, tool results).
    async for mode, data in agent.astream(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
        context=TutorContext(sources=tuple(sources)),
        stream_mode=["messages", "updates"],
    ):
        if mode == "messages":
            chunk, _metadata = data
            # AIMessageChunk = a streamed token; a full AIMessage arrives
            # instead if the model call was not streamed.
            if isinstance(chunk, (AIMessageChunk, AIMessage)) and chunk.text:
                yield {"type": "text-delta", "delta": chunk.text}
            continue

        for update in data.values():  # mode == "updates": {node_name: update}
            if not isinstance(update, dict):
                continue
            for msg in update.get("messages", []):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        yield {"type": "tool-call", "id": call["id"],
                               "name": call["name"], "args": call["args"]}
                elif isinstance(msg, ToolMessage):
                    for citation in msg.artifact or []:
                        citations.setdefault(citation["url"], citation)
                    yield {"type": "tool-result", "id": msg.tool_call_id,
                           "name": msg.name, "preview": str(msg.content)[:300]}

    yield {"type": "sources", "sources": list(citations.values())}
    yield {"type": "finish"}
